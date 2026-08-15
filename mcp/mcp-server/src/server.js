import { randomUUID } from "node:crypto";
import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { readAudit, writeAudit } from "./audit.js";
import {
  btrfsHealth,
  dashboardEvidence,
  dockerContainers,
  dockerImages,
  dockerInspect,
  dockerLogs,
  filesystemUsage,
  nvmeHealth,
  raidHealth,
  smartHealth,
  storageInventory,
  storageMounts,
  systemInfo,
  systemProcesses,
} from "./evidence.js";

const port = Number.parseInt(process.env.PORT ?? "8718", 10);
const transports = new Map();
const SERVER_VERSION = "0.6.1";
const containerReference = z.string().min(1).max(128).regex(/^[A-Za-z0-9][A-Za-z0-9_.-]*$/);

function toolResult(value) {
  const structuredContent = Array.isArray(value)
    ? { count: value.length, items: value }
    : value;
  return {
    content: [{ type: "text", text: JSON.stringify(value, null, 2) }],
    structuredContent,
  };
}

function registerReadTool(server, name, description, inputSchema, handler) {
  server.registerTool(
    name,
    {
      description,
      inputSchema,
      annotations: {
        title: name,
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async (args) => {
      const started = Date.now();
      try {
        const value = await handler(args);
        await writeAudit({ actor: "mcp-client", tool: name, result: "SUCCESS", durationMs: Date.now() - started });
        return toolResult(value);
      } catch (error) {
        await writeAudit({ actor: "mcp-client", tool: name, result: "ERROR", durationMs: Date.now() - started, error: String(error?.message ?? error) });
        return { content: [{ type: "text", text: `Tool failed: ${error?.message ?? error}` }], isError: true };
      }
    },
  );
}

function createServer() {
  const server = new McpServer({ name: "zimabrain-mcp-server", version: SERVER_VERSION });

  registerReadTool(server, "system_info", "Read verified host OS, CPU, memory and uptime evidence.", {}, systemInfo);
  registerReadTool(server, "storage_mounts", "List verified host storage mount sources and targets.", {}, storageMounts);
  registerReadTool(server, "storage_inventory", "List physical disks, partitions, filesystems and approved mountpoints through the fixed storage collector.", {}, storageInventory);
  registerReadTool(server, "filesystem_usage", "Read capacity and usage for approved /DATA and /media filesystems.", {}, filesystemUsage);
  registerReadTool(server, "smart_health", "Read bounded SMART health, temperature, sector and CRC evidence from explicitly allowed SATA devices.", {}, smartHealth);
  registerReadTool(server, "nvme_health", "Read bounded NVMe health, temperature, endurance and media-error evidence from explicitly allowed controllers.", {}, nvmeHealth);
  registerReadTool(server, "btrfs_health", "Read Btrfs filesystem membership and persistent device error counters from explicitly allowed devices.", {}, btrfsHealth);
  registerReadTool(server, "raid_health", "Report configured MD RAID, multi-device Btrfs and observable ZFS state without claiming health when RAID is absent.", {}, raidHealth);
  registerReadTool(server, "docker_ps", "List Docker containers through the GET-only socket proxy.", {}, dockerContainers);
  registerReadTool(server, "docker_images", "List local Docker images through the GET-only socket proxy.", {}, dockerImages);
  registerReadTool(
    server,
    "docker_inspect",
    "Inspect one container while omitting environment, command, entrypoint and labels.",
    { container: containerReference },
    ({ container }) => dockerInspect(container),
  );
  registerReadTool(
    server,
    "docker_logs",
    "Read a bounded, redacted tail from one container (maximum 200 lines).",
    { container: containerReference, tail: z.number().int().min(1).max(200).default(100) },
    ({ container, tail }) => dockerLogs(container, tail),
  );
  registerReadTool(
    server,
    "system_processes",
    "List bounded host processes without command lines or environment data.",
    { sort: z.enum(["cpu", "memory", "pid"]).default("cpu"), limit: z.number().int().min(1).max(100).default(25) },
    ({ sort, limit }) => systemProcesses(sort, limit),
  );

  server.registerResource(
    "current-inventory",
    "zimaos://inventory/current",
    { description: "Current read-only ZimaOS evidence inventory", mimeType: "application/json" },
    async (uri) => ({
      contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(await dashboardEvidence(), null, 2) }],
    }),
  );

  server.registerPrompt(
    "diagnose_system",
    {
      description: "Verifier-first system review using only current MCP evidence.",
      argsSchema: { question: z.string().min(3).max(500) },
    },
    async ({ question }) => ({
      messages: [{ role: "user", content: { type: "text", text: `Question: ${question}\nUse current MCP evidence only. Separate verified, partially verified, and not verified claims. Do not infer success without proof.` } }],
    }),
  );

  return server;
}

const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: "256kb" }));

app.get("/health", (_request, response) => {
  response.json({ status: "ok", name: "zimabrain-mcp-server", version: SERVER_VERSION, mode: "viewer", liveTools: 13, storageLayer: "fixed-read-only-collector" });
});

app.get("/api/dashboard", async (_request, response) => {
  try {
    const [evidence, audit] = await Promise.all([dashboardEvidence(), readAudit(20)]);
    response.set("Cache-Control", "no-store").json({ ...evidence, audit });
  } catch (error) {
    response.status(503).json({ status: "error", error: String(error?.message ?? error), generatedAt: new Date().toISOString() });
  }
});

app.post("/mcp", async (request, response) => {
  const sessionId = request.header("mcp-session-id");
  try {
    let transport = sessionId ? transports.get(sessionId) : undefined;
    if (!transport && !sessionId && isInitializeRequest(request.body)) {
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        enableJsonResponse: true,
        onsessioninitialized: (id) => transports.set(id, transport),
      });
      transport.onclose = () => {
        if (transport.sessionId) transports.delete(transport.sessionId);
      };
      const server = createServer();
      await server.connect(transport);
    } else if (!transport) {
      response.status(400).json({ jsonrpc: "2.0", error: { code: -32000, message: "Invalid or missing MCP session" }, id: null });
      return;
    }
    await transport.handleRequest(request, response, request.body);
  } catch {
    if (!response.headersSent) {
      response.status(500).json({ jsonrpc: "2.0", error: { code: -32603, message: "Internal MCP error" }, id: null });
    }
  }
});

app.get("/mcp", async (request, response) => {
  const transport = transports.get(request.header("mcp-session-id"));
  if (!transport) return response.status(400).send("Invalid or missing MCP session");
  await transport.handleRequest(request, response);
});

app.delete("/mcp", async (request, response) => {
  const transport = transports.get(request.header("mcp-session-id"));
  if (!transport) return response.status(400).send("Invalid or missing MCP session");
  await transport.handleRequest(request, response);
});

app.listen(port, "0.0.0.0", () => {
  console.log(`ZimaBrain MCP server listening on ${port}`);
});

async function shutdown() {
  for (const transport of transports.values()) await transport.close();
  process.exit(0);
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);
