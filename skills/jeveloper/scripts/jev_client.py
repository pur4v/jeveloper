#!/usr/bin/env python3
"""jev_client.py — a zero-dependency client for TypeSafe AI's Jev (System One) model.

Jev is not an LLM. It takes STATE (text or JSON) plus one or more typed QUESTIONS and
returns typed *probabilistic decisions* in a single fast pass (~70-500ms, ~$0.042 per
million input tokens, output free). That profile is what makes it usable on every tool
call and every loop step without anyone noticing the cost or the latency.

This module wraps `POST /v1/systemone` using ONLY the Python standard library, so it runs
inside Claude Code hooks with no `pip install` and no virtualenv.

Question primitives (build them with the helpers below):
  noul(instructions)                 -> yes/no        answer["noul"]:   probability 0..1
  choice(instructions, options)      -> pick 1 of N   answer["choice"], answer["probabilities"]
  score(instructions, criteria)      -> ordered scale answer["score"] (may land between levels)

Auth: the TYPESAFE_API_KEY environment variable. When it is unset — or any network/parse
error occurs — the client returns clearly-flagged MOCK answers (`mock=True`) instead of
raising. Callers (the hooks) treat mock/degraded results as "no opinion" and fail OPEN,
so a missing key or a Jev outage never blocks the user's work.

NOTE ON THE WIRE SCHEMA: the request/response field names below follow TypeSafe's public
examples (state + questions -> answers; each question has a "type" and "instructions").
The exact shape of `choice`/`score` options is not fully documented publicly; it is kept
in one place (`_question_wire`) so it is trivial to correct against the console.typesafe.ai
docs once you have a key. Until then the default keyless MOCK path is what runs.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_URL = os.environ.get("JEVELOPER_API_URL", "https://api.typesafe.ai/v1/systemone")
MODEL = os.environ.get("JEVELOPER_MODEL", "jev-latest")
TIMEOUT = float(os.environ.get("JEVELOPER_TIMEOUT", "5"))


# --- question builders -------------------------------------------------------

def noul(instructions: str) -> dict:
    """A yes/no judgement. The answer carries `noul`: P(statement is true), 0..1."""
    return {"type": "noul", "instructions": instructions}


def choice(instructions: str, options: dict[str, str]) -> dict:
    """Pick one of up to 255 options. `options` maps value -> human description."""
    return {"type": "choice", "instructions": instructions, "options": options}


def score(instructions: str, criteria: list[str]) -> dict:
    """Position on an ordered scale (2-10 levels). `criteria` are the levels, low->high."""
    return {"type": "score", "instructions": instructions, "criteria": criteria}


# --- transport ---------------------------------------------------------------

def _question_wire(q: dict) -> dict:
    """Map our normalized question dict to Jev's request field names. One place to fix."""
    return q


def ask(state, questions: dict[str, dict], api_key: str | None = None,
        kind: str = "ask") -> dict:
    """Pose typed questions to Jev about `state`. Returns:

        {"answers": {name: {...typed answer...}}, "mock": bool, "error": str | None}

    Never raises for network/auth/parse problems — those come back as mock=True. Every call
    is metered (best-effort) so the thinking-token savings can be reported; `kind` tags the
    call site (next / check / warden / route / tree / search / ask).
    """
    key = api_key or os.environ.get("TYPESAFE_API_KEY")
    if not key:
        result = _mock(questions, error="TYPESAFE_API_KEY not set")
    else:
        payload = {
            "model": MODEL,
            "state": state,
            "questions": {name: _question_wire(q) for name, q in questions.items()},
        }
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # TypeSafe returns answers under "answers"; tolerate a flat top-level shape.
            answers = data.get("answers", data) if isinstance(data, dict) else {}
            result = {"answers": answers, "mock": False, "error": None}
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            result = _mock(questions, error=f"{type(exc).__name__}: {exc}")

    try:  # metering is best-effort and must never affect the caller
        import jev_meter
        jev_meter.record(kind=kind, decisions=len(questions), mock=result.get("mock", True))
    except Exception:
        pass
    return result


def _mock(questions: dict[str, dict], error: str | None = None) -> dict:
    """Neutral, clearly-flagged answers so callers can fail open."""
    answers: dict[str, dict] = {}
    for name, q in questions.items():
        t = q.get("type")
        if t == "noul":
            answers[name] = {"type": "noul", "noul": 0.5, "confidence": 0.0}
        elif t == "choice":
            opts = q.get("options") or {}
            first = next(iter(opts), None)
            answers[name] = {
                "type": "choice",
                "choice": first,
                "probabilities": {},
                "confidence": 0.0,
            }
        elif t == "score":
            answers[name] = {"type": "score", "score": 0.0, "confidence": 0.0}
        else:
            answers[name] = {"type": t, "confidence": 0.0}
    return {"answers": answers, "mock": True, "error": error}


# --- small accessors (defensive; tolerate the mock/degraded shapes) ----------

def noul_of(answer: dict) -> float:
    """P(true) for a noul answer, defaulting to 0.5 (no opinion)."""
    try:
        return float(answer.get("noul", 0.5))
    except (TypeError, ValueError):
        return 0.5


def score_of(answer: dict) -> float:
    try:
        return float(answer.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def confidence_of(answer: dict) -> float:
    try:
        return float(answer.get("confidence", 0.0))
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    # Tiny smoke test: prints a mock (keyless) or live answer for one noul.
    import sys

    state = sys.argv[1] if len(sys.argv) > 1 else "The deploy failed twice; users see 500s."
    out = ask(state, {"urgent": noul("The message conveys urgency or an incident")})
    print(json.dumps(out, indent=2))
