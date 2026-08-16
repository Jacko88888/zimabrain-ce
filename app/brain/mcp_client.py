"""Small, bounded MCP Streamable HTTP client for ZimaBrain CE.

The client deliberately exposes only the thirteen read-only tools published by the
local ZimaBrain MCP server.  It uses only Python's standard library so the Brain
does not need an additional runtime dependency.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


DEFAULT_MCP_URL = ""
PROTOCOL_VERSION = "2025-06-18"
ALLOWED_TOOLS = frozenset(
    {
        "system_info",
        "storage_mounts",
        "storage_inventory",
        "filesystem_usage",
        "smart_health",
        "nvme_health",
        "btrfs_health",
        "raid_health",
        "docker_ps",
        "docker_images",
        "docker_inspect",
        "docker_logs",
        "system_processes",
    }
)
CONTAINER_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class McpClientError(RuntimeError):
    pass


class ZimaBrainMcpClient:
    def __init__(self, url=None, timeout=None):
        self.url = (url or os.environ.get("ZIMABRAIN_MCP_URL") or DEFAULT_MCP_URL).strip()
        self.timeout = float(timeout or os.environ.get("ZIMABRAIN_MCP_TIMEOUT", "6"))
        self.session_id = ""
        self._request_id = 0

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    @staticmethod
    def _decode_response(raw, content_type):
        text = raw.decode("utf-8", errors="replace")
        if "text/event-stream" not in (content_type or "").lower():
            return json.loads(text) if text.strip() else {}

        events = []
        for line in text.splitlines():
            if line.startswith("data:"):
                value = line[5:].strip()
                if value:
                    events.append(json.loads(value))
        if not events:
            raise McpClientError("MCP server returned an empty event stream")
        return events[-1]

    def _send(self, payload=None, method="POST", require_session=True):
        if not self.url:
            raise McpClientError("ZIMABRAIN_MCP_URL is not configured")
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id
        elif require_session:
            raise McpClientError("MCP session has not been initialized")

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(self.url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                session_id = response.headers.get("mcp-session-id")
                if session_id:
                    self.session_id = session_id
                return self._decode_response(response.read(), response.headers.get("content-type", ""))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise McpClientError(f"MCP request failed: {error}") from error

    @staticmethod
    def _result_value(message):
        if not isinstance(message, dict):
            raise McpClientError("MCP response was not an object")
        if message.get("error"):
            error = message["error"]
            raise McpClientError(str(error.get("message") if isinstance(error, dict) else error))
        return message.get("result", {})

    def initialize(self):
        if self.session_id:
            return
        message = self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "zimabrain-ce", "version": "1.7.0-mcp-preview"},
                },
            },
            require_session=False,
        )
        self._result_value(message)
        if not self.session_id:
            raise McpClientError("MCP server did not issue a session ID")
        self._send(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )

    def list_tools(self):
        result = self._result_value(
            self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list", "params": {}})
        )
        tools = result.get("tools", []) if isinstance(result, dict) else []
        return [tool for tool in tools if tool.get("name") in ALLOWED_TOOLS]

    @staticmethod
    def _validated_arguments(tool, arguments):
        arguments = dict(arguments or {})
        if tool in {
            "system_info",
            "storage_mounts",
            "storage_inventory",
            "filesystem_usage",
            "smart_health",
            "nvme_health",
            "btrfs_health",
            "raid_health",
            "docker_ps",
            "docker_images",
        }:
            if arguments:
                raise McpClientError(f"{tool} does not accept arguments")
            return {}
        if tool in {"docker_inspect", "docker_logs"}:
            container = str(arguments.get("container", ""))
            if not CONTAINER_REFERENCE.fullmatch(container):
                raise McpClientError("An exact, valid container name or ID is required")
            clean = {"container": container}
            if tool == "docker_logs":
                tail = int(arguments.get("tail", 100))
                if not 1 <= tail <= 200:
                    raise McpClientError("Log tail must be between 1 and 200")
                clean["tail"] = tail
            return clean
        if tool == "system_processes":
            sort = str(arguments.get("sort", "cpu"))
            limit = int(arguments.get("limit", 25))
            if sort not in {"cpu", "memory", "pid"} or not 1 <= limit <= 100:
                raise McpClientError("Invalid process sort or limit")
            return {"sort": sort, "limit": limit}
        raise McpClientError(f"Tool is not allow-listed: {tool}")

    def call_tool(self, tool, arguments=None):
        if tool not in ALLOWED_TOOLS:
            raise McpClientError(f"Tool is not allow-listed: {tool}")
        clean_arguments = self._validated_arguments(tool, arguments)
        result = self._result_value(
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "tools/call",
                    "params": {"name": tool, "arguments": clean_arguments},
                }
            )
        )
        if result.get("isError"):
            text = " ".join(
                str(item.get("text", "")) for item in result.get("content", []) if isinstance(item, dict)
            ).strip()
            raise McpClientError(text or f"MCP tool failed: {tool}")
        if "structuredContent" in result:
            return result["structuredContent"]
        for item in result.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                return json.loads(item.get("text", "{}"))
        raise McpClientError(f"MCP tool returned no structured evidence: {tool}")

    def close(self):
        if not self.session_id:
            return
        try:
            self._send(method="DELETE")
        except McpClientError:
            pass
        finally:
            self.session_id = ""
