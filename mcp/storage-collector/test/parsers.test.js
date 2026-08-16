import test from "node:test";
import assert from "node:assert/strict";
import { parseBtrfsFilesystems, parseBtrfsStats, parseDf, parseMdstat, parseNvme, parseSmart } from "../src/parsers.js";
import { countActionable } from "../src/collector.js";

test("SMART parser distinguishes a historical CRC warning from disk failure", () => {
  const result = parseSmart(
    {
      model_name: "WDC WD40EFPX",
      device: { protocol: "ATA" },
      smart_status: { passed: true },
      temperature: { current: 29 },
      power_on_time: { hours: 10753 },
      ata_smart_attributes: {
        table: [
          { id: 5, raw: { value: 0 } },
          { id: 197, raw: { value: 0 } },
          { id: 198, raw: { value: 0 } },
          { id: 199, raw: { value: 8 } },
        ],
      },
      ata_smart_error_log: { summary: { count: 0 } },
    },
    "/dev/sda",
  );
  assert.equal(result.smartPassed, true);
  assert.equal(result.status, "attention");
  assert.equal(result.crcErrors, 8);
  assert.equal(result.pendingSectors, 0);
  assert.match(result.findings[0].message, /monitor whether this count increases/);
});

test("NVMe parser converts Kelvin and preserves healthy evidence", () => {
  const result = parseNvme(
    {
      critical_warning: 0,
      temperature: 309,
      avail_spare: 100,
      spare_thresh: 10,
      percent_used: 0,
      media_errors: 0,
      num_err_log_entries: 0,
      unsafe_shutdowns: 332,
      power_on_hours: 729,
    },
    { mn: "Samsung SSD 990 PRO", fr: "5B2QJXD7" },
    "/dev/nvme0",
  );
  assert.equal(result.temperatureC, 35.9);
  assert.equal(result.status, "healthy");
  assert.equal(result.mediaErrors, 0);
});

test("Btrfs parser records single-device filesystems and clean counters", () => {
  const filesystems = parseBtrfsFilesystems(`Label: none  uuid: 33e02fc2-d982-43e2-bdd2-96c084c636bd
        Total devices 1 FS bytes used 785782386688
        devid    1 size 4000787030016 used 792446631936 path /dev/sda
`);
  assert.equal(filesystems.length, 1);
  assert.equal(filesystems[0].totalDevices, 1);
  assert.equal(filesystems[0].devices[0].path, "/dev/sda");

  const stats = parseBtrfsStats(`[/dev/sda].write_io_errs    0
[/dev/sda].read_io_errs     0
[/dev/sda].flush_io_errs    0
[/dev/sda].corruption_errs  0
[/dev/sda].generation_errs  0`, "/dev/sda");
  assert.equal(stats.status, "healthy");
  assert.equal(stats.totalErrors, 0);
});

test("RAID parser reports no arrays instead of inventing healthy RAID", () => {
  assert.deepEqual(parseMdstat("Personalities : \nunused devices: <none>\n"), []);
});

test("filesystem parser deduplicates mounts and does not flag read-only ISO media", () => {
  const rows = parseDf(`Filesystem Type 1-blocks Used Available Capacity Mounted on
/dev/nvme3n1p8 ext4 1000 900 100 90% /host/DATA
/dev/sda btrfs 1000 100 900 10% /host/media/HDD-Storage
/dev/sdd iso9660 1000 1000 0 100% /host/DATA/.media/sdc
/dev/sdd iso9660 1000 1000 0 100% /host/media/docker/overlay2/id/merged/host/DATA/.media/sdc
/dev/sdd iso9660 1000 1000 0 100% /host/media/sdc
overlay overlay 1000 10 990 1% /
`);
  assert.equal(rows.length, 3);
  assert.equal(rows[0].target, "/DATA");
  assert.equal(rows[0].status, "attention");
  assert.equal(rows[2].target, "/media/sdc");
  assert.equal(rows[2].filesystem, "iso9660");
  assert.equal(rows[2].status, "informational");
  assert.equal(countActionable(rows), 1);
  assert.equal(countActionable([rows[2]]), 0);
});
