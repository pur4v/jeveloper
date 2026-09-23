#!/usr/bin/env python3
"""jev_setkey.py — store a Jev API key the user pasted, so the Bash CLIs run live.

Human-in-the-loop fallback: when no key can be found anywhere (Jev keeps coming back mock),
Claude asks the user for their key and — with the user's explicit permission — runs this to
cache it. Writes to ~/.config/claude/.jeveloper-key (0600); works in every terminal after.

Usage:
  jev_setkey.py <KEY>                     # defaults to OpenRouter
  jev_setkey.py --typesafe <KEY>          # TypeSafe native
  jev_setkey.py OPENROUTER_API_KEY <KEY>  # explicit env-var name
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_color as clr  # noqa: E402
import jev_config as cfg_mod  # noqa: E402


def main(argv: list[str]) -> int:
    args = list(argv)
    name = "OPENROUTER_API_KEY"
    if args and args[0] in ("--typesafe", "--direct", "--native"):
        name, args = "TYPESAFE_API_KEY", args[1:]
    if len(args) == 2 and args[0].endswith("_API_KEY"):
        name, key = args[0], args[1]
    elif len(args) == 1:
        key = args[0]
    else:
        sys.stderr.write(__doc__ or "")
        return 2

    if cfg_mod.set_key(name, key):
        sys.stderr.write(clr.jev(
            f"stored {name} — Jev is now live in this and future terminals "
            f"(cached 0600 at {cfg_mod._KEY_CACHE})") + "\n")
        return 0
    sys.stderr.write(clr.err("could not store the key (empty/too short or path unwritable)") + "\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
