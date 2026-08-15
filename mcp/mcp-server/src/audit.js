import { appendFile, mkdir, readFile } from "node:fs/promises";

const auditPath = process.env.AUDIT_PATH ?? "/data/audit.jsonl";

export async function writeAudit(entry) {
  await mkdir(new URL(".", `file://${auditPath}`).pathname, { recursive: true });
  const record = { timestamp: new Date().toISOString(), ...entry };
  await appendFile(auditPath, `${JSON.stringify(record)}\n`, { encoding: "utf8", mode: 0o600 });
}

export async function readAudit(limit = 20) {
  try {
    const text = await readFile(auditPath, "utf8");
    return text
      .trim()
      .split("\n")
      .filter(Boolean)
      .slice(-limit)
      .reverse()
      .map((line) => JSON.parse(line));
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}
