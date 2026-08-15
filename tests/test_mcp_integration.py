import json
import os
import sys
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
if APP not in sys.path:
    sys.path.insert(0, APP)

from brain import mcp_evidence
from brain.mcp_client import McpClientError, ZimaBrainMcpClient


class _Response:
    def __init__(self, payload=None, headers=None):
        self.payload = b"" if payload is None else json.dumps(payload).encode()
        self.headers = headers or {"content-type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class McpClientTests(unittest.TestCase):
    def test_session_initialization_and_read_only_call(self):
        seen = []

        def fake_open(request, timeout):
            payload = json.loads(request.data) if request.data else None
            seen.append((request.method, payload, dict(request.header_items())))
            if payload and payload.get("method") == "initialize":
                return _Response(
                    {"jsonrpc": "2.0", "id": payload["id"], "result": {"protocolVersion": "2025-06-18"}},
                    {"content-type": "application/json", "mcp-session-id": "test-session"},
                )
            if payload and payload.get("method") == "notifications/initialized":
                return _Response()
            if payload and payload.get("method") == "tools/call":
                return _Response({"jsonrpc": "2.0", "id": payload["id"], "result": {"structuredContent": {"hostname": "cube"}}})
            return _Response()

        with mock.patch("urllib.request.urlopen", side_effect=fake_open):
            with ZimaBrainMcpClient("http://mcp.test/mcp") as client:
                self.assertEqual(client.call_tool("system_info"), {"hostname": "cube"})

        self.assertEqual(seen[0][1]["method"], "initialize")
        self.assertEqual(seen[2][1]["params"]["name"], "system_info")
        self.assertTrue(any(method == "DELETE" for method, _payload, _headers in seen))

    def test_client_rejects_actions_and_bad_targets_before_network(self):
        client = ZimaBrainMcpClient("http://mcp.test/mcp")
        client.session_id = "session"
        with self.assertRaises(McpClientError):
            client.call_tool("docker_restart", {"container": "x"})
        with self.assertRaises(McpClientError):
            client.call_tool("docker_logs", {"container": "bad/name"})

    def test_storage_tools_accept_no_user_arguments(self):
        client = ZimaBrainMcpClient("http://mcp.test/mcp")
        for tool in ("storage_inventory", "filesystem_usage", "smart_health", "nvme_health", "btrfs_health", "raid_health"):
            self.assertEqual(client._validated_arguments(tool, {}), {})
            with self.assertRaises(McpClientError):
                client._validated_arguments(tool, {"device": "/dev/sda"})


class EvidenceAdapterTests(unittest.TestCase):
    def test_broad_storage_question_calls_all_six_storage_tools(self):
        client = mock.MagicMock()
        client.__enter__.return_value = client
        client.list_tools.return_value = [{"name": name} for name in sorted(mcp_evidence.ALLOWED_TOOLS)]
        client.call_tool.side_effect = lambda tool, _arguments: {"tool": tool, "status": "success"}
        base = {
            "status": "connected",
            "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
            "calls": [],
            "results": {},
        }

        with mock.patch.object(mcp_evidence, "ZimaBrainMcpClient", return_value=client):
            snapshot = mcp_evidence.collect_question_evidence("Check all storage health for disk problems", base=base)

        self.assertEqual(set(snapshot["calls"]), set(mcp_evidence.STORAGE_TOOLS) | {"storage_mounts"})
        for tool in mcp_evidence.STORAGE_TOOLS:
            client.call_tool.assert_any_call(tool, {})

    def test_critical_filesystem_question_calls_capacity_tool(self):
        client = mock.MagicMock()
        client.__enter__.return_value = client
        client.list_tools.return_value = [{"name": name} for name in sorted(mcp_evidence.ALLOWED_TOOLS)]
        client.call_tool.side_effect = lambda tool, _arguments: {"tool": tool, "status": "success"}
        base = {
            "status": "connected",
            "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
            "calls": [],
            "results": {},
        }

        with mock.patch.object(mcp_evidence, "ZimaBrainMcpClient", return_value=client):
            snapshot = mcp_evidence.collect_question_evidence(
                "Are any filesystems critically full? Explain any read-only media showing 100% used.",
                base=base,
            )

        self.assertIn("filesystem_usage", snapshot["calls"])
        client.call_tool.assert_any_call("filesystem_usage", {})

    def test_inspect_restart_count_does_not_call_logs(self):
        client = mock.MagicMock()
        client.__enter__.return_value = client
        client.list_tools.return_value = [{"name": name} for name in sorted(mcp_evidence.ALLOWED_TOOLS)]
        client.call_tool.side_effect = lambda tool, _arguments: {
            "docker_ps": {
                "items": [
                    {
                        "name": "zimabrain-mcp-server",
                        "image": "zimabrain/mcp",
                        "state": "running",
                    }
                ]
            },
            "docker_inspect": {
                "name": "zimabrain-mcp-server",
                "state": {"running": True, "status": "running"},
                "security": {"privileged": False},
                "restartCount": 0,
            },
        }[tool]
        base = {
            "status": "connected",
            "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
            "calls": [],
            "results": {"docker_ps": client.call_tool("docker_ps", {})},
        }
        client.reset_mock()

        with mock.patch.object(mcp_evidence, "ZimaBrainMcpClient", return_value=client):
            snapshot = mcp_evidence.collect_question_evidence(
                "Inspect zimabrain-mcp-server and tell me whether it is running, healthy, privileged and how many times it has restarted.",
                base=base,
            )

        called_tools = [call.args[0] for call in client.call_tool.call_args_list]
        self.assertIn("docker_inspect", called_tools)
        self.assertNotIn("docker_logs", called_tools)
        self.assertEqual(snapshot["calls"], ["docker_inspect"])

    def test_legacy_translation_contains_no_process_arguments(self):
        snapshot = {
            "status": "connected",
            "results": {
                "docker_ps": {"items": [{"name": "app", "image": "safe/image", "status": "Up", "ports": []}]},
                "storage_mounts": {"items": [{"source": "/dev/sda", "target": "/DATA", "filesystem": "ext4", "options": ["rw"]}]},
                "system_processes": {"items": [{"pid": 5, "parentPid": 1, "name": "worker", "state": "S", "cpuTicks": 4, "residentMemoryBytes": 9, "args": "SECRET"}]},
            },
        }
        translated = mcp_evidence.legacy_overrides(snapshot)
        self.assertIn("app|safe/image|Up", translated["docker_ps"])
        self.assertIn('TARGET="/DATA"', translated["mcp_storage_mounts"])
        self.assertNotIn("SECRET", translated["mcp_processes"])

    def test_answer_block_is_honest_about_hybrid_mode(self):
        block = mcp_evidence.render_answer_evidence(
            {
                "status": "connected",
                "generatedAt": "now",
                "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
                "calls": ["system_info"],
                "results": {"system_info": {"hostname": "cube", "os": "ZimaOS", "cpuCount": 12}},
            }
        )
        self.assertIn("read-only", block)
        self.assertIn("append-only MCP ledger", block)
        self.assertIn("until MCP parity is complete", block)

    def test_evidence_time_is_rendered_in_sydney_time(self):
        with mock.patch.dict(os.environ, {"TZ": "Australia/Sydney"}):
            block = mcp_evidence.render_answer_evidence(
                {
                    "status": "connected",
                    "generatedAt": "2026-08-15T16:33:39+00:00",
                    "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
                    "calls": [],
                    "results": {},
                }
            )
        self.assertIn("2026-08-16 02:33:39 AEST", block)

    def test_system_answer_is_plain_english_and_complete(self):
        answer = mcp_evidence.render_mcp_direct_answer(
            {
                "status": "connected",
                "results": {
                    "system_info": {
                        "os": "ZimaOS v1.7.1-beta1",
                        "osVersion": "1.7.1-beta1",
                        "cpuModel": "Example CPU",
                        "cpuCount": 12,
                        "totalMemoryBytes": 16 * 1024 ** 3,
                        "availableMemoryBytes": 6 * 1024 ** 3,
                    }
                },
            },
            "What operating system, CPU and memory does this ZimaCube have?",
        )
        self.assertIn("Your ZimaCube is running ZimaOS", answer)
        self.assertIn("Example CPU", answer)
        self.assertIn("16.00 GiB", answer)

    def test_targeted_log_answer_does_not_invent_an_error(self):
        answer = mcp_evidence.render_targeted_container_answer(
            {
                "status": "connected",
                "generatedAt": "now",
                "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
                "calls": ["docker_inspect", "docker_logs"],
                "results": {
                    "docker_inspect": {
                        "name": "zimabrain-mcp-server",
                        "state": {"running": True, "status": "running", "health": {"status": "healthy"}},
                        "security": {"privileged": False},
                        "restartCount": 0,
                    },
                    "docker_logs": {
                        "container": "zimabrain-mcp-server",
                        "returnedLines": 1,
                        "requestedTail": 80,
                        "lines": ["ZimaBrain MCP server listening on 8718"],
                    },
                    "system_info": {"hostname": "cube", "os": "ZimaOS", "cpuCount": 12},
                },
            },
            "Check the recent logs for zimabrain-mcp-server and identify any verified errors. Do not guess",
        )
        self.assertIn("Plain-English answer", answer)
        self.assertIn("did not find an error marker", answer)
        self.assertIn("PARTIALLY VERIFIED", answer)
        self.assertNotIn("whole-system assessment", answer)

    def test_process_answer_is_live_mcp_focused(self):
        answer = mcp_evidence.render_targeted_process_answer(
            {
                "status": "connected",
                "generatedAt": "2026-08-15T16:33:39+00:00",
                "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
                "calls": ["system_info", "system_processes"],
                "results": {
                    "system_info": {"hostname": "cube", "os": "ZimaOS", "cpuCount": 12},
                    "system_processes": {
                        "sampleWindowMs": 300,
                        "hostCpuBusyPercent": 6.15,
                        "items": [{"pid": 10, "name": "node", "cpuPercentOfHost": 3.3, "cpuPercentOfCore": 39.6}],
                    },
                },
            },
            "Which processes are currently using the most CPU, and is there verified evidence of high CPU pressure?",
        )
        self.assertIn("VERIFIED FROM LIVE BOUNDED MCP EVIDENCE", answer)
        self.assertIn("PID 10 `node`", answer)
        self.assertIn("does not show high host CPU pressure", answer)
        self.assertNotIn("memory in total", answer)

    def test_hybrid_heading_identifies_live_mcp(self):
        answer = mcp_evidence.mark_hybrid_mcp_verification(
            "@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT EVIDENCE\n"
            "- This answer is based on evidence found in the current report.\n"
            "- The answer uses current same-report Docker inspect evidence."
        )
        self.assertIn("LIVE MCP AND SAME-REPORT EVIDENCE", answer)
        self.assertIn("current read-only MCP Docker evidence", answer)

    def test_storage_answer_is_conversational_and_does_not_call_crc_a_disk_failure(self):
        answer = mcp_evidence.render_targeted_storage_answer(
            {
                "status": "connected",
                "generatedAt": "2026-08-15T21:00:00+00:00",
                "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
                "calls": ["smart_health", "nvme_health", "btrfs_health", "raid_health"],
                "results": {
                    "system_info": {"hostname": "cube", "os": "ZimaOS", "cpuCount": 12},
                    "smart_health": {
                        "devices": [
                            {
                                "device": "/dev/sda",
                                "model": "WDC WD40EFPX",
                                "status": "attention",
                                "temperatureC": 29,
                                "smartPassed": True,
                                "reallocatedSectors": 0,
                                "pendingSectors": 0,
                                "offlineUncorrectable": 0,
                                "crcErrors": 8,
                                "findings": [{"code": "crc_errors", "message": "8 historical UDMA CRC errors were recorded; monitor whether this count increases."}],
                            }
                        ]
                    },
                    "nvme_health": {
                        "devices": [
                            {
                                "device": "/dev/nvme0",
                                "model": "Samsung SSD 990 PRO",
                                "status": "healthy",
                                "healthVerified": True,
                                "temperatureC": 35.9,
                                "criticalWarning": 0,
                                "mediaErrors": 0,
                                "percentageUsed": 0,
                                "findings": [],
                            }
                        ]
                    },
                    "btrfs_health": {"observedFilesystems": 5, "multiDeviceFilesystems": 0, "errorCount": 0, "status": "healthy"},
                    "raid_health": {"configured": False, "status": "not_applicable", "zfs": {"kernelLoaded": True, "configured": False, "pools": []}},
                },
            },
            "Are any disks reporting SMART, NVMe, Btrfs or RAID problems?",
        )
        self.assertIn("VERIFIED FROM LIVE MCP STORAGE EVIDENCE", answer)
        self.assertIn("CRC=8", answer)
        self.assertIn("monitor whether this count increases", answer)
        self.assertIn("cable, connector or backplane", answer)
        self.assertIn("ZFS kernel module is loaded", answer)
        self.assertIn("RAID is not configured", answer)
        self.assertNotIn("SMART failed", answer)
        self.assertIn("main MCP server has no `/dev` access", answer)

    def test_nvme_answer_abstains_when_admin_counters_are_blocked(self):
        answer = mcp_evidence.render_targeted_storage_answer(
            {
                "status": "connected",
                "generatedAt": "2026-08-15T21:00:00+00:00",
                "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
                "calls": ["nvme_health"],
                "results": {
                    "system_info": {"hostname": "cube", "os": "ZimaOS", "cpuCount": 12},
                    "nvme_health": {
                        "observedDevices": 1,
                        "unverifiedCount": 1,
                        "devices": [
                            {
                                "device": "/dev/nvme0",
                                "model": "Samsung SSD 990 PRO",
                                "controllerState": "live",
                                "temperatureC": 36.9,
                                "healthVerified": False,
                                "status": "unknown",
                                "findings": [{"code": "nvme_smart_unavailable", "level": "unknown"}],
                            }
                        ],
                    },
                },
            },
            "Are my NVMe drives healthy? Include temperature, endurance used and media errors.",
        )
        self.assertIn("PARTIALLY VERIFIED", answer)
        self.assertIn("36.9°C", answer)
        self.assertIn("endurance, media-error and critical-warning counters are not verified", answer)
        self.assertNotIn("None%", answer)
        self.assertNotIn("is healthy", answer)

    def test_filesystem_capacity_answer_explains_full_read_only_media(self):
        answer = mcp_evidence.render_targeted_storage_answer(
            {
                "status": "connected",
                "generatedAt": "2026-08-15T23:38:57+00:00",
                "availableTools": sorted(mcp_evidence.ALLOWED_TOOLS),
                "calls": ["filesystem_usage"],
                "results": {
                    "filesystem_usage": {
                        "attentionCount": 0,
                        "filesystems": [
                            {
                                "source": "/dev/sdd",
                                "filesystem": "iso9660",
                                "usedPercent": 100,
                                "target": "/media/sdc",
                                "readOnlyMedia": True,
                                "status": "informational",
                            }
                        ],
                    }
                },
            },
            "Are any filesystems critically full? Explain any read-only media showing 100% used.",
        )

        self.assertIn("0 require capacity attention", answer)
        self.assertIn("read-only iso9660 media", answer)
        self.assertIn("100% figure is normal and is not a capacity warning", answer)
        self.assertIn("MCP Storage and Disk Health Layer", answer)


if __name__ == "__main__":
    unittest.main()
