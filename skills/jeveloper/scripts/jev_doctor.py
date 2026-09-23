#!/usr/bin/env python3
"""jev_doctor.py — one health check: is jeveloper actually LIVE in this session?

jeveloper is designed to fail open and stay silent when it's off or keyless, so the dominant
failure mode is that a mistyped key or an unregistered hook makes the whole plugin quietly do
nothing. This prints, in one shot: master switch, key detection, a real live probe, each
reflex's on/off + live/MOCK state, config-file validity, and hook registration — with the
exact fix for every red line. Diagnostic only; never changes anything, always exits 0.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402
import jev_color as clr  # noqa: E402
import jev_config as cfg_mod  # noqa: E402


def main() -> None:
    cfg = cfg_mod.load_config()
    ok = "✓"
    bad = "✗"
    lines = ["jeveloper — doctor", ""]

    enabled = bool(cfg.get("enabled"))
    key = cfg_mod._key_present(cfg)
    lines.append(f"  {ok if enabled else bad} enabled: {enabled}   (config 'enabled'={cfg.get('enabled')!r})")
    lines.append(f"  {ok if key else bad} Jev key: {'found' if key else 'MISSING'}")
    if not key:
        lines.append("      fix: set OPENROUTER_API_KEY (or TYPESAFE_API_KEY) in this session's")
        lines.append("           environment, or install via /plugin so the key is injected.")

    probe = jc.ask({"ping": "doctor"}, {"healthy": jc.noul("This is a health probe.")}, kind="ask")
    live = not probe.get("mock")
    lines.append(f"  {ok if live else bad} live probe: {'LIVE (real Jev decision)' if live else 'MOCK (no real decision)'}")
    if not live and key:
        err = probe.get("error")
        lines.append(f"      fix: probe did not reach Jev{' — ' + err if err else ''};")
        lines.append("           check the key value, provider, and network.")

    lines.append("  reflexes:")
    for mode in ("drive", "route", "check", "warden"):
        on = cfg_mod.mode_enabled(cfg, mode)
        note = "" if (live or not on) else "  (ON but will MOCK — no key)"
        lines.append(f"      {ok if on else '·'} {mode:7} {'on' if on else 'off'}{note}")

    cpath = os.path.join(os.getcwd(), ".jeveloper.json")
    if os.path.exists(cpath):
        try:
            json.load(open(cpath, encoding="utf-8"))
            lines.append(f"  {ok} .jeveloper.json: valid")
        except ValueError as e:
            lines.append(f"  {bad} .jeveloper.json: INVALID JSON — {e}")
            lines.append(f"      fix: correct or delete {cpath}")
    else:
        lines.append(f"  {ok} .jeveloper.json: none (defaults; enabled='auto' → on when a key is present)")

    root_env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root_env:
        hp = os.path.join(root_env, "hooks", "hooks.json")
        found = os.path.exists(hp)
        lines.append(f"  {ok if found else bad} hooks.json: {'registered' if found else 'MISSING'}")

    lines.append("")
    verdict = "LIVE — jeveloper is working." if (enabled and live) else "NOT live — fix the red (✗) lines above."
    lines.append(f"  verdict: {verdict}")
    out = []
    for ln in lines:
        if "✗" in ln or ln.strip().startswith("fix:"):
            out.append(clr.paint(ln, "err"))
        elif "verdict:" in ln:
            out.append(clr.paint(ln, "jev" if "LIVE" in ln else "err"))
        elif "✓" in ln:
            out.append(clr.paint(ln, "ok"))
        elif ln == "jeveloper — doctor":
            out.append(clr.paint(ln, "bold"))
        else:
            out.append(ln)
    print("\n".join(out))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # diagnostic must never crash the session
        print(f"jeveloper doctor error: {exc}")
        sys.exit(0)
