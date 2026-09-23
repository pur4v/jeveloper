#!/usr/bin/env python3
"""jev_path.py — score several candidate situations/paths with Jev and return the best to run.

The loop this serves: at each state, Claude throws 2-6 candidate paths (situations it could
pursue next); Jev SCORES every one in a single batched call; jev_path ranks them, picks the
best, and emits a `directive` — an explicit "DO NEXT" step for Claude to execute without
re-deliberating. Jev's output is the marching order, not a label to re-interpret.

  state --(Claude throws N situations)--> Jev scores each --> best path --> directive --> act

Usage:
  jev_path.py "<state>" "<objective>" s1:"path 1" s2:"path 2" ...
  echo '[{"id":"s1","label":"..."}]' | jev_path.py "<state>" "<objective>" -

Prints JSON: {scores, ranking, best, directive, confidence, mock, paths}. `scores` are
normalized 0..1 (higher = better). On mock (no key) every score is 0.5 and `mock` is true —
Claude should then decide for itself, not follow a placeholder.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402
import jev_config as cfg_mod  # noqa: E402

_LEVELS = ["very poor", "poor", "fair", "good", "excellent"]


def score_paths(state: str, objective: str, paths: list[dict]) -> dict:
    """paths: list of {"id","label"}. One batched Jev call scores each; returns the decision."""
    cfg_mod.mark_consulted()  # consulting Jev re-arms the Jev-first gate for this turn
    labels = {p["id"]: p.get("label", p["id"]) for p in paths}
    questions = {
        pid: jc.score(
            "Rate how well this path advances the objective, accounting for its likely "
            f"outcome. Objective: {objective}. Path: {label}",
            _LEVELS,
        )
        for pid, label in labels.items()
    }
    result = jc.ask({"state": state, "objective": objective}, questions, kind="path")
    mock = result.get("mock", True)
    answers = result.get("answers", {})
    denom = float(len(_LEVELS) - 1) or 1.0
    scores = {
        pid: (0.5 if mock else round(jc.score_of(answers.get(pid, {}), _LEVELS) / denom, 3))
        for pid in labels
    }
    ranking = sorted(scores, key=lambda k: scores[k], reverse=True)
    best = ranking[0] if ranking else None
    best_label = labels.get(best, best) if best else "(none)"
    if mock:
        directive = (f"[mock - no Jev key] Jev could not score the paths; decide yourself, "
                     f"then act. Provisional best '{best}': {best_label}.")
    else:
        second = ranking[1] if len(ranking) > 1 else None
        also = f" (next-best: {second} @ {scores[second]:.2f})" if second else ""
        directive = (f"DO NEXT -> {best}: {best_label} (score {scores.get(best, 0):.2f}). "
                     f"Execute this path as your next single action, then let the Check hook "
                     f"verify. Do not re-deliberate the lower-scored paths{also}.")
    return {
        "scores": scores,
        "ranking": ranking,
        "best": best,
        "directive": directive,
        "confidence": round(scores.get(best, 0.0), 3),
        "mock": mock,
        "paths": labels,
    }


def _parse_paths(args: list[str]) -> list[dict]:
    if args == ["-"]:
        data = json.loads(sys.stdin.read())
        return [{"id": o["id"], "label": o.get("label", o["id"])} for o in data]
    paths = []
    for item in args:
        key, _, desc = item.partition(":")
        paths.append({"id": key, "label": desc or key})
    return paths


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        sys.stderr.write(__doc__ or "")
        return 2
    state, objective, rest = argv[0], argv[1], argv[2:]
    paths = _parse_paths(rest)
    if not paths:
        sys.stderr.write("jev_path needs at least one candidate path\n")
        return 2
    print(json.dumps(score_paths(state, objective, paths), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
