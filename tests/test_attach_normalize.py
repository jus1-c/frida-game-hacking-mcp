"""Tests for attach() target normalization.

These tests run WITHOUT a real Frida device — they monkeypatch the
server's device/session with fakes and assert what target type is
actually handed to device.attach().
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import frida_game_hacking_mcp.server as srv


class FakeDevice:
    def __init__(self):
        self.attach_calls = []

    def attach(self, target, **kwargs):
        self.attach_calls.append(target)
        return FakeSession()

    def enumerate_processes(self):
        return []


class FakeSession:
    is_detached = False


def _setup(target):
    """Install fakes and return (device, result)."""
    device = FakeDevice()
    srv._session.device = device
    srv._session.session = None
    srv._session.pid = None
    srv._session.process_name = None
    srv._session.spawned = False
    # FRIDA_AVAILABLE is True in this env; force it anyway for safety
    srv.FRIDA_AVAILABLE = True
    result = srv.attach(target)
    return device, result


def test_attach_numeric_string_coerced_to_int():
    """attach("15400") must call device.attach(15400) with an int.

    Regression: MCP clients often send the PID as a string; the old code
    passed it through as a string, which Frida treats as a process NAME,
    raising ProcessNotFoundError.
    """
    device, result = _setup("15400")
    assert device.attach_calls == [15400], device.attach_calls
    assert result.get("success") is True


def test_attach_int_passed_through():
    device, result = _setup(15400)
    assert device.attach_calls == [15400], device.attach_calls
    assert result.get("success") is True


def test_attach_name_kept_as_string():
    device, result = _setup("StarSEA.exe")
    assert device.attach_calls == ["StarSEA.exe"], device.attach_calls
    assert result.get("success") is True