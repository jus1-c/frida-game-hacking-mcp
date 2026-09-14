"""Tests for get_js_api_surface() filter matching and _run_once error capture.

These run WITHOUT a Frida device: they exercise the pure filter logic and
the message-routing in _run_once via a fake session.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import frida_game_hacking_mcp.server as srv


class FakeScript:
    def __init__(self, messages):
        self._messages = messages
        self._handler = None

    def on(self, event, handler):
        self._handler = handler

    def load(self):
        for msg in self._messages:
            self._handler(msg, None)

    def unload(self):
        pass


class FakeSession:
    is_detached = False

    def __init__(self, messages):
        self._messages = messages

    def create_script(self, code):
        return FakeScript(self._messages)


def test_filter_matches_qualified_path():
    """filter="Process" must match members of the Process namespace."""
    surface = {"groups": {"Process": ["enumerateProcesses", "getModuleByName"],
                          "Module": ["getExportByName"]}}
    srv._session.js_surface = surface
    srv._session.session = FakeSession([])
    result = srv.get_js_api_surface(filter="Process")
    assert result["success"] is True
    assert "Process.enumerateProcesses" in result["matches"]
    assert "Process.getModuleByName" in result["matches"]
    assert "Module.getExportByName" not in result["matches"]


def test_filter_matches_member_substring():
    surface = {"groups": {"Module": ["getExportByName", "getBaseAddress"]}}
    srv._session.js_surface = surface
    srv._session.session = FakeSession([])
    result = srv.get_js_api_surface(filter="getExport")
    assert result["matches"] == ["Module.getExportByName"]


def test_run_once_captures_errors():
    """_run_once must append error messages to errors_out."""
    srv._session.session = FakeSession([
        {"type": "error", "description": "TypeError: not a function",
         "stack": "    at <eval> (script.js:3:15)"},
        {"type": "send", "payload": {"ok": True}},
    ])
    errors = []
    payloads = srv._run_once("ignored", errors_out=errors)
    assert payloads == [{"ok": True}]
    assert len(errors) == 1
    assert errors[0]["description"] == "TypeError: not a function"
    assert "script.js:3" in errors[0]["stack"]


def test_run_once_ignores_errors_without_errors_out():
    """Without errors_out, error messages stay swallowed (back-compat)."""
    srv._session.session = FakeSession([
        {"type": "error", "description": "boom", "stack": "x"},
        {"type": "send", "payload": "ok"},
    ])
    payloads = srv._run_once("ignored")
    assert payloads == ["ok"]