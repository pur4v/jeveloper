#!/usr/bin/env python3
"""jev_ask.py — one-shot CLI for asking Jev a typed question.

Used by the /jeveloper:route, /jeveloper:check, and /jeveloper:ask commands, but handy on
its own. Prints the JSON answer (mock=true when TYPESAFE_API_KEY is unset).

Usage:
  jev_ask.py noul   "<state>" "<instructions>"
  jev_ask.py choice "<state>" "<instructions>" value1[:desc] value2[:desc] ...
  jev_ask.py score  "<state>" "<instructions>" level_low ... level_high

Examples:
  jev_ask.py noul "tests: 3 passed, 1 skipped" "All tests genuinely passed"
  jev_ask.py choice "Rename a symbol across 40 files" "Which model fits?" \\
      haiku:cheap-fast sonnet:balanced opus:hardest-reasoning
  jev_ask.py score "PR adds a feature with no tests" "How production-ready is this?" \\
      "not ready" "needs work" "shippable"
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        sys.stderr.write(__doc__ or "")
        return 2

    qtype, state, instructions, rest = argv[0], argv[1], argv[2], argv[3:]

    if qtype == "noul":
        question = jc.noul(instructions)
    elif qtype == "choice":
        options: dict[str, str] = {}
        for item in rest:
            key, _, desc = item.partition(":")
            options[key] = desc or key
        if not options:
            sys.stderr.write("choice needs at least one option\n")
            return 2
        question = jc.choice(instructions, options)
    elif qtype == "score":
        if not rest:
            sys.stderr.write("score needs at least two ordered levels\n")
            return 2
        question = jc.score(instructions, rest)
    else:
        sys.stderr.write(f"unknown question type: {qtype}\n")
        return 2

    result = jc.ask(state, {"answer": question})
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
