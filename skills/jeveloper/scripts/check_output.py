#!/usr/bin/env python3
"""check_output.py — PostToolUse hook. Jev verifies what a tool just produced.

After a matched tool returns, Jev reads the call + its output (~100ms) and judges whether
the result is actually a failure or fails to accomplish the tool's evident intent — the
green-looking-but-skipped test, the edit that didn't do what it claimed, the command whose
output contains an error Claude might gloss over. When Jev is confident something's wrong,
the hook feeds that concern back to Claude as blocking PostToolUse context so it
self-corrects on the spot instead of building on a bad result.

Fails OPEN on every uncertainty: disabled, keyless (mock), Jev down, or below threshold.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402
import jev_config as cfg_mod  # noqa: E402

MAX_CHARS = 12000  # keep the state well under Jev's context budget


def _truncate(value, limit: int = MAX_CHARS):
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) > limit:
        return text[:limit] + f"\n…[truncated {len(text) - limit} chars]"
    return text


def main() -> None:
    data = cfg_mod.read_hook_input()
    cfg = cfg_mod.load_config()
    if not cfg_mod.mode_enabled(cfg, "check"):
        cfg_mod.fail_open("check disabled")

    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", data.get("tool_output", {}))

    state = {
        "tool": tool,
        "tool_input": _truncate(tool_input),
        "tool_output": _truncate(tool_response),
    }
    result = jc.ask(
        state,
        {
            "is_failure": jc.noul(
                "The tool output indicates a real failure: an error, a non-zero exit, a "
                "traceback, a rejected edit, or a test that errored/was skipped rather "
                "than genuinely passing."
            ),
            "misses_intent": jc.noul(
                "The result does not accomplish what this tool call was evidently trying "
                "to do."
            ),
        },
        kind="check",
    )
    if result.get("mock"):
        cfg_mod.fail_open("mock/keyless — no opinion")

    answers = result.get("answers", {})
    p_fail = jc.noul_of(answers.get("is_failure", {}))
    p_miss = jc.noul_of(answers.get("misses_intent", {}))
    worst = max(p_fail, p_miss)

    threshold = float(cfg.get("check", {}).get("fail_threshold", 0.80))
    if worst < threshold:
        cfg_mod.fail_open(f"ok (fail={p_fail:.2f}, miss={p_miss:.2f})")
        return

    concerns = []
    if p_fail >= threshold:
        concerns.append(f"the output looks like a failure/error (p={p_fail:.2f})")
    if p_miss >= threshold:
        concerns.append(f"it may not accomplish the call's intent (p={p_miss:.2f})")
    reason = (
        "jeveloper (Jev check) flagged this tool result: "
        + "; ".join(concerns)
        + ". Re-read the output and confirm it truly succeeded before continuing; "
        "fix and retry if it did not."
    )

    # PostToolUse: `decision: block` surfaces `reason` to Claude as feedback.
    cfg_mod.emit({"decision": "block", "reason": reason})
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if os.environ.get("JEVELOPER_DEBUG"):
            sys.stderr.write(f"[jeveloper] check_output error: {exc}\n")
        sys.exit(0)
