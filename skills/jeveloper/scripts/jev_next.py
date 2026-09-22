#!/usr/bin/env python3
"""jev_next.py — the decision primitive for the driver loop: Jev picks the next action.

This is the "Jev decides, Claude follows" half of the ping-pong. Instead of Claude spending
reasoning tokens deliberating which action to take, Claude cheaply *enumerates* 2–5 candidate
actions and hands them here; Jev (a `choice`, one fast call) returns the one to do next, with
per-option probabilities and a confidence. Claude then just executes it. The verify half is
the PostToolUse Check hook.

The same primitive does subagent selection — the candidate "actions" can be subagent/agent
types ("which agent should handle this?"). It's all one `choice` for Jev to judge.

Usage:
  jev_next.py "<state>" "<objective>" id1[:desc] id2[:desc] ...
  # or pipe a JSON list of {"id","label"} on stdin:
  echo '[{"id":"a","label":"..."}]' | jev_next.py "<state>" "<objective>" -

Prints JSON: {chosen, confidence, probabilities, mock, options}. On mock (no key) `chosen`
is the first option and `mock` is true — Claude should then decide for itself, not follow a
placeholder.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402


def choose(state: str, objective: str, options: list[dict]) -> dict:
    """options: list of {"id","label"}. Returns the decision dict."""
    opt_map = {o["id"]: o.get("label", o["id"]) for o in options}
    result = jc.ask(
        {"state": state, "objective": objective},
        {"next": jc.choice(
            f"Which single next action best advances the objective: {objective}?",
            opt_map,
        )},
        kind="next",
    )
    ans = result.get("answers", {}).get("next", {})
    probs = ans.get("probabilities") or {}
    chosen = ans.get("choice")
    if result.get("mock") or chosen is None:
        chosen = options[0]["id"] if options else None
    return {
        "chosen": chosen,
        "confidence": jc.confidence_of(ans),
        "probabilities": probs,
        "mock": result.get("mock", True),
        "options": opt_map,
    }


def _parse_options(args: list[str]) -> list[dict]:
    if args == ["-"] or (len(args) == 1 and args[0] == "-"):
        data = json.loads(sys.stdin.read())
        return [{"id": o["id"], "label": o.get("label", o["id"])} for o in data]
    options = []
    for item in args:
        key, _, desc = item.partition(":")
        options.append({"id": key, "label": desc or key})
    return options


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        sys.stderr.write(__doc__ or "")
        return 2
    state, objective, rest = argv[0], argv[1], argv[2:]
    options = _parse_options(rest)
    if not options:
        sys.stderr.write("jev_next needs at least one candidate action\n")
        return 2
    print(json.dumps(choose(state, objective, options), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
