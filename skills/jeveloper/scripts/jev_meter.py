#!/usr/bin/env python3
"""jev_meter.py — record what Jev decided, so the "reduce thinking-token cost" claim is
measured instead of asserted.

Every Jev call is a decision that Claude did NOT have to deliberate through. We can log the
facts we actually know — how many batched Jev calls, how many typed decisions they answered,
how many were live vs. mock — and pair them with a single, explicit, user-tunable estimate of
how many *reasoning* tokens each offloaded decision would otherwise have cost Claude.

Honesty rules:
  * We never claim to have measured Claude's counterfactual thinking. `tokens_per_decision`
    is an ASSUMPTION (default 500, override with JEVELOPER_TOKENS_PER_DECISION), and the
    report labels the saving as an *estimate*.
  * Mock (keyless) calls offloaded nothing real — they are counted separately and excluded
    from the estimate.
  * Metering never raises and never blocks: all writes are best-effort.

Log: `<cwd>/.jeveloper/metrics.jsonl` (or $JEVELOPER_METRICS). One JSON object per Jev call.
"""
from __future__ import annotations

import json
import os
import time


def _log_path() -> str:
    p = os.environ.get("JEVELOPER_METRICS")
    if p:
        return p
    return os.path.join(os.getcwd(), ".jeveloper", "metrics.jsonl")


def record(kind: str, decisions: int, mock: bool, calls: int = 1,
           cost: float = 0.0, input_tokens: int = 0, session: str = "") -> None:
    """Append one metering record. Best-effort; never raises. `cost`/`input_tokens` come
    from the Jev response `usage` (real spend), when the provider returns it."""
    try:
        path = _log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rec = {
            "ts": round(time.time(), 3),
            "kind": kind,
            "calls": calls,
            "decisions": int(decisions),
            "mock": bool(mock),
            "cost": float(cost),
            "input_tokens": int(input_tokens),
            "session": session or os.environ.get("JEVELOPER_SESSION", ""),
        }
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def report(path: str | None = None) -> dict:
    path = path or _log_path()
    tpd = float(os.environ.get("JEVELOPER_TOKENS_PER_DECISION", "500"))
    totals = {"calls": 0, "live_calls": 0, "mock_calls": 0,
              "decisions": 0, "live_decisions": 0, "by_kind": {},
              "jev_cost_usd": 0.0, "jev_input_tokens": 0}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                totals["calls"] += r.get("calls", 1)
                totals["decisions"] += r.get("decisions", 0)
                totals["jev_cost_usd"] += float(r.get("cost", 0.0) or 0.0)
                totals["jev_input_tokens"] += int(r.get("input_tokens", 0) or 0)
                k = r.get("kind", "ask")
                bk = totals["by_kind"].setdefault(
                    k, {"calls": 0, "decisions": 0, "live_calls": 0, "cost": 0.0})
                bk["calls"] += r.get("calls", 1)
                bk["decisions"] += r.get("decisions", 0)
                if r.get("mock"):
                    totals["mock_calls"] += r.get("calls", 1)
                else:
                    totals["live_calls"] += r.get("calls", 1)
                    totals["live_decisions"] += r.get("decisions", 0)
                    bk["live_calls"] += r.get("calls", 1)
                    bk["cost"] += float(r.get("cost", 0.0) or 0.0)
    except OSError:
        pass
    totals["tokens_per_decision"] = tpd
    totals["est_thinking_tokens_saved"] = int(totals["live_decisions"] * tpd)
    return totals


def format_report(totals: dict) -> str:
    lines = [
        "jeveloper — Jev decision meter",
        f"  Jev calls:            {totals['calls']}  (live {totals['live_calls']}, mock {totals['mock_calls']})",
        f"  decisions offloaded:  {totals['decisions']}  (live {totals['live_decisions']})",
        "  by kind:",
    ]
    by_kind = totals.get("by_kind") or {}
    if by_kind:
        for k in sorted(by_kind, key=lambda x: (-by_kind[x]["calls"], x)):
            v = by_kind[k]
            lines.append(
                f"      {k:8} {v['calls']:>4} calls, {v['decisions']:>4} decisions, "
                f"live {v['live_calls']:>4}, ${v['cost']:.6f}")
    else:
        lines.append("      —")
    lines += [
        f"  Jev spend (real):     ${totals['jev_cost_usd']:.6f}  ({totals['jev_input_tokens']:,} input tokens)",
        f"  est. thinking tokens saved: ~{totals['est_thinking_tokens_saved']:,}"
        f"  (estimate: {int(totals['tokens_per_decision'])} tok/decision × {totals['live_decisions']} live decisions)",
        "  NOTE: Jev spend is measured from the API; the thinking-tokens-saved figure is an",
        "        estimate from an assumed per-decision cost, not a measurement.",
    ]
    if totals["mock_calls"]:
        lines.append(f"  ({totals['mock_calls']} mock calls offloaded nothing — no key set.)")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    arg = sys.argv[1] if len(sys.argv) > 1 else "report"
    if arg == "reset":
        try:
            os.remove(_log_path())
            print("meter reset")
        except OSError:
            print("nothing to reset")
    else:
        print(format_report(report()))
