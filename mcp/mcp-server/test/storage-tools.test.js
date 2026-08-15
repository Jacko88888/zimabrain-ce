import test from "node:test";
import assert from "node:assert/strict";

test("storage adapter calls only fixed collector endpoints", async () => {
  const seen = [];
  globalThis.fetch = async (url) => {
    seen.push(String(url));
    return {
      ok: true,
      async json() {
        return { collectorStatus: "success", generatedAt: "2026-08-16T00:00:00Z", observedDevices: 1, devices: [] };
      },
    };
  };
  const evidence = await import(`../src/evidence.js?test=${Date.now()}`);
  await evidence.storageInventory();
  await evidence.filesystemUsage();
  await evidence.smartHealth();
  await evidence.nvmeHealth();
  await evidence.btrfsHealth();
  await evidence.raidHealth();
  assert.deepEqual(
    seen.map((url) => url.split("/").at(-1)),
    ["inventory", "filesystems", "smart", "nvme", "btrfs", "raid"],
  );
});
