#!/usr/bin/env python3
"""jev_search.py — search over candidate OPTIONS with Jev as the evaluation function.

The job: from the current state there are several things you could do; you want the one that
leads to the best *outcome*, accounting for what happens next — not just the one that looks
best right now. This is ordinary lookahead search, with **Jev as the evaluator**.

The division of labour is jeveloper's whole thesis: **Claude proposes** the candidate options
(System-2 generation); **Jev scores** them (System-1 evaluation, ~100 ms, ~free). Because Jev
scores every question in a request in parallel, a whole level of options is a single batched
call — so genuine lookahead is affordable.

(If it helps your intuition: it's the move-ordering + minimax idea a game engine uses, with
Jev standing in for the hand-written evaluation function. But nothing here is game-specific.)

  * Evaluate: Jev scores each option at a node (one batched `score` call).
  * Order + beam: keep the top `beam` options by score, prune the rest.
  * Look ahead: for a kept option that has `next`, recurse; its value becomes the backed-up
    value of that subtree (the immediate score is used only for ordering/pruning).
  * Back up, per the node's `mode`:
        "maximize" (default) -> we choose; take the best child
        "minimize"           -> worst-case: something/someone else chooses the worst-for-us
        "average"            -> expected value: score-weighted average of children

Spec (JSON) — a search node:
  {
    "id": "root",
    "objective": "what a good option should achieve",   # inherited by descendants
    "mode": "maximize" | "minimize" | "average",         # default "maximize"
    "criteria": ["very poor","poor","fair","good","excellent"],  # optional score scale
    "options": [
      { "id": "o1", "label": "do X",
        "next": { <another node — the likely follow-on situation / responses> } },
      { "id": "o2", "label": "do Y" }                    # leaf: valued by Jev directly
    ]
  }

CLI:  jev_search.py <spec.json> "<state>" [beam] [depth]
      TYPESAFE_API_KEY unset -> MOCK (every option scores a neutral 0.5, flagged).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402

DEFAULT_CRITERIA = ["very poor", "poor", "fair", "good", "excellent"]
DEFAULT_BEAM = 2
DEFAULT_DEPTH = 3
MAX_CALLS = 64  # hard cap on batched Jev calls per search, so a big tree can't blow up


class Budget:
    def __init__(self, limit: int):
        self.left = limit

    def take(self) -> bool:
        if self.left <= 0:
            return False
        self.left -= 1
        return True


def _score_options(node: dict, state, objective: str, criteria: list[str], budget: Budget):
    """One batched Jev call: score every candidate option at this node. Returns (scores, mock)."""
    options = node.get("options", [])
    if not options or not budget.take():
        return {o["id"]: 0.5 for o in options}, True
    questions = {
        o["id"]: jc.score(
            f"How well does the option \"{o.get('label', o['id'])}\" achieve the "
            f"objective: {objective}?",
            criteria,
        )
        for o in options
    }
    result = jc.ask({"state": state, "objective": objective}, questions)
    if result.get("mock"):
        # No key / unreachable: every option is a neutral 0.5 placeholder, clearly flagged.
        return {o["id"]: 0.5 for o in options}, True
    answers = result.get("answers", {})
    denom = max(len(criteria) - 1, 1)
    scores = {}
    for o in options:
        s = jc.score_of(answers.get(o["id"], {}))
        scores[o["id"]] = max(0.0, min(1.0, s / denom))
    return scores, False


def search(node: dict, state, beam: int, depth: int, budget: Budget,
           objective: str = "", criteria=None) -> dict:
    objective = node.get("objective", objective) or "(unspecified)"
    criteria = node.get("criteria", criteria) or DEFAULT_CRITERIA
    mode = node.get("mode", "maximize")
    options = node.get("options", [])

    if not options:
        return {"value": 0.5, "best": None, "path": [], "options": [], "mock": True,
                "mode": mode}

    scores, mock = _score_options(node, state, objective, criteria, budget)
    ordered = sorted(options, key=lambda o: scores[o["id"]], reverse=(mode != "minimize"))
    kept = ordered[: max(1, beam)]

    evaluated = []
    for o in options:
        entry = {"id": o["id"], "label": o.get("label", o["id"]),
                 "immediate": round(scores[o["id"]], 3), "pruned": o not in kept}
        if o in kept and o.get("next") and depth > 0:
            child_state = f"{state}\n[after: {o.get('label', o['id'])}]"
            sub = search(o["next"], child_state, beam, depth - 1, budget,
                         objective, criteria)
            entry["value"] = sub["value"]
            entry["path"] = [entry["id"]] + sub["path"]
            entry["next"] = sub
            mock = mock or sub["mock"]
        else:
            entry["value"] = round(scores[o["id"]], 3)
            entry["path"] = [entry["id"]]
        evaluated.append(entry)

    considered = [e for e in evaluated if not e["pruned"]]
    if mode == "minimize":
        best = min(considered, key=lambda e: e["value"])
        node_value = best["value"]
    elif mode == "average":
        total = sum(e["value"] for e in considered) or 1.0
        node_value = sum(e["value"] * e["value"] for e in considered) / total
        best = max(considered, key=lambda e: e["value"])
    else:  # "maximize"
        best = max(considered, key=lambda e: e["value"])
        node_value = best["value"]

    return {"value": round(node_value, 3), "best": best["id"], "path": best["path"],
            "options": evaluated, "mock": mock, "mode": mode, "objective": objective}


# --- pretty trace ------------------------------------------------------------

def render(result: dict, indent: int = 0) -> str:
    pad = "  " * indent
    lines = []
    for e in result.get("options", []):
        mark = "·" if e.get("pruned") else ("➤" if e["id"] == result.get("best") else "•")
        flag = " [pruned]" if e.get("pruned") else ""
        look = f"  (now {e['immediate']} → outcome {e['value']})" if "next" in e else ""
        lines.append(f"{pad}{mark} {e['id']}: {e['label']}  [{e['value']}]{look}{flag}")
        if "next" in e:
            lines.append(render(e["next"], indent + 1))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        sys.stderr.write(__doc__ or "")
        return 2
    spec_path, state = argv[0], argv[1]
    beam = int(argv[2]) if len(argv) > 2 else DEFAULT_BEAM
    depth = int(argv[3]) if len(argv) > 3 else DEFAULT_DEPTH
    try:
        spec = json.load(open(spec_path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"could not read spec {spec_path}: {exc}\n")
        return 2

    budget = Budget(MAX_CALLS)
    result = search(spec, state, beam, depth, budget)
    print(f"BEST OPTION: {result['best']}  (outcome value {result['value']})")
    print(f"Best path: {' → '.join(result['path']) or '(none)'}")
    print(f"beam={beam} depth={depth}  Jev calls used: {MAX_CALLS - budget.left}")
    if result["mock"]:
        print("MOCK mode — TYPESAFE_API_KEY unset; scores are neutral placeholders.")
    print("\nSearch tree (➤ chosen, · pruned):")
    print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
