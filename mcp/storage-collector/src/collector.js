import { execFile } from "node:child_process";
import { readFile, readdir, realpath } from "node:fs/promises";
import { promisify } from "node:util";
import { parseBtrfsFilesystems, parseBtrfsStats, parseDf, parseMdstat, parseSmart } from "./parsers.js";

const execFileAsync = promisify(execFile);
const DEVICE = /^\/dev\/(?:sd[a-z]|nvme\d+n\d+|nvme\d+)$/;

export function countActionable(items) {
  return items.filter((item) => ["attention", "critical"].includes(item.status)).length;
}

function deviceList(name, fallback) {
  const values = String(process.env[name] ?? fallback).split(",").map((value) => value.trim()).filter(Boolean);
  if (!values.every((value) => DEVICE.test(value))) throw new Error(`Invalid ${name} device allow-list`);
  return values;
}

const SATA_DEVICES = deviceList("SATA_DEVICES", "/dev/sda,/dev/sdb,/dev/sdc");
const NVME_CONTROLLERS = deviceList("NVME_CONTROLLERS", "/dev/nvme0,/dev/nvme1,/dev/nvme2,/dev/nvme3");
const BTRFS_DEVICES = deviceList("BTRFS_DEVICES", "/dev/sda,/dev/sdb,/dev/nvme0n1,/dev/nvme1n1,/dev/nvme2n1");

async function command(program, args, timeout = 12000) {
  try {
    return await execFileAsync(program, args, { timeout, maxBuffer: 4 * 1024 * 1024, encoding: "utf8" });
  } catch (error) {
    if (error?.stdout) return { stdout: String(error.stdout), stderr: String(error.stderr ?? ""), exitCode: error.code };
    throw new Error(`${program} failed without readable output`);
  }
}

async function jsonCommand(program, args) {
  const result = await command(program, args);
  try {
    return JSON.parse(result.stdout);
  } catch {
    throw new Error(`${program} returned invalid JSON`);
  }
}

export async function storageInventory() {
  const payload = await jsonCommand("lsblk", ["--json", "--bytes", "--output", "NAME,KNAME,PATH,TYPE,SIZE,MODEL,TRAN,FSTYPE,MOUNTPOINTS"]);
  const excluded = /^(?:loop|nbd)\d+$/;
  const disks = (payload.blockdevices ?? []).filter((disk) => disk.type === "disk" && !excluded.test(disk.name)).map((disk) => ({
    name: disk.name,
    path: disk.path,
    type: disk.type,
    sizeBytes: Number(disk.size ?? 0),
    model: String(disk.model ?? "").trim() || null,
    transport: disk.tran ?? null,
    filesystem: disk.fstype ?? null,
    mountpoints: (disk.mountpoints ?? []).filter(Boolean).map((value) => String(value).replace(/^\/host/, "")),
    partitions: (disk.children ?? []).map((part) => ({
      name: part.name,
      path: part.path,
      type: part.type,
      sizeBytes: Number(part.size ?? 0),
      filesystem: part.fstype ?? null,
      mountpoints: (part.mountpoints ?? []).filter(Boolean).map((value) => String(value).replace(/^\/host/, "")),
    })),
  }));
  return { observedDisks: disks.length, disks };
}

export async function filesystemUsage() {
  const result = await command("df", ["-B1", "-P", "-T"]);
  const filesystems = parseDf(result.stdout);
  return {
    observedFilesystems: filesystems.length,
    attentionCount: countActionable(filesystems),
    filesystems,
  };
}

export async function smartHealth() {
  const devices = [];
  for (const device of SATA_DEVICES) {
    try {
      devices.push(parseSmart(await jsonCommand("smartctl", ["-j", "-a", "-d", "sat", device]), device));
    } catch (error) {
      devices.push({ device, status: "unknown", error: String(error.message ?? error), findings: [] });
    }
  }
  return { observedDevices: devices.length, attentionCount: countActionable(devices), devices };
}

