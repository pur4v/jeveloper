#!/usr/bin/env python3
"""route_gate.py — PreToolUse hook. Jev's fast safety gate on tool calls.

Before a matched tool runs, Jev judges (in ~100ms) whether the call is destructive or
out-of-scope for the task. High risk -> the gate returns a `deny`/`ask` permission
decision with a one-line reason; otherwise it stays silent and the call proceeds.

This is the honest, architecture-true half of "tool selection": a hook cannot pick
Claude's tool for it (Claude already chose), but it CAN veto a dangerous one before it
executes. The other half — routing among models/subagents/approaches — is on-demand via
`/jeveloper:route`, because that decision belongs to Claude's reasoning, not a gate.

Fails OPEN on every uncertainty: disabled, keyless (mock), Jev down, or below threshold.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402
import jev_config as cfg_mod  # noqa: E402


def _is_consult_command(tool: str, tool_input: dict) -> bool:
    """The consult itself runs jev_next/jev_ask via Bash — never gate that, or the Jev-first
    rule deadlocks (you couldn't consult Jev because the consult command is blocked)."""
    if tool != "Bash":
        return False
    cmd = (tool_input or {}).get("command", "") or ""
    return "jev_next" in cmd or "jev_ask" in cmd


def main() -> None:
    data = cfg_mod.read_hook_input()
    cfg = cfg_mod.load_config()
    if not cfg_mod.mode_enabled(cfg, "route"):
        cfg_mod.fail_open("route disabled")

    tool = data.get("tool_name", "")
    route_cfg = cfg.get("route", {})
    tools = route_cfg.get("tools") or []
    if tools and tool not in tools:
        cfg_mod.fail_open(f"{tool} not in route.tools")

    tool_input = data.get("tool_input", {})

    # Jev-first: block the first substantive action of the turn until Jev has actually been
    # consulted (jev_next / jev_ask has run this turn), so the *decision* is offloaded to Jev
    # before Claude commits reasoning to an action. Only enforced while `drive` is on, since
    # the UserPromptSubmit hook re-arms the per-turn marker each turn. Claude sees the deny
    # reason, runs jev_next, then retries — no user prompt. This costs no Jev call itself.
    # The consult itself runs jev_next/jev_ask via Bash, so that command is never gated.
    consult_tools = route_cfg.get("consult_tools") or []
    if (route_cfg.get("consult_first")
            and cfg_mod.mode_enabled(cfg, "drive")
            and tool in consult_tools
            and not _is_consult_command(tool, tool_input)
            and not cfg_mod.was_consulted()):
        cfg_mod.emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "jeveloper (Jev-first): consult Jev before this action so the decision "
                        "is offloaded from Claude's own reasoning. Enumerate 2-5 candidate "
                        "actions and run: python3 "
                        f"\"{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jev_next.py')}\" "
                        "\"<one-line state>\" \"<objective>\" id1:label id2:label ... — follow "
                        "`chosen`, then retry this tool. (Enforced once per turn.)"
                    ),
                }
            }
        )
        sys.exit(0)

    goal = cfg.get("goal", "")

    # State handed to Jev: the concrete action, plus the standing goal if configured.
    state = {
        "tool": tool,
        "tool_input": tool_input,
        "project_goal": goal or "(not specified)",
    }
    result = jc.ask(
        state,
        {
            "unsafe": jc.noul(
                "This action is destructive or irreversible (deletes/overwrites data, "
                "force-pushes, drops resources, exfiltrates secrets, or affects systems "
                "outside the current project)."
            ),
            "out_of_scope": jc.noul(
                "This action is unrelated to, or works against, the stated project goal."
            ),
        },
        kind="route",
    )
    if result.get("mock"):
        cfg_mod.fail_open("mock/keyless — no opinion")

    answers = result.get("answers", {})
    p_unsafe = jc.noul_of(answers.get("unsafe", {}))
    p_oos = jc.noul_of(answers.get("out_of_scope", {}))
    risk = max(p_unsafe, p_oos)

    deny_t = float(route_cfg.get("deny_threshold", 0.85))
    ask_t = float(route_cfg.get("ask_threshold", 0.60))

    if risk >= deny_t:
        decision = "deny"
    elif risk >= ask_t:
        decision = "ask"
    else:
        cfg_mod.fail_open(f"risk {risk:.2f} below ask_threshold {ask_t}")
        return

    why = []
    if p_unsafe >= ask_t:
        why.append(f"looks destructive/irreversible (p={p_unsafe:.2f})")
    if p_oos >= ask_t:
        why.append(f"looks out-of-scope for the goal (p={p_oos:.2f})")
    reason = "jeveloper (Jev gate): " + "; ".join(why or [f"risk p={risk:.2f}"])

    cfg_mod.emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        }
    )
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never let a hook crash block the user
        if os.environ.get("JEVELOPER_DEBUG"):
            sys.stderr.write(f"[jeveloper] route_gate error: {exc}\n")
        sys.exit(0)
