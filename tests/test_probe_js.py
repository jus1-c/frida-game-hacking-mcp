"""Tests for the JS API-surface probe builder.

These tests run WITHOUT a Frida device — they only exercise the pure
string-building logic in server._build_probe_js.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frida_game_hacking_mcp.server import _build_probe_js, _CORE_NAMESPACES


def test_probe_js_has_outer_array():
    """The generated JS must wrap the namespace pairs in ONE outer array.

    Regression: the old code produced
        ["Frida","Frida"],["Process","Process"],...["Console","Console"].forEach(...)
    which the comma operator collapses to only the LAST pair iterating.
    """
    js = _build_probe_js([])
    # outer array must open before the first pair and close right before .forEach
    assert "[[" in js, "expected outer array wrapper, got: %r" % js[:120]
    assert "]].forEach" in js, "expected outer array to close before .forEach"


def test_probe_js_iterates_all_core_namespaces():
    """Every core namespace must appear as a pair inside the outer array."""
    js = _build_probe_js([])
    for key, path in _CORE_NAMESPACES:
        assert '["%s","%s"]' % (key, path) in js, "missing pair %s/%s" % (key, path)


def test_probe_js_whitelists_extras():
    """Whitelisted extras are included; unknown names are dropped."""
    js = _build_probe_js(["Stalker", "Bogus", "Socket"])
    assert '["Stalker","Stalker"]' in js
    assert '["Socket","Socket"]' in js
    assert "Bogus" not in js


def test_probe_js_extra_not_duplicated():
    """An extra that is already a core namespace must not be duplicated."""
    js = _build_probe_js(["Process"])
    assert js.count('["Process","Process"]') == 1