"""Tests for get_script_source() and replace_in_script().

Run WITHOUT a Frida device — fake session only.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import frida_game_hacking_mcp.server as srv


class FakeScript:
    def __init__(self, code):
        self.code = code
        self.loaded = False
        self.unloaded = False
        self._handler = None

    def on(self, event, handler):
        self._handler = handler

    def load(self):
        self.loaded = True

    def unload(self):
        self.unloaded = True


class FakeSession:
    is_detached = False

    def __init__(self):
        self.scripts = []

    def create_script(self, code):
        s = FakeScript(code)
        self.scripts.append(s)
        return s


def _setup():
    srv._session.device = None
    srv._session.session = FakeSession()
    srv._session.pid = 1
    srv._session.process_name = "fake"
    srv._session.spawned = False
    srv._session.custom_scripts.clear()
    srv._session.script_messages.clear()
    srv._session.script_sources.clear()
    srv.FRIDA_AVAILABLE = True
    srv.load_script("var a = 1;\nvar b = Module.findBaseAddress('x');\n", "t")


def test_get_script_source_returns_stored_source():
    _setup()
    result = srv.get_script_source("t")
    assert result["success"] is True
    assert "Module.findBaseAddress" in result["source"]


def test_get_script_source_missing_script():
    _setup()
    result = srv.get_script_source("nope")
    assert "error" in result


def test_replace_in_script_reloads_with_new_source():
    _setup()
    old_script = srv._session.custom_scripts["t"]
    result = srv.replace_in_script(
        "t",
        "Module.findBaseAddress('x')",
        "Process.findModuleByName('x').base",
    )
    assert result.get("success") is True
    assert old_script.unloaded is True
    new_script = srv._session.custom_scripts["t"]
    assert new_script is not old_script
    assert new_script.loaded is True
    assert "Process.findModuleByName" in srv._session.script_sources["t"]
    assert "Module.findBaseAddress" not in srv._session.script_sources["t"]


def test_replace_in_script_not_found():
    _setup()
    before = srv._session.script_sources["t"]
    result = srv.replace_in_script("t", "nonexistent_text", "x")
    assert "error" in result
    assert srv._session.script_sources["t"] == before
    assert srv._session.custom_scripts["t"].unloaded is False


def test_replace_in_script_multiple_matches():
    _setup()
    srv._session.script_sources["t"] = "a = 1;\na = 2;\na = 3;"
    result = srv.replace_in_script("t", "a =", "b =")
    assert "error" in result
    assert "3 times" in result["error"]


def test_replace_in_script_missing_script():
    _setup()
    result = srv.replace_in_script("nope", "a", "b")
    assert "error" in result
