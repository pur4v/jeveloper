#!/usr/bin/env python3
"""drive_inject.py — UserPromptSubmit hook. Makes jeveloper's driver mode always-on.

The requirement: Jev is the *first* call for every action — it selects what to do, then its
output is verified, on a loop. Claude Code can't force Claude to defer its decisions, so this
injects a short standing instruction into every turn: run the Jev ping-pong (enumerate
options cheaply → jev_next decides → execute → the Check hook verifies → repeat). Emitted
only when jeveloper is enabled (a Jev key is set); otherwise silent, so keyless is inert.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_config as cfg_mod  # noqa: E402

# When the prompt itself is a compare/explore-several-approaches request, we don't leave the
# fan-out to the model's discretion — we inject a hard, prompt-specific directive that says to
# fan out NOW. (A hook can't spawn subagents itself; this is the strongest automatic lever.)
_FANOUT_RE = re.compile(
    r"\b(compare|comparison|trade[- ]?offs?|versus|vs\.?|evaluate|weigh|pros and cons|"
    r"which (?:one|is|should|approach|option)|best (?:way|approach|option)|"
    r"(?:different|several|multiple|various|a few) (?:ways|approaches|options|designs|"
    r"alternatives|strategies)|\d+\s+(?:ways|approaches|options|designs|ideas|alternatives|"
    r"strategies))\b",
    re.I,
)

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
_NEXT = os.path.join(_SCRIPTS, "jev_next.py")

INSTRUCTION = f"""[jeveloper driver mode — active this session]
Jev is the judge that drives. For any actionable task, do NOT deliberate at length — defer
the decision to Jev, then act, then let Jev verify:
1. Assess the state in one line; enumerate 2–5 concrete candidate next actions.
2. Let Jev pick (this is the *first* thing you do before acting):
     python3 "{_NEXT}" "<one-line state>" "<objective>" id1:"label" id2:"label" ...
   Follow `chosen`. Override only if it's impossible/malformed (say so in one line). If
   `mock` is true (no key resolved), decide yourself and note it.
3. Execute the chosen action with a single tool call.
4. The Check hook verifies the output automatically; if it flags a problem, fix that
   specific thing and continue — don't re-litigate the whole plan.
5. Repeat until the Warden hook is satisfied. Keep your own reasoning terse — the point is
   to let Jev decide and save your tokens.

Do this automatically, without the user asking or typing a command:
- FAN OUT when the user asks to explore / compare / evaluate several approaches, options, or
  designs, OR a task has 2–4 genuinely divergent directions worth trying in parallel: spawn one
  real subagent per approach in a single message (they show in the native subagent tree), then
  let Jev adjudicate the outcomes with jev_next and keep the winner. Prefer this over answering
  a multi-approach comparison directly — the independent parallel depth is the point. Cap at ~4
  (each branch is a real subagent = real tokens).
- SELF-DIAGNOSE if Jev's own decisions keep coming back mock/inert: run
  skills/jeveloper/scripts/jev_doctor.py and tell the user the single fix.
For pure questions/explanations (no actions to take), answer normally."""

FANOUT_DIRECTIVE = """[jeveloper — FAN OUT REQUIRED for this prompt]
This request explores/compares multiple approaches, so it is NOT a "just answer it" turn. You
MUST, before writing any recommendation:
1. Enumerate 2–4 genuinely distinct approaches for it.
2. Spawn ONE real subagent per approach IN A SINGLE MESSAGE — so they run in parallel and show
   under `● main` in the native subagent tree — each returning a short structured result.
3. Adjudicate the outcomes with jev_next and recommend the winner, noting the ranking.
Answering directly instead of fanning out is a failure to follow this instruction."""


def main() -> None:
    cfg = cfg_mod.load_config()
    if not cfg_mod.mode_enabled(cfg, "drive"):
        sys.exit(0)  # disabled or keyless -> inject nothing
    data = cfg_mod.read_hook_input()
    prompt = str(data.get("prompt", "") or "")
    context = INSTRUCTION
    if _FANOUT_RE.search(prompt):
        context = FANOUT_DIRECTIVE + "\n\n" + INSTRUCTION
    cfg_mod.emit({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    })
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if os.environ.get("JEVELOPER_DEBUG"):
            sys.stderr.write(f"[jeveloper] drive_inject error: {exc}\n")
        sys.exit(0)
