#!/usr/bin/env python3
"""jev_config.py — shared config + stdin/stdout plumbing for the jeveloper hooks.

The three hooks (route_gate, check_output, warden) are inert until jeveloper is
explicitly enabled, so installing the plugin never surprises anyone by gating tool
calls. Enable per project with `/jeveloper:setup` (writes `.jeveloper.json`) or by
exporting JEVELOPER_ENABLED=1.

Config resolution (later wins):
  1. built-in DEFAULTS below
  2. `.jeveloper.json` in the current working directory (the project root)
  3. JEVELOPER_ENABLED=1 / JEVELOPER_ENABLED=0 environment override of the master switch
"""
from __future__ import annotations

import json
import os
import sys

DEFAULTS: dict = {
    # Master switch. Ships OFF: the plugin does nothing until you opt in.
    "enabled": False,
    # A standing objective the warden judges "done-ness" against. Optional; when
    # empty the warden falls back to the transcript's own most recent user request.
    "goal": "",
    "route": {
        "enabled": True,
        # Only these tools are gated (a matcher is also set in hooks.json; this is
        # the second, finer gate). Empty list = gate everything the hook receives.
        "tools": ["Bash"],
        # P(unsafe) at/above this -> deny; at/above ask_threshold -> ask; else allow.
        "deny_threshold": 0.85,
        "ask_threshold": 0.60,
    },
    "check": {
        "enabled": True,
        # P(the output is a failure/does-not-satisfy-intent) at/above this -> feed
        # the concern back to Claude as blocking PostToolUse context.
        "fail_threshold": 0.80,
    },
    "warden": {
        "enabled": True,
        # Score 0..10 of how complete the task is. Below this -> keep the loop going.
        "done_threshold": 7.0,
        # Hard cap on how many times the warden may re-open the loop in a row, so a
        # stubborn task can never trap the session in an infinite continue.
        "max_continues": 3,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(cwd: str | None = None) -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
    root = cwd or os.getcwd()
    path = os.path.join(root, ".jeveloper.json")
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = _deep_merge(cfg, json.load(fh))
    except (OSError, ValueError):
        pass  # no file / bad file -> defaults (which are OFF)

    env = os.environ.get("JEVELOPER_ENABLED")
    if env is not None:
        cfg["enabled"] = env not in ("0", "false", "False", "")
    return cfg


def mode_enabled(cfg: dict, mode: str) -> bool:
    return bool(cfg.get("enabled")) and bool(cfg.get(mode, {}).get("enabled"))


def read_hook_input() -> dict:
    """Parse the JSON Claude Code sends a hook on stdin. Never raises."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        return {}


def emit(obj: dict) -> None:
    """Print a hook JSON result to stdout."""
    sys.stdout.write(json.dumps(obj))
    sys.stdout.flush()


def fail_open(reason: str = "") -> None:
    """Exit 0 with no decision — the safe default whenever jeveloper has no opinion
    (disabled, mock/keyless, Jev unreachable, or below threshold)."""
    if reason and os.environ.get("JEVELOPER_DEBUG"):
        sys.stderr.write(f"[jeveloper] fail-open: {reason}\n")
    sys.exit(0)
