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
    # Master switch. "auto" (default) = ON whenever a Jev key is in the environment, OFF
    # otherwise — so installing + setting a key is all it takes, no config file needed.
    # Set true/false in .jeveloper.json (or JEVELOPER_ENABLED=1/0) to force it.
    "enabled": "auto",
    # Which Jev provider to use. "auto" = OpenRouter if OPENROUTER_API_KEY is set, else
    # TypeSafe native. Force one with "openrouter" or "direct" (aka "typesafe"). The key is
    # ALWAYS read from the environment (api_key_env names the var) — never stored here.
    "provider": {
        "use": "auto",          # auto | openrouter | direct
        "model": "",            # optional model-id override
        "api_url": "",          # optional endpoint override
        "api_key_env": "",      # optional: custom env var holding the key
    },
    # A standing objective the warden judges "done-ness" against. Optional; when
    # empty the warden falls back to the transcript's own most recent user request.
    "goal": "",
    # Jev drives every turn — the always-on ping-pong, injected by the UserPromptSubmit hook.
    "drive": {"enabled": True},
    "route": {
        "enabled": True,
        # Which tools the gate applies to. Empty list = gate EVERYTHING the hook receives
        # (hooks.json matcher is "*", so that's every tool). Narrow it here if the latency of
        # a Jev call on read-only tools isn't worth it.
        "tools": [],
        # P(unsafe) at/above this -> deny; at/above ask_threshold -> ask; else allow.
        "deny_threshold": 0.85,
        "ask_threshold": 0.60,
        # Jev-first: block the first substantive action of a turn until Jev has been consulted
        # (jev_next / jev_ask has run this turn), so the decision is offloaded to Jev before
        # Claude commits expensive reasoning to an action. Only enforced while `drive` is on
        # (drive resets the per-turn marker). Set false to disable the enforcement.
        "consult_first": True,
        "consult_tools": ["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "Task"],
    },
    "check": {
        "enabled": True,
        # P(the output is a failure/does-not-satisfy-intent) at/above this -> feed
        # the concern back to Claude as blocking PostToolUse context.
        "fail_threshold": 0.80,
    },
    "warden": {
        "enabled": True,
        # Score 0..10 of how complete the task is. At/above this the stop is allowed; below it
        # the loop keeps going. Completeness is the sole gate — the old `met` veto was dropped
        # (too noisy for text/advice turns); see warden.py.
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
    elif cfg.get("enabled") in ("auto", None):
        cfg["enabled"] = _key_present(cfg)  # zero-config: on when a key is set
    return cfg


def _key_present(cfg: dict) -> bool:
    names = ["OPENROUTER_API_KEY", "TYPESAFE_API_KEY"]
    custom = (cfg.get("provider") or {}).get("api_key_env")
    if custom:
        names.insert(0, custom)
    # A key may come from a plain env export OR from the plugin's userConfig prompt,
    # which Claude Code injects as CLAUDE_PLUGIN_OPTION_<NAME>. Accept either form.
    return any(os.environ.get(n) or os.environ.get("CLAUDE_PLUGIN_OPTION_" + n) for n in names)


def mode_enabled(cfg: dict, mode: str) -> bool:
    return bool(cfg.get("enabled")) and bool(cfg.get(mode, {}).get("enabled"))


def consult_marker_path() -> str:
    """Per-project marker recording whether Jev has been consulted in the current turn.

    Lives under the project's .jeveloper/ dir (keyed by cwd, like the metrics log) — NOT the
    temp dir: the Bash sandbox and the hook processes run with different TMPDIRs, so a
    tmp-based marker written by the Bash `jev_next` CLI is invisible to the gate hook. They
    do share the same cwd (that's how the meter works across both), so the project dir is the
    reliable common ground for the driver hook, the PreToolUse gate, and the jev_next/jev_ask
    CLI Claude runs.
    """
    return os.path.join(os.getcwd(), ".jeveloper", "consult.turn")


def mark_consulted() -> None:
    """Record that Jev was consulted this turn (best-effort; never raises)."""
    try:
        path = consult_marker_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("1")
    except OSError:
        pass


def reset_consulted() -> None:
    """Clear the per-turn consulted marker (best-effort; never raises)."""
    try:
        os.remove(consult_marker_path())
    except OSError:
        pass


def was_consulted() -> bool:
    return os.path.exists(consult_marker_path())


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