export async function nvmeHealth() {
  const devices = [];
  for (const device of NVME_CONTROLLERS) {
    const controller = device.split("/").at(-1);
    try {
      const sysfsRoot = `/host/sys/class/nvme/${controller}`;
      const [model, firmware, state, temperatureC] = await Promise.all([
        readFile(`${sysfsRoot}/model`, "utf8").then((value) => value.trim()),
        readFile(`${sysfsRoot}/firmware_rev`, "utf8").then((value) => value.trim()),
        readFile(`${sysfsRoot}/state`, "utf8").then((value) => value.trim()),
        nvmeSysfsTemperature(controller),
      ]);
      const findings = [{
        level: "unknown",
        code: "nvme_smart_unavailable",
        message: "NVMe SMART endurance and media-error counters are not available through the safe read-only device boundary.",
      }];
      if (temperatureC !== null && temperatureC >= 75) findings.push({ level: "critical", code: "temperature", value: temperatureC, message: `NVMe temperature is ${temperatureC}°C.` });
      else if (temperatureC !== null && temperatureC >= 65) findings.push({ level: "warning", code: "temperature", value: temperatureC, message: `NVMe temperature is elevated at ${temperatureC}°C.` });
      const actionable = findings.find((finding) => finding.level === "critical" || finding.level === "warning");
      devices.push({
        device,
        model,
        firmware,
        controllerState: state,
        temperatureC,
        healthVerified: false,
        criticalWarning: null,
        availableSpare: null,
        spareThreshold: null,
        percentageUsed: null,
        mediaErrors: null,
        errorLogEntries: null,
        unsafeShutdowns: null,
        powerOnHours: null,
        status: actionable?.level === "critical" ? "critical" : actionable ? "attention" : "unknown",
        findings,
      });
    } catch (error) {
      devices.push({ device, status: "unknown", healthVerified: false, error: String(error.message ?? error), findings: [] });
    }
  }
  return {
    observedDevices: devices.length,
    attentionCount: countActionable(devices),
    unverifiedCount: devices.filter((item) => item.healthVerified !== true).length,
    devices,
  };
}

async function nvmeSysfsTemperature(controller) {
  const hwmonRoot = "/host/sys/class/hwmon";
  const entries = await readdir(hwmonRoot, { withFileTypes: true }).catch(() => []);
  for (const entry of entries) {
    if (!entry.isDirectory() && !entry.isSymbolicLink()) continue;
    const path = `${hwmonRoot}/${entry.name}`;
    const name = await readFile(`${path}/name`, "utf8").then((value) => value.trim()).catch(() => "");
    if (name !== "nvme") continue;
    const devicePath = await realpath(`${path}/device`).catch(() => "");
    if (!devicePath.endsWith(`/nvme/${controller}`)) continue;
    const raw = await readFile(`${path}/temp1_input`, "utf8").then((value) => Number(value.trim())).catch(() => NaN);
    return Number.isFinite(raw) ? Number((raw / 1000).toFixed(1)) : null;
  }
  return null;
}

export async function btrfsHealth() {
  const shown = await command("btrfs", ["filesystem", "show", "--raw"]);
  const filesystems = parseBtrfsFilesystems(shown.stdout);
  const deviceStats = [];
  for (const device of BTRFS_DEVICES) {
    const result = await command("btrfs", ["device", "stats", "-c", device]);
    deviceStats.push(parseBtrfsStats(result.stdout, device));
  }
  const errorCount = deviceStats.reduce((sum, item) => sum + item.totalErrors, 0);
  return {
    observedFilesystems: filesystems.length,
    multiDeviceFilesystems: filesystems.filter((item) => item.totalDevices > 1).length,
    errorCount,
    status: errorCount > 0 ? "attention" : "healthy",
    filesystems,
    deviceStats,
  };
}

export async function raidHealth() {
  const mdstat = await readFile("/host/proc/mdstat", "utf8");
  const mdArrays = parseMdstat(mdstat);
  const btrfs = await btrfsHealth();
  const multiDeviceBtrfs = btrfs.filesystems.filter((filesystem) => filesystem.totalDevices > 1);
  const zfsKernelLoaded = await readFile("/host/proc/modules", "utf8").then((text) => /^zfs\s/m.test(text)).catch(() => false);
  const zfsPools = await readdir("/host/proc/spl/kstat/zfs", { withFileTypes: true })
    .then((entries) => entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort())
    .catch(() => []);
  const configured = mdArrays.length > 0 || multiDeviceBtrfs.length > 0 || zfsPools.length > 0;
  const degraded = mdArrays.some((array) => !array.active) || multiDeviceBtrfs.some((filesystem) => filesystem.devices.length < filesystem.totalDevices);
  return {
    configured,
    status: !configured ? "not_applicable" : degraded ? "attention" : "healthy",
    mdraid: { configured: mdArrays.length > 0, arrays: mdArrays },
    btrfsMultiDevice: { configured: multiDeviceBtrfs.length > 0, filesystems: multiDeviceBtrfs },
    zfs: {
      kernelLoaded: zfsKernelLoaded,
      configured: zfsPools.length > 0,
      pools: zfsPools,
      poolDetailsMeasured: false,
    },
    note: !configured ? "No active MD RAID, multi-device Btrfs or configured ZFS pool was observed." : null,
  };
}
