function number(value, fallback = 0) {
  if (value === null || value === undefined || value === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function rawAttribute(attribute) {
  return number(attribute?.raw?.value ?? attribute?.raw?.string?.match(/\d+/)?.[0]);
}

function attributeMap(payload) {
  return new Map((payload?.ata_smart_attributes?.table ?? []).map((attribute) => [number(attribute.id), attribute]));
}

function statusFromFindings(findings) {
  if (findings.some((finding) => finding.level === "critical")) return "critical";
  if (findings.some((finding) => finding.level === "warning")) return "attention";
  return "healthy";
}

export function parseSmart(payload, device) {
  const attributes = attributeMap(payload);
  const reallocated = rawAttribute(attributes.get(5));
  const pending = rawAttribute(attributes.get(197));
  const offlineUncorrectable = rawAttribute(attributes.get(198));
  const crcErrors = rawAttribute(attributes.get(199));
  const reportedUncorrectable = rawAttribute(attributes.get(187));
  const temperatureC = number(payload?.temperature?.current, null);
  const passed = payload?.smart_status?.passed === true;
  const findings = [];

  if (!passed) findings.push({ level: "critical", code: "smart_failed", message: "SMART overall health did not pass." });
  if (pending > 0) findings.push({ level: "critical", code: "pending_sectors", value: pending, message: `${pending} pending sector(s) require attention.` });
  if (offlineUncorrectable > 0) findings.push({ level: "critical", code: "offline_uncorrectable", value: offlineUncorrectable, message: `${offlineUncorrectable} offline-uncorrectable sector(s) were reported.` });
  if (reportedUncorrectable > 0) findings.push({ level: "critical", code: "reported_uncorrectable", value: reportedUncorrectable, message: `${reportedUncorrectable} reported-uncorrectable error(s) were recorded.` });
  if (reallocated > 0) findings.push({ level: "warning", code: "reallocated_sectors", value: reallocated, message: `${reallocated} reallocated sector(s) were recorded.` });
  if (crcErrors > 0) findings.push({ level: "warning", code: "crc_errors", value: crcErrors, message: `${crcErrors} historical UDMA CRC error(s) were recorded; monitor whether this count increases.` });
  if (temperatureC !== null && temperatureC >= 55) findings.push({ level: "critical", code: "temperature", value: temperatureC, message: `Drive temperature is ${temperatureC}°C.` });
  else if (temperatureC !== null && temperatureC >= 45) findings.push({ level: "warning", code: "temperature", value: temperatureC, message: `Drive temperature is elevated at ${temperatureC}°C.` });

  return {
    device,
    model: payload?.model_name ?? payload?.model_family ?? "Unknown",
    protocol: payload?.device?.protocol ?? "ATA",
    smartPassed: passed,
    temperatureC,
    powerOnHours: number(payload?.power_on_time?.hours, null),
    reallocatedSectors: reallocated,
    pendingSectors: pending,
    offlineUncorrectable,
    reportedUncorrectable,
    crcErrors,
    errorLogCount: number(payload?.ata_smart_error_log?.summary?.count),
    status: statusFromFindings(findings),
    findings,
  };
}

function nvmeTemperatureC(value) {
  const temperature = number(value, null);
  if (temperature === null) return null;
  return Number((temperature > 200 ? temperature - 273.15 : temperature).toFixed(1));
}

export function parseNvme(smart, identity, device) {
  const criticalWarning = number(smart?.critical_warning);
  const temperatureC = nvmeTemperatureC(smart?.temperature);
  const availableSpare = number(smart?.avail_spare, null);
  const spareThreshold = number(smart?.spare_thresh, null);
  const percentageUsed = number(smart?.percent_used, null);
  const mediaErrors = number(smart?.media_errors);
  const errorLogEntries = number(smart?.num_err_log_entries);
  const findings = [];

  if (criticalWarning > 0) findings.push({ level: "critical", code: "critical_warning", value: criticalWarning, message: `NVMe critical-warning mask is ${criticalWarning}.` });
  if (mediaErrors > 0) findings.push({ level: "critical", code: "media_errors", value: mediaErrors, message: `${mediaErrors} NVMe media/data-integrity error(s) were recorded.` });
  if (availableSpare !== null && spareThreshold !== null && availableSpare <= spareThreshold) findings.push({ level: "critical", code: "low_spare", value: availableSpare, message: `Available spare is ${availableSpare}%, at or below the ${spareThreshold}% threshold.` });
  if (percentageUsed !== null && percentageUsed >= 100) findings.push({ level: "critical", code: "endurance_used", value: percentageUsed, message: `NVMe endurance use is ${percentageUsed}%.` });
  else if (percentageUsed !== null && percentageUsed >= 80) findings.push({ level: "warning", code: "endurance_used", value: percentageUsed, message: `NVMe endurance use is elevated at ${percentageUsed}%.` });
  if (temperatureC !== null && temperatureC >= 75) findings.push({ level: "critical", code: "temperature", value: temperatureC, message: `NVMe temperature is ${temperatureC}°C.` });
  else if (temperatureC !== null && temperatureC >= 65) findings.push({ level: "warning", code: "temperature", value: temperatureC, message: `NVMe temperature is elevated at ${temperatureC}°C.` });

  return {
    device,
    model: String(identity?.mn ?? identity?.model_number ?? "Unknown").trim(),
    firmware: String(identity?.fr ?? identity?.firmware_rev ?? "Unknown").trim(),
    criticalWarning,
    temperatureC,
    availableSpare,
    spareThreshold,
    percentageUsed,
    mediaErrors,
    errorLogEntries,
    unsafeShutdowns: number(smart?.unsafe_shutdowns),
    powerOnHours: number(smart?.power_on_hours),
    status: statusFromFindings(findings),
    findings,
  };
}

export function parseBtrfsFilesystems(text) {
  const filesystems = [];
  let current = null;
  for (const line of String(text ?? "").split(/\r?\n/)) {
    const header = line.match(/^Label:\s+(.*?)\s+uuid:\s+([0-9a-f-]+)$/i);
    if (header) {
      current = { label: header[1] === "none" ? null : header[1], uuid: header[2], totalDevices: 0, devices: [] };
      filesystems.push(current);
      continue;
    }
    const total = line.match(/^\s*Total devices\s+(\d+)\s+FS bytes used\s+(\d+)/);
    if (total && current) {
      current.totalDevices = number(total[1]);
      current.bytesUsed = number(total[2]);
      continue;
    }
    const device = line.match(/^\s*devid\s+(\d+)\s+size\s+(\d+)\s+used\s+(\d+)\s+path\s+(.+)$/);
    if (device && current) current.devices.push({ id: number(device[1]), sizeBytes: number(device[2]), usedBytes: number(device[3]), path: device[4].trim() });
  }
  return filesystems;
}

export function parseBtrfsStats(text, device) {
  const counters = {};
  for (const line of String(text ?? "").split(/\r?\n/)) {
    const match = line.match(/\.(write_io_errs|read_io_errs|flush_io_errs|corruption_errs|generation_errs)\s+(\d+)$/);
    if (match) counters[match[1]] = number(match[2]);
  }
  for (const name of ["write_io_errs", "read_io_errs", "flush_io_errs", "corruption_errs", "generation_errs"]) counters[name] ??= 0;
  const totalErrors = Object.values(counters).reduce((sum, value) => sum + value, 0);
  return { device, ...counters, totalErrors, status: totalErrors > 0 ? "attention" : "healthy" };
}

export function parseMdstat(text) {
  const arrays = [];
  for (const line of String(text ?? "").split(/\r?\n/)) {
    const match = line.match(/^(md\d+)\s*:\s*(active|inactive)\s+(\S+)\s+(.+)$/);
    if (match) arrays.push({ name: match[1], active: match[2] === "active", level: match[3], members: match[4].trim() });
  }
  return arrays;
}

export function parseDf(text) {
  const rows = [];
  for (const line of String(text ?? "").split(/\r?\n/).slice(1)) {
    const match = line.trim().match(/^(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%\s+(.+)$/);
    if (!match) continue;
    const filesystem = match[2];
    const target = match[7].replace(/^\/host/, "") || "/";
    if (!(target === "/DATA" || target.startsWith("/DATA/") || target === "/media" || target.startsWith("/media/"))) continue;
    if (target.includes("/docker/overlay2/") || target.includes("/merged/host/")) continue;
    const usedPercent = number(match[6]);
    const readOnlyMedia = ["iso9660", "squashfs"].includes(filesystem);
    rows.push({
      source: match[1],
      filesystem,
      sizeBytes: number(match[3]),
      usedBytes: number(match[4]),
      availableBytes: number(match[5]),
      usedPercent,
      target,
      readOnlyMedia,
      status: readOnlyMedia ? "informational" : usedPercent >= 95 ? "critical" : usedPercent >= 85 ? "attention" : "healthy",
    });
  }
  const preferred = new Map();
  const targetRank = (target) => target.startsWith("/media/") ? 0 : target.startsWith("/DATA/.media/") ? 2 : 1;
  for (const row of rows) {
    const existing = preferred.get(row.source);
    if (!existing || targetRank(row.target) < targetRank(existing.target) || (targetRank(row.target) === targetRank(existing.target) && row.target.length < existing.target.length)) {
      preferred.set(row.source, row);
    }
  }
  return [...preferred.values()];
}
