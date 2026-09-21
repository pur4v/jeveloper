#!/usr/bin/env python3
"""jev_search.py — search over candidate MOVES with Jev as the evaluation function.

The chess analogy: from any position there are several candidate moves; a chess engine
scores each with an evaluation function, keeps the strongest, looks ahead at the likely
replies, and backs the scores up (minimax) to choose the move that leads to the best *line* —
not merely the best-looking immediate move.

jeveloper does the same for an agent's decisions. **Claude proposes** the candidate moves
(System-2 generation); **Jev judges** them (System-1 evaluation, ~100 ms, ~free). Because
Jev scores every question in a request in parallel, a whole ply of candidate moves is a
single batched call — so genuine lookahead is affordable.

  * Evaluate: Jev scores each candidate move at a node (one batched `score` call).
  * Order + beam: keep the top `beam` moves by score, prune the rest (move ordering).
  * Look ahead: for a kept move that has `replies`, recurse; its value becomes the
    backed-up value of that subtree (immediate score is used only for ordering/pruning).
  * Back up (minimax/expectimax) by whose ply it is:
        player "us"    -> maximize   (our move: we pick the best)
        player "them"  -> minimize   (adversarial/worst-case reply — robust planning)
        player "chance"-> expectimax (score-weighted average of replies)
  * Recommend the root move with the best backed-up value, and print the principal
    variation (the best line) plus a full trace.

Spec (JSON) — a move-search node:
  {
    "id": "root",
    "objective": "what a good move should achieve",   # inherited by descendants
    "player": "us" | "them" | "chance",               # default "us"
    "criteria": ["losing","weak","even","promising","winning"],  # optional score scale
    "moves": [
      { "id": "m1", "move": "do X",
        "replies": { <another node — the likely responses/next decisions> } },
      { "id": "m2", "move": "do Y" }                   # leaf: valued by Jev directly
    ]
  }

CLI:  jev_search.py <spec.json> "<state>" [beam] [depth]
      TYPESAFE_API_KEY unset -> MOCK (every move scores a neutral 0.5, flagged).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402

DEFAULT_CRITERIA = ["losing", "weak", "even", "promising", "winning"]
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


def _score_moves(node: dict, state, objective: str, criteria: list[str], budget: Budget):
    """One batched Jev call: score every candidate move at this node. Returns (scores, mock)."""
    moves = node.get("moves", [])
    if not moves or not budget.take():
        return {m["id"]: 0.5 for m in moves}, True
    questions = {
        m["id"]: jc.score(
            f"In this position, how strong is the move \"{m.get('move', m['id'])}\" "
            f"toward the objective: {objective}?",
            criteria,
        )
        for m in moves
    }
    result = jc.ask({"position": state, "objective": objective}, questions)
    if result.get("mock"):
        # No key / unreachable: every move is a neutral 0.5 placeholder, clearly flagged.
        return {m["id"]: 0.5 for m in moves}, True
    answers = result.get("answers", {})
    denom = max(len(criteria) - 1, 1)
    scores = {}
    for m in moves:
        s = jc.score_of(answers.get(m["id"], {}))
        scores[m["id"]] = max(0.0, min(1.0, s / denom))
    return scores, False


def search(node: dict, state, beam: int, depth: int, budget: Budget,
           objective: str = "", criteria=None) -> dict:
    objective = node.get("objective", objective) or "(unspecified)"
    criteria = node.get("criteria", criteria) or DEFAULT_CRITERIA
    player = node.get("player", "us")
    moves = node.get("moves", [])

    if not moves:
        return {"value": 0.5, "best": None, "pv": [], "moves": [], "mock": True,
                "player": player}

    scores, mock = _score_moves(node, state, objective, criteria, budget)
    ordered = sorted(moves, key=lambda m: scores[m["id"]], reverse=(player != "them"))
    kept = ordered[: max(1, beam)]

    evaluated = []
    for m in moves:
        entry = {"id": m["id"], "move": m.get("move", m["id"]),
                 "immediate": round(scores[m["id"]], 3), "pruned": m not in kept}
        if m in kept and m.get("replies") and depth > 0:
            child_state = f"{state}\n[after move: {m.get('move', m['id'])}]"
            sub = search(m["replies"], child_state, beam, depth - 1, budget,
                         objective, criteria)
            entry["value"] = sub["value"]
            entry["pv"] = [entry["id"]] + sub["pv"]
            entry["replies"] = sub
            mock = mock or sub["mock"]
        else:
            entry["value"] = round(scores[m["id"]], 3)
            entry["pv"] = [entry["id"]]
        evaluated.append(entry)

    considered = [e for e in evaluated if not e["pruned"]]
    if player == "them":
        best = min(considered, key=lambda e: e["value"])
        node_value = best["value"]
    elif player == "chance":
        total = sum(e["value"] for e in considered) or 1.0
        node_value = sum(e["value"] * e["value"] for e in considered) / total
        best = max(considered, key=lambda e: e["value"])
    else:  # "us"
        best = max(considered, key=lambda e: e["value"])
        node_value = best["value"]

    return {"value": round(node_value, 3), "best": best["id"], "pv": best["pv"],
            "moves": evaluated, "mock": mock, "player": player,
            "objective": objective}


# --- pretty trace ------------------------------------------------------------

def render(result: dict, indent: int = 0) -> str:
    pad = "  " * indent
    lines = []
    for e in result.get("moves", []):
        mark = "·" if e.get("pruned") else ("➤" if e["id"] == result.get("best") else "•")
        flag = " [pruned]" if e.get("pruned") else ""
        look = f"  (imm {e['immediate']} → line {e['value']})" if "replies" in e else ""
        lines.append(f"{pad}{mark} {e['id']}: {e['move']}  [{e['value']}]{look}{flag}")
        if "replies" in e:
            lines.append(render(e["replies"], indent + 1))
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
    print(f"BEST MOVE: {result['best']}  (line value {result['value']})")
    print(f"Principal variation: {' → '.join(result['pv']) or '(none)'}")
    print(f"beam={beam} depth={depth}  Jev calls used: {MAX_CALLS - budget.left}")
    if result["mock"]:
        print("MOCK mode — TYPESAFE_API_KEY unset; scores are neutral placeholders.")
    print("\nSearch tree (➤ chosen, · pruned):")
    print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
