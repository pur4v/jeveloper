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
           session: str = "") -> None:
    """Append one metering record. Best-effort; never raises."""
    try:
        path = _log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rec = {
            "ts": round(time.time(), 3),
            "kind": kind,
            "calls": calls,
            "decisions": int(decisions),
            "mock": bool(mock),
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
              "decisions": 0, "live_decisions": 0, "by_kind": {}}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                totals["calls"] += r.get("calls", 1)
                totals["decisions"] += r.get("decisions", 0)
                k = r.get("kind", "ask")
                totals["by_kind"][k] = totals["by_kind"].get(k, 0) + r.get("calls", 1)
                if r.get("mock"):
                    totals["mock_calls"] += r.get("calls", 1)
                else:
                    totals["live_calls"] += r.get("calls", 1)
                    totals["live_decisions"] += r.get("decisions", 0)
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
        "  by kind:              " + (", ".join(f"{k}={v}" for k, v in sorted(totals["by_kind"].items())) or "—"),
        f"  est. thinking tokens saved: ~{totals['est_thinking_tokens_saved']:,}"
        f"  (estimate: {int(totals['tokens_per_decision'])} tok/decision × {totals['live_decisions']} live decisions)",
        "  NOTE: the saving is an estimate from an assumed per-decision cost, not a measurement.",
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
