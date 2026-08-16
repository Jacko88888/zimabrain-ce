import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parent


class StorageBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
        cls.storage = yaml.safe_load((ROOT / "docker-compose.storage.yml").read_text(encoding="utf-8"))

    def test_collector_has_no_host_port_and_fixed_security_boundary(self):
        collector = self.storage["services"]["zimabrain-storage-collector"]
        self.assertNotIn("ports", collector)
        self.assertTrue(collector["read_only"])
        self.assertEqual(collector["cap_drop"], ["ALL"])
        self.assertEqual(collector["cap_add"], ["SYS_RAWIO"])
        self.assertEqual(collector["security_opt"], ["no-new-privileges:true"])
        self.assertTrue(all(str(device).endswith(":r") for device in collector["devices"]))
        self.assertNotIn("/dev:/dev", collector["devices"])

    def test_main_mcp_server_remains_device_free_and_non_root(self):
        server = self.base["services"]["zimabrain-mcp-server"]
        self.assertNotIn("devices", server)
        self.assertEqual(server["cap_drop"], ["ALL"])
        dockerfile = (ROOT / "Dockerfile.mcp").read_text(encoding="utf-8")
        self.assertIn("USER node", dockerfile)

    def test_collector_reuses_existing_internal_network(self):
        collector = self.storage["services"]["zimabrain-storage-collector"]
        self.assertEqual(collector["networks"], ["docker-api"])
        self.assertNotIn("networks", self.storage)
        self.assertTrue(self.base["networks"]["docker-api"]["internal"])

    def test_collector_uses_execfile_and_has_no_shell_execution(self):
        collector = (ROOT / "storage-collector/src/collector.js").read_text(encoding="utf-8")
        self.assertIn("execFile", collector)
        self.assertNotIn("exec(", collector)
        self.assertNotIn("shell:", collector)


if __name__ == "__main__":
    unittest.main()
