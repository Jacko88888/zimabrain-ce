import http from "node:http";
import { btrfsHealth, filesystemUsage, nvmeHealth, raidHealth, smartHealth, storageInventory } from "./collector.js";

const port = Number.parseInt(process.env.PORT ?? "8720", 10);
const routes = new Map([
  ["/inventory", storageInventory],
  ["/filesystems", filesystemUsage],
  ["/smart", smartHealth],
  ["/nvme", nvmeHealth],
  ["/btrfs", btrfsHealth],
  ["/raid", raidHealth],
]);

const server = http.createServer(async (request, response) => {
  response.setHeader("Content-Type", "application/json");
  response.setHeader("Cache-Control", "no-store");
  if (request.method !== "GET") {
    response.writeHead(405).end(JSON.stringify({ status: "error", error: "Method not allowed" }));
    return;
  }
  if (request.url === "/health") {
    response.writeHead(200).end(JSON.stringify({ status: "ok", name: "zimabrain-storage-collector", version: "0.1.1", mode: "fixed-read-only" }));
    return;
  }
  const handler = routes.get(request.url);
  if (!handler) {
    response.writeHead(404).end(JSON.stringify({ status: "error", error: "Unknown endpoint" }));
    return;
  }
  try {
    const result = await handler();
    response.writeHead(200).end(JSON.stringify({ collectorStatus: "success", generatedAt: new Date().toISOString(), ...result }));
  } catch (error) {
    response.writeHead(503).end(JSON.stringify({ status: "error", error: String(error?.message ?? error), generatedAt: new Date().toISOString() }));
  }
});

server.listen(port, "0.0.0.0", () => console.log(`ZimaBrain storage collector listening on ${port}`));
