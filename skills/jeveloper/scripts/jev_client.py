#!/usr/bin/env python3
"""jev_client.py — a zero-dependency client for TypeSafe AI's Jev (System One) model.

Jev is not an LLM. It takes STATE (text or JSON) plus one or more typed QUESTIONS and
returns typed *probabilistic decisions* in a single fast pass (~70-500ms, ~$0.042 per
million input tokens, output free). That profile is what makes it usable on every tool call
and every loop step without anyone noticing the cost or the latency.

This module wraps the Jev "decisions" API using ONLY the Python standard library, so it runs
inside Claude Code hooks with no `pip install` and no virtualenv.

Two providers, auto-detected from whichever key is set (OpenRouter wins if both are):
  * OpenRouter — POST https://openrouter.ai/api/alpha/decisions, Bearer OPENROUTER_API_KEY,
    model `typesafe/jev-latest`.
  * TypeSafe native — POST https://api.typesafe.ai/v1/systemone, Bearer TYPESAFE_API_KEY,
    model `jev-latest`.
Override with JEVELOPER_API_URL / JEVELOPER_MODEL. With no key set — or on any network/parse
error — the client returns clearly-flagged MOCK answers (`mock=True`) instead of raising, so
callers (the hooks) fail OPEN.

Wire schema (confirmed against OpenRouter's Decisions API):
  request:  {"model", "state", "questions": {name: {"type", "instructions", "criteria"?}}}
            noul   -> {"type":"noul","instructions":...}
            choice -> {"type":"choice","instructions":..., "criteria": {opt: desc, ...}}
            score  -> {"type":"score","instructions":...,  "criteria": {level: desc, ...}}
  response: {"answers": {name: {...}}, "usage": {"input_tokens","output_tokens","cost"}, ...}
            noul   -> {"noul": p}  (or {"probabilities": {...}})
            choice -> {"probabilities": {opt: p}, "confidence"}   (chosen = argmax)
            score  -> {"probabilities": {level: p}, "legend", "confidence"}
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

TIMEOUT = float(os.environ.get("JEVELOPER_TIMEOUT", "5"))

_OPENROUTER_URL = "https://openrouter.ai/api/alpha/decisions"
_TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"

# name -> (endpoint, default model, default key env var)
_PROVIDERS = {
    "openrouter": (_OPENROUTER_URL, "typesafe/jev-latest", "OPENROUTER_API_KEY"),
    "typesafe": (_TYPESAFE_URL, "jev-latest", "TYPESAFE_API_KEY"),
}
_ALIASES = {"direct": "typesafe", "native": "typesafe", "openrouter.ai": "openrouter"}


def _provider_cfg() -> dict:
    """Read the `provider` block from .jeveloper.json (best-effort; {} if absent)."""
    try:
        import jev_config
        return jev_config.load_config().get("provider", {}) or {}
    except Exception:
        return {}


def _resolve():
    """Pick the provider. Selection order: JEVELOPER_PROVIDER env > `.jeveloper.json`
    provider.use > auto (OpenRouter if its key is set, else TypeSafe). Keys always come from
    the environment — never from config. Returns (url, model, key) or None for MOCK."""
    cfg = _provider_cfg()
    use = (os.environ.get("JEVELOPER_PROVIDER") or cfg.get("use") or "auto").lower()
    use = _ALIASES.get(use, use)
    override_url = os.environ.get("JEVELOPER_API_URL") or cfg.get("api_url") or ""
    override_model = os.environ.get("JEVELOPER_MODEL") or cfg.get("model") or ""
    key_env = cfg.get("api_key_env") or ""

    def build(name: str):
        url, model, default_env = _PROVIDERS[name]
        key = (os.environ.get(key_env) if key_env else None) or os.environ.get(default_env)
        if not key:
            return None
        return (override_url or url, override_model or model, key)

    if use in _PROVIDERS:
        return build(use)  # explicit choice: no silent fallback to the other provider
    return build("openrouter") or build("typesafe")  # auto


# --- question builders -------------------------------------------------------

def noul(instructions: str) -> dict:
    """A yes/no judgement. Answer carries `noul` = P(statement is true), 0..1."""
    return {"type": "noul", "instructions": instructions}


def choice(instructions: str, options: dict[str, str]) -> dict:
    """Pick one of up to 255 options. `options` maps value -> human description."""
    return {"type": "choice", "instructions": instructions, "criteria": dict(options)}


def score(instructions: str, criteria) -> dict:
    """Position on an ordered scale. `criteria` is the levels low->high: a list of names,
    or a {level: description} map. Stored as a map on the wire; order is preserved."""
    if isinstance(criteria, dict):
        crit = dict(criteria)
    else:
        crit = {str(c): str(c) for c in criteria}
    return {"type": "score", "instructions": instructions, "criteria": crit}


def _ordered_levels(q: dict) -> list[str]:
    return list((q.get("criteria") or {}).keys())


# --- transport ---------------------------------------------------------------

def ask(state, questions: dict[str, dict], api_key: str | None = None,
        kind: str = "ask") -> dict:
    """Pose typed questions to Jev about `state`. Returns:

        {"answers": {name: {...}}, "mock": bool, "error": str|None, "usage": {...}}

    Never raises for network/auth/parse problems — those come back as mock=True. Every call
    is metered best-effort; `kind` tags the call site (next/check/warden/route/tree/search).
    """
    resolved = _resolve()
    if resolved is None and not api_key:
        result = _mock(questions, error="no OPENROUTER_API_KEY / TYPESAFE_API_KEY set")
    else:
        if resolved is not None:
            url, model, key = resolved
        else:  # explicit api_key with no env provider -> assume OpenRouter
            url, model, key = _OPENROUTER_URL, os.environ.get(
                "JEVELOPER_MODEL", "typesafe/jev-latest"), api_key
        payload = {"model": model, "state": state, "questions": questions}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            answers = data.get("answers", {}) if isinstance(data, dict) else {}
            result = {"answers": answers, "mock": False, "error": None,
                      "usage": data.get("usage", {}) if isinstance(data, dict) else {}}
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            result = _mock(questions, error=f"{type(exc).__name__}: {exc}")

    try:  # metering is best-effort and must never affect the caller
        import jev_meter
        usage = result.get("usage") or {}
        jev_meter.record(kind=kind, decisions=len(questions), mock=result.get("mock", True),
                         cost=float(usage.get("cost", 0.0) or 0.0),
                         input_tokens=int(usage.get("input_tokens", 0) or 0))
    except Exception:
        pass
    return result


def _mock(questions: dict[str, dict], error: str | None = None) -> dict:
    answers: dict[str, dict] = {}
    for name, q in questions.items():
        t = q.get("type")
        if t == "noul":
            answers[name] = {"type": "noul", "noul": 0.5, "confidence": 0.0}
        elif t == "choice":
            crit = q.get("criteria") or {}
            first = next(iter(crit), None)
            answers[name] = {"type": "choice", "choice": first,
                             "probabilities": {}, "confidence": 0.0}
        elif t == "score":
            answers[name] = {"type": "score", "probabilities": {}, "confidence": 0.0}
        else:
            answers[name] = {"type": t, "confidence": 0.0}
    return {"answers": answers, "mock": True, "error": error, "usage": {}}


# --- accessors (defensive; tolerate every observed response shape) -----------

def noul_of(answer: dict) -> float:
    """P(true) for a noul answer, defaulting to 0.5 (no opinion)."""
    if answer.get("noul") is not None:
        try:
            return float(answer["noul"])
        except (TypeError, ValueError):
            return 0.5
    p = answer.get("probabilities") or {}
    for k in ("true", "yes", "True", "Yes"):
        if k in p:
            return float(p[k])
    for k in ("false", "no", "False", "No"):
        if k in p:
            return 1.0 - float(p[k])
    return 0.5


def choice_of(answer: dict):
    """The chosen option: an explicit `choice`, else argmax of probabilities."""
    if answer.get("choice") is not None:
        return answer["choice"]
    p = answer.get("probabilities") or {}
    return max(p, key=p.get) if p else None


def score_of(answer: dict, levels=None) -> float:
    """A scalar score in *index units* (0..len-1). Prefers an explicit scalar `score`;
    otherwise the expected level index from `probabilities` over the ordered legend/levels."""
    if answer.get("score") is not None:
        try:
            return float(answer["score"])
        except (TypeError, ValueError):
            return 0.0
    p = answer.get("probabilities") or {}
    legend = answer.get("legend")
    order = None
    if isinstance(legend, dict):
        order = list(legend.keys())
    elif isinstance(legend, list):
        order = legend
    elif isinstance(levels, dict):
        order = list(levels.keys())
    elif isinstance(levels, list):
        order = list(levels)
    elif p:
        order = list(p.keys())
    if p and order:
        return sum(float(p.get(k, 0.0)) * i for i, k in enumerate(order))
    return 0.0


def confidence_of(answer: dict) -> float:
    try:
        return float(answer.get("confidence", 0.0))
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    import sys

    state = sys.argv[1] if len(sys.argv) > 1 else "The deploy failed twice; users see 500s."
    out = ask(state, {"urgent": noul("The message conveys urgency or an incident")})
    print(json.dumps(out, indent=2))
