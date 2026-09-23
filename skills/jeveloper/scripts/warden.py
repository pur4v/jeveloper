#!/usr/bin/env python3
"""warden.py — Stop hook. Jev decides whether the task is actually done.

When Claude is about to stop, the warden asks Jev to judge the work against the goal:
a 0-10 completeness score plus a yes/no on whether every acceptance criterion is met.
If Jev is confident the task is NOT finished, the warden blocks the stop and hands Claude
a concrete note on what's missing, so the agent loop keeps going until the work is real —
not until Claude first feels like stopping.

Two safety rails so this can never trap a session:
  * a hard `max_continues` cap per session (counter in the temp dir), and
  * fail-OPEN on every uncertainty (disabled, keyless/mock, Jev down, or score >= threshold).
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402
import jev_config as cfg_mod  # noqa: E402

MAX_STATE_CHARS = 16000

# Greetings and pleasantries that carry no task to verify.
_GREETINGS = {
    "hi", "hello", "hey", "yo", "sup", "hiya", "howdy", "hey there",
    "good morning", "good afternoon", "good evening", "gm", "gn",
    "thanks", "thank you", "thx", "ty", "ok", "okay", "k", "cool",
    "nice", "great", "got it", "sounds good", "bye", "cya",
}

# Artifacts _flatten() emits for tool-only turns — never a real objective on their own.
_PLACEHOLDER_RE = re.compile(r"\(tool_result\)|\(tool_use:[^)]*\)")
_NO_GOAL = "(no explicit goal found in transcript)"

# Substrings that mark a "user" turn as system-injected (task notifications, system
# reminders, our own Stop-hook feedback) rather than a real user request.
_INJECTED_MARKERS = (
    "<system-reminder>", "<task-notification>", "</task-notification>",
    "<tool-use-id>", "</note>", "stop hook feedback:",
)


def _is_injected(text: str) -> bool:
    t = text.lower()
    return any(m in t for m in _INJECTED_MARKERS)


def _is_trivial_objective(text: str) -> bool:
    """True when there is nothing real to verify — a greeting, a tiny remark, a synthetic
    placeholder (tool-only turn / no-goal fallback), or the warden's own feedback fed back
    in as a user turn (which would loop forever)."""
    t = text.strip().lower().rstrip("!.?")
    if not t or t == _NO_GOAL:
        return True
    # A turn that was only tool_result / tool_use blocks carries no objective.
    if not _PLACEHOLDER_RE.sub("", t).strip():
        return True
    # System-injected content (task notifications, system reminders) is never an objective.
    if _is_injected(t):
        return True
    # Our own Stop-hook feedback lands in the transcript as a user message; never grade it.
    if "jev warden" in t and "completeness" in t:
        return True
    if t in _GREETINGS:
        return True
    # Very short with no real ask (e.g. "hi!", "yo", "ok cool").
    if len(t) <= 12 and len(t.split()) <= 2:
        return True
    return False


def _counter_path(session_id: str) -> str:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "nosession"
    return os.path.join(tempfile.gettempdir(), f"jeveloper-warden-{safe}.count")


def _read_counter(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            return int(fh.read().strip() or "0")
    except (OSError, ValueError):
        return 0


def _write_counter(path: str, n: int) -> None:
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(str(n))
    except OSError:
        pass


def _reset_counter(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _recent_transcript(path: str, max_chars: int = MAX_STATE_CHARS) -> tuple[str, str]:
    """Return (latest_user_request, recent_activity_tail) from a JSONL transcript."""
    last_user = ""
    lines: list[str] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                try:
                    ev = json.loads(raw)
                except ValueError:
                    continue
                msg = ev.get("message", ev)
                role = msg.get("role") or ev.get("type")
                content = msg.get("content")
                text = _flatten(content)
                if not text:
                    continue
                if (role == "user" and _PLACEHOLDER_RE.sub("", text).strip()
                        and not _is_injected(text)):
                    last_user = text
                lines.append(f"[{role}] {text}")
    except OSError:
        return "", ""
    tail = "\n".join(lines)[-max_chars:]
    return last_user[-4000:], tail


def _flatten(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    parts.append("(tool_result)")
                elif block.get("type") == "tool_use":
                    parts.append(f"(tool_use: {block.get('name', '')})")
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(p for p in parts if p).strip()
    return ""


def main() -> None:
    data = cfg_mod.read_hook_input()
    cfg = cfg_mod.load_config()
    if not cfg_mod.mode_enabled(cfg, "warden"):
        cfg_mod.fail_open("warden disabled")

    warden_cfg = cfg.get("warden", {})
    session_id = str(data.get("session_id", ""))
    counter_path = _counter_path(session_id)
    continues = _read_counter(counter_path)
    max_continues = int(warden_cfg.get("max_continues", 3))

    if continues >= max_continues:
        _reset_counter(counter_path)
        cfg_mod.fail_open(f"max_continues ({max_continues}) reached — letting it stop")

    goal = cfg.get("goal", "")
    latest_user, tail = _recent_transcript(data.get("transcript_path", ""))
    objective = goal or latest_user or "(no explicit goal found in transcript)"

    if not goal and _is_trivial_objective(objective):
        _reset_counter(counter_path)
        cfg_mod.fail_open("trivial/greeting objective — nothing to verify")

    state = {
        "objective": objective,
        "recent_activity": tail or "(transcript unavailable)",
    }
    result = jc.ask(
        state,
        {
            "completeness": jc.score(
                "How complete is the objective, judged only by the work shown in "
                "recent_activity?",
                criteria=[
                    "not started / untouched",
                    "partially done, major pieces missing",
                    "mostly done, loose ends remain",
                    "done and verified",
                ],
            ),
            "criteria_met": jc.noul(
                "Every acceptance criterion implied by the objective has been met AND "
                "verified in the recent activity (not merely attempted)."
            ),
            "blocked": jc.noul(
                "The agent is genuinely blocked or waiting on the user, so continuing "
                "on its own would not help."
            ),
        },
        kind="warden",
    )
    if result.get("mock"):
        cfg_mod.fail_open("mock/keyless — no opinion")

    answers = result.get("answers", {})
    score = jc.score_of(answers.get("completeness", {}))
    met = jc.noul_of(answers.get("criteria_met", {}))
    blocked = jc.noul_of(answers.get("blocked", {}))

    done_threshold = float(warden_cfg.get("done_threshold", 7.0))
    # Normalize a 0..(len-1) or 0..10 style score onto 0..10 if it looks like a small scale.
    if score <= 3.0 and done_threshold > 3.0:
        score = score / 3.0 * 10.0

    if blocked >= 0.7:
        _reset_counter(counter_path)
        cfg_mod.fail_open(f"agent looks blocked (p={blocked:.2f}) — letting it stop")

    # A pure question is "done" when it's answered well; completeness captures that, and the
    # "every criterion verified" test doesn't fit an answer-only turn, so don't require `met`.
    is_question = objective.strip().endswith("?")
    if score >= done_threshold and (met >= 0.5 or is_question):
        _reset_counter(counter_path)
        cfg_mod.fail_open(f"done (score={score:.1f}, met={met:.2f}, question={is_question})")
        return

    _write_counter(counter_path, continues + 1)
    reason = (
        f"jeveloper (Jev warden) thinks the task isn't finished "
        f"(completeness {score:.1f}/10, criteria-met p={met:.2f}). "
        f"Objective: {objective[:400]}. "
        "Identify what is still missing or unverified and continue until it is truly "
        f"done, then stop. (Warden pass {continues + 1}/{max_continues}.)"
    )
    # Stop hook: `decision: block` forces Claude to keep going with `reason` as guidance.
    cfg_mod.emit({"decision": "block", "reason": reason})
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if os.environ.get("JEVELOPER_DEBUG"):
            sys.stderr.write(f"[jeveloper] warden error: {exc}\n")
        sys.exit(0)
