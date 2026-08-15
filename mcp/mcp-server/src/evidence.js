import { readFile, readdir } from "node:fs/promises";

const HOST_ROOT = process.env.HOST_ROOT ?? "/host";
const DOCKER_API = process.env.DOCKER_API ?? "http://docker-proxy:2375";
const STORAGE_COLLECTOR_URL = process.env.STORAGE_COLLECTOR_URL ?? "http://storage-collector:8720";
const STORAGE_ENDPOINTS = new Set(["inventory", "filesystems", "smart", "nvme", "btrfs", "raid"]);

function hostPath(path) {
  return `${HOST_ROOT}${path}`;
}

async function readText(path) {
  return readFile(hostPath(path), "utf8");
}

function parseKeyValue(text, separator = "=") {
  const result = {};
  for (const line of text.split("\n")) {
    const index = line.indexOf(separator);
    if (index < 1) continue;
    const key = line.slice(0, index).trim();
    const value = line.slice(index + separator.length).trim().replace(/^"|"$/g, "");
    result[key] = value;
  }
  return result;
}

function decodeMount(value) {
  return value
    .replaceAll("\\040", " ")
    .replaceAll("\\011", "\t")
    .replaceAll("\\012", "\n")
    .replaceAll("\\134", "\\");
}

async function dockerGet(path) {
  const response = await fetch(`${DOCKER_API}${path}`, {
    signal: AbortSignal.timeout(5000),
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Docker proxy returned HTTP ${response.status}`);
  }
  return response.json();
}

async function dockerBuffer(path) {
  const response = await fetch(`${DOCKER_API}${path}`, {
    signal: AbortSignal.timeout(5000),
    headers: { Accept: "application/octet-stream" },
  });
  if (!response.ok) throw new Error(`Docker proxy returned HTTP ${response.status}`);
  return Buffer.from(await response.arrayBuffer());
}

async function storageCollectorGet(endpoint) {
  if (!STORAGE_ENDPOINTS.has(endpoint)) throw new Error("Storage collector endpoint is not allow-listed");
  const response = await fetch(`${STORAGE_COLLECTOR_URL}/${endpoint}`, {
    signal: AbortSignal.timeout(20000),
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Storage collector returned HTTP ${response.status}`);
  const payload = await response.json();
  if (payload?.collectorStatus !== "success") throw new Error(`Storage collector failed: ${payload?.error ?? "unknown error"}`);
  return payload;
}

export const storageInventory = () => storageCollectorGet("inventory");
export const filesystemUsage = () => storageCollectorGet("filesystems");
export const smartHealth = () => storageCollectorGet("smart");
export const nvmeHealth = () => storageCollectorGet("nvme");
export const btrfsHealth = () => storageCollectorGet("btrfs");
export const raidHealth = () => storageCollectorGet("raid");

function decodeDockerLogStream(buffer) {
  const chunks = [];
  let offset = 0;
  while (offset + 8 <= buffer.length && buffer[offset] <= 2 && buffer[offset + 1] === 0 && buffer[offset + 2] === 0 && buffer[offset + 3] === 0) {
    const length = buffer.readUInt32BE(offset + 4);
    if (offset + 8 + length > buffer.length) break;
    chunks.push(buffer.subarray(offset + 8, offset + 8 + length).toString("utf8"));
    offset += 8 + length;
  }
  return chunks.length && offset === buffer.length ? chunks.join("") : buffer.toString("utf8");
}

function redactLogLine(line) {
  return line
    .replace(/\x1B\[[0-?]*[ -/]*[@-~]/g, "")
    .replace(/(bearer\s+)[A-Za-z0-9._~+\/-]+=*/gi, "$1[REDACTED]")
    .replace(/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g, "[REDACTED_JWT]")
    .replace(/(https?:\/\/[^\s:/@]+:)[^\s@]+@/gi, "$1[REDACTED]@")
    .replace(/\b(password|passwd|token|secret|api[_-]?key|access[_-]?key|private[_-]?key|credential|authorization|cookie)(\s*[:=]\s*)([^\s,;]+)/gi, "$1$2[REDACTED]")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");
}

function safeContainerReference(container) {
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(container)) throw new Error("Invalid container name or ID");
  return encodeURIComponent(container);
}

export async function systemInfo() {
  const [osText, uptimeText, memText, cpuText, hostnameText] = await Promise.all([
    readText("/etc/os-release"),
    readText("/proc/uptime"),
    readText("/proc/meminfo"),
    readText("/proc/cpuinfo"),
    readText("/etc/hostname").catch(() => "unknown"),
  ]);
  const os = parseKeyValue(osText);
  const mem = parseKeyValue(memText, ":");
  const cpuModels = cpuText
    .split("\n")
    .filter((line) => line.startsWith("model name"))
    .map((line) => line.split(":").slice(1).join(":").trim());
  const cpuCount = cpuText.split("\n").filter((line) => /^processor\s*:/.test(line)).length;
  const totalMemoryBytes = Number.parseInt(mem.MemTotal ?? "0", 10) * 1024;
  const availableMemoryBytes = Number.parseInt(mem.MemAvailable ?? "0", 10) * 1024;

  return {
    hostname: hostnameText.trim(),
    os: os.PRETTY_NAME ?? os.NAME ?? "Unknown",
    osVersion: os.VERSION_ID ?? null,
    uptimeSeconds: Math.floor(Number.parseFloat(uptimeText.split(/\s+/)[0] ?? "0")),
    cpuCount,
    cpuModel: cpuModels[0] ?? "Unknown",
    totalMemoryBytes,
    availableMemoryBytes,
  };
}

export async function storageMounts() {
  const mountInfo = await readText("/proc/1/mountinfo");
  const mounts = [];
  for (const line of mountInfo.split("\n")) {
    if (!line.trim()) continue;
    const fields = line.split(" ");
    const separator = fields.indexOf("-");
    if (separator < 0 || fields.length < separator + 3) continue;
    const target = decodeMount(fields[4]);
    if (!(target === "/" || target === "/DATA" || target.startsWith("/DATA/") || target === "/media" || target.startsWith("/media/"))) continue;
    mounts.push({
      source: decodeMount(fields[separator + 2]),
      target,
      filesystem: fields[separator + 1],
      options: fields[5]?.split(",") ?? [],
    });
  }
  return mounts.sort((a, b) => a.target.localeCompare(b.target));
}

export async function dockerContainers() {
  const containers = await dockerGet("/containers/json?all=1&size=0");
  return containers.map((container) => ({
    id: container.Id.slice(0, 12),
    name: (container.Names?.[0] ?? "unknown").replace(/^\//, ""),
    image: container.Image,
    state: container.State,
    status: container.Status,
    health: container.Status?.includes("(unhealthy)")
      ? "unhealthy"
      : container.Status?.includes("(healthy)")
        ? "healthy"
        : "not-reported",
    ports: (container.Ports ?? []).map((port) => ({
      private: port.PrivatePort,
      public: port.PublicPort ?? null,
      type: port.Type,
      ip: port.IP ?? null,
    })),
  }));
}

export async function dockerImages() {
  const images = await dockerGet("/images/json?all=0");
  return images.map((image) => ({
    id: image.Id.replace(/^sha256:/, "").slice(0, 12),
    tags: image.RepoTags ?? [],
    sizeBytes: image.Size,
    created: image.Created,
  }));
}

export async function dockerInspect(container) {
  const data = await dockerGet(`/containers/${safeContainerReference(container)}/json`);
  const state = data.State ?? {};
  const host = data.HostConfig ?? {};
  return {
    id: String(data.Id ?? "").slice(0, 12),
    name: String(data.Name ?? "unknown").replace(/^\//, ""),
    image: data.Config?.Image ?? null,
    created: data.Created ?? null,
    state: {
      status: state.Status ?? null,
      running: Boolean(state.Running),
      paused: Boolean(state.Paused),
      restarting: Boolean(state.Restarting),
      oomKilled: Boolean(state.OOMKilled),
      dead: Boolean(state.Dead),
      pid: state.Pid ?? null,
      exitCode: state.ExitCode ?? null,
      startedAt: state.StartedAt ?? null,
      finishedAt: state.FinishedAt ?? null,
      health: state.Health ? { status: state.Health.Status, failingStreak: state.Health.FailingStreak } : null,
    },
    restartCount: data.RestartCount ?? 0,
    restartPolicy: host.RestartPolicy?.Name ?? "no",
    security: {
      privileged: Boolean(host.Privileged),
      readonlyRootfs: Boolean(host.ReadonlyRootfs),
      networkMode: host.NetworkMode ?? null,
      pidMode: host.PidMode || null,
      ipcMode: host.IpcMode || null,
      capAdd: host.CapAdd ?? [],
      capDrop: host.CapDrop ?? [],
      securityOpt: host.SecurityOpt ?? [],
    },
    ports: data.NetworkSettings?.Ports ?? {},
    mounts: (data.Mounts ?? []).map((mount) => ({
      type: mount.Type,
      source: mount.Source,
      destination: mount.Destination,
      readWrite: Boolean(mount.RW),
      propagation: mount.Propagation || null,
    })),
    networks: Object.entries(data.NetworkSettings?.Networks ?? {}).map(([name, network]) => ({
      name,
      ipAddress: network.IPAddress || null,
      gateway: network.Gateway || null,
      macAddress: network.MacAddress || null,
    })),
    omittedSensitiveFields: ["Config.Env", "Config.Cmd", "Config.Entrypoint", "Config.Labels"],
  };
}

export async function dockerLogs(container, tail = 100) {
  const safeTail = Math.max(1, Math.min(200, Number.parseInt(String(tail), 10) || 100));
  const buffer = await dockerBuffer(`/containers/${safeContainerReference(container)}/logs?stdout=1&stderr=1&timestamps=1&tail=${safeTail}`);
  const lines = decodeDockerLogStream(buffer).split(/\r?\n/).filter(Boolean).slice(-safeTail).map(redactLogLine);
  return { container, requestedTail: safeTail, returnedLines: lines.length, redacted: true, lines };
}

function memoryValue(status, name) {
  const match = status.match(new RegExp(`^${name}:\\s+(\\d+)\\s+kB$`, "m"));
  return match ? Number.parseInt(match[1], 10) * 1024 : 0;
}

export async function systemProcesses(sort = "cpu", limit = 25) {
  const safeLimit = Math.max(1, Math.min(100, Number.parseInt(String(limit), 10) || 25));
  const sampleWindowMs = 300;

  async function processSnapshot() {
    const cpuStat = await readText("/proc/stat");
    const cpuFields = (cpuStat.split("\n")[0] ?? "").trim().split(/\s+/).slice(1).map((value) => Number.parseInt(value, 10) || 0);
    const totalCpuTicks = cpuFields.reduce((total, value) => total + value, 0);
    const idleCpuTicks = (cpuFields[3] ?? 0) + (cpuFields[4] ?? 0);
    const cpuCount = cpuStat.split("\n").filter((line) => /^cpu\d+\s/.test(line)).length || 1;
  const processDirectories = (await readdir(hostPath("/proc"), { withFileTypes: true }))
    .filter((entry) => entry.isDirectory() && /^\d+$/.test(entry.name));
  const processes = [];
  for (const entry of processDirectories) {
    try {
      const [stat, status] = await Promise.all([
        readText(`/proc/${entry.name}/stat`),
        readText(`/proc/${entry.name}/status`),
      ]);
      const close = stat.lastIndexOf(")");
      const open = stat.indexOf("(");
      if (open < 0 || close < open) continue;
      const fields = stat.slice(close + 2).trim().split(/\s+/);
      const statusFields = parseKeyValue(status, ":");
      processes.push({
        pid: Number.parseInt(entry.name, 10),
        name: stat.slice(open + 1, close),
        state: fields[0] ?? null,
        parentPid: Number.parseInt(fields[1] ?? "0", 10),
        uid: Number.parseInt((statusFields.Uid ?? "0").split(/\s+/)[0], 10),
        threads: Number.parseInt(fields[17] ?? "0", 10),
        cpuTicks: Number.parseInt(fields[11] ?? "0", 10) + Number.parseInt(fields[12] ?? "0", 10),
        residentMemoryBytes: memoryValue(status, "VmRSS"),
        virtualMemoryBytes: memoryValue(status, "VmSize"),
      });
    } catch {
      // A process can exit between directory discovery and evidence reads.
    }
  }
    return { totalCpuTicks, idleCpuTicks, cpuCount, processes };
  }

  const first = await processSnapshot();
  await new Promise((resolve) => setTimeout(resolve, sampleWindowMs));
  const second = await processSnapshot();
  const firstByPid = new Map(first.processes.map((process) => [process.pid, process]));
  const totalDelta = Math.max(1, second.totalCpuTicks - first.totalCpuTicks);
  const idleDelta = Math.max(0, second.idleCpuTicks - first.idleCpuTicks);
  const hostCpuBusyPercent = Math.max(0, Math.min(100, ((totalDelta - idleDelta) / totalDelta) * 100));
  const processes = second.processes.map((process) => {
    const previous = firstByPid.get(process.pid);
    const cpuDeltaTicks = previous && previous.name === process.name
      ? Math.max(0, process.cpuTicks - previous.cpuTicks)
      : 0;
    const cpuPercentOfHost = Math.max(0, Math.min(100, (cpuDeltaTicks / totalDelta) * 100));
    return {
      ...process,
      cpuDeltaTicks,
      cpuPercentOfHost: Number(cpuPercentOfHost.toFixed(2)),
      cpuPercentOfCore: Number((cpuPercentOfHost * second.cpuCount).toFixed(2)),
    };
  });
  const comparator = sort === "memory"
    ? (a, b) => b.residentMemoryBytes - a.residentMemoryBytes
    : sort === "pid"
      ? (a, b) => a.pid - b.pid
      : (a, b) => b.cpuPercentOfHost - a.cpuPercentOfHost || b.cpuTicks - a.cpuTicks;
  return {
    sort,
    limit: safeLimit,
    observedProcesses: processes.length,
    sampleWindowMs,
    cpuCount: second.cpuCount,
    hostCpuBusyPercent: Number(hostCpuBusyPercent.toFixed(2)),
    items: processes.sort(comparator).slice(0, safeLimit),
  };
}

export async function dockerInfo() {
  const info = await dockerGet("/info");
  return {
    containers: info.Containers,
    containersRunning: info.ContainersRunning,
    containersPaused: info.ContainersPaused,
    containersStopped: info.ContainersStopped,
    images: info.Images,
    dockerRootDir: info.DockerRootDir,
    driver: info.Driver,
  };
}

export async function dashboardEvidence() {
  const generatedAt = new Date().toISOString();
  const [system, mounts, containers, images, docker] = await Promise.all([
    systemInfo(),
    storageMounts(),
    dockerContainers(),
    dockerImages(),
    dockerInfo(),
  ]);
  const unhealthy = containers.filter((container) => container.health === "unhealthy");
  const running = containers.filter((container) => container.state === "running").length;

  return {
    status: "live",
    mode: "viewer",
    generatedAt,
    server: { name: "zimabrain-mcp-server", version: "0.5.0", transport: "streamable-http" },
    system,
    docker: { ...docker, observedContainers: containers.length, running, unhealthy: unhealthy.length },
    storage: { observedMounts: mounts.length, mounts },
    images: { observed: images.length },
    findings: [
      {
        state: unhealthy.length ? "attention" : "verified",
        name: "containers_healthy",
        result: unhealthy.length ? `${unhealthy.length} container(s) report unhealthy` : "No containers report an unhealthy state",
        source: "docker_ps",
        age: "now",
      },
      {
        state: "verified",
        name: "docker_inventory_current",
        result: `${running} running of ${containers.length} observed containers`,
        source: "docker_ps",
        age: "now",
      },
      {
        state: mounts.length ? "verified" : "unknown",
        name: "storage_inventory_current",
        result: mounts.length ? `${mounts.length} host storage mount(s) observed` : "No host storage mounts were verified",
        source: "storage_mounts",
        age: "now",
      },
      {
        state: "unknown",
        name: "no_critical_exposure",
        result: "External reachability has not been measured",
        source: "not measured in stage one",
        age: "unknown",
      },
    ],
  };
}
