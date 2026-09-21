#!/usr/bin/env python3
"""jev_tree.py — evaluate a decision TREE over Jev, then recursively reduce it.

The idea: a hard call is rarely one question. It's a tree of smaller decisions —
"should I auto-merge?" = "tests green?" AND "low risk?" AND ("scope creep?" → "…justified?").
This module poses those sub-decisions to Jev, branches on the answers, and folds the leaves
back up into one final decision — cheaply, because Jev evaluates every question at a level
IN PARALLEL, so each level of the tree costs a single batched request.

Two passes:
  * Expand (top-down): a node's answer selects which child branch(es) to walk. With
    `explore`, several plausible branches are walked at once (the "review multiple
    decisions at a time" case).
  * Reduce (bottom-up): each node combines its children via `reduce`. Every value is
    normalized to 0..1 so the operators compose regardless of question type.

Node schema (JSON):
  {
    "id": "unique_id",                         # required
    "question": {                              # optional (omit for a pure combinator node)
      "type": "noul" | "choice" | "score",
      "instructions": "...",
      "options": {"a": "desc", ...},           # choice only
      "criteria": ["low", ..., "high"],        # score only
      "threshold": 0.5                          # noul only (branch cutoff; default 0.5)
    },
    "children":                                # optional
        [ <node>, ... ]                        #   LIST  -> fan-out: all evaluated, then reduced
      | { "<branch>": <node> | [ <node> ] },   #   MAP   -> conditional: the answer picks branch(es)
    "reduce": "and|or|mean|max|min|argmax|first",  # default "mean"
    "explore": false,                          # map children: expand every matching branch
    "margin": 0.15,                            # choice explore: options within margin of the top prob
    "band": [0.35, 0.65]                       # noul explore: walk BOTH branches when prob in band
  }

Branch keys: noul -> "true"/"false"; choice -> the option value; score -> the child-map key
whose name best matches the chosen level.

Values (all 0..1): noul -> P(true); score -> score/(levels-1); choice -> top option prob;
internal node -> its `reduce` over child values. Labels: "yes"/"no", the level, the chosen
option, or (for argmax) the winning child.

CLI:  jev_tree.py <spec.json> "<state>"      # prints final decision + indented trace
      TYPESAFE_API_KEY unset -> every node is MOCK (neutral 0.5, flagged) — the tree still
      renders so you can validate its shape without a key.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client as jc  # noqa: E402

_REDUCERS = {
    "and": min,
    "or": max,
    "min": min,
    "max": max,
    "mean": lambda vs: sum(vs) / len(vs),
    "first": lambda vs: vs[0],
    "argmax": max,  # value is max; label handled specially
}


def _build_question(q: dict) -> dict:
    t = q.get("type")
    if t == "noul":
        return jc.noul(q["instructions"])
    if t == "choice":
        return jc.choice(q["instructions"], q.get("options", {}))
    if t == "score":
        return jc.score(q["instructions"], q.get("criteria", []))
    raise ValueError(f"unknown question type: {t!r}")


def _value_label(q: dict, ans: dict) -> tuple[float, str]:
    """Normalize a Jev answer to (value in 0..1, human label)."""
    t = q.get("type")
    if t == "noul":
        p = jc.noul_of(ans)
        return p, ("yes" if p >= float(q.get("threshold", 0.5)) else "no")
    if t == "score":
        levels = q.get("criteria", [])
        s = jc.score_of(ans)
        denom = max(len(levels) - 1, 1)
        val = max(0.0, min(1.0, s / denom))
        label = levels[min(len(levels) - 1, max(0, round(s)))] if levels else f"{s:.2f}"
        return val, label
    if t == "choice":
        probs = ans.get("probabilities") or {}
        top = max(probs.values()) if probs else jc.confidence_of(ans)
        return float(top), str(ans.get("choice"))
    return 0.5, "?"


def _branch_keys(q: dict, ans: dict, node: dict) -> list[str]:
    """Which child-map branches to expand, given the node's own answer."""
    t = q.get("type")
    if t == "noul":
        p = jc.noul_of(ans)
        band = node.get("band")
        if node.get("explore") and band and band[0] <= p <= band[1]:
            return ["true", "false"]
        return ["true" if p >= float(q.get("threshold", 0.5)) else "false"]
    if t == "choice":
        probs = ans.get("probabilities") or {}
        chosen = str(ans.get("choice"))
        if node.get("explore") and probs:
            top = max(probs.values())
            margin = float(node.get("margin", 0.15))
            return [k for k, v in probs.items() if top - v <= margin]
        return [chosen]
    if t == "score":
        # Match the chosen level name to a child-map key (case-insensitive contains).
        _, label = _value_label(q, ans)
        keys = list((node.get("children") or {}).keys())
        hit = [k for k in keys if k.lower() in label.lower() or label.lower() in k.lower()]
        return hit or keys[:1]
    return []


def _as_node_list(spec) -> list[dict]:
    return spec if isinstance(spec, list) else [spec]


def evaluate_forest(nodes: list[dict], state) -> list[dict]:
    """Evaluate sibling nodes together: ONE batched Jev call for their own questions."""
    questions = {n["id"]: _build_question(n["question"]) for n in nodes if n.get("question")}
    result = jc.ask(state, questions) if questions else {"answers": {}, "mock": False}
    answers = result.get("answers", {})
    mock = result.get("mock", False)
    return [_resolve(n, answers.get(n["id"], {}), mock, state) for n in nodes]


def _resolve(node: dict, ans: dict, mock: bool, state) -> dict:
    dec: dict = {"id": node["id"], "mock": mock}
    q = node.get("question")
    if q:
        val, label = _value_label(q, ans)
        dec["question_type"] = q["type"]
        dec["answer"] = ans
        dec["own_value"] = round(val, 3)
        dec["own_label"] = label

    children = node.get("children")
    reduce_op = node.get("reduce", "mean")

    if not children:
        # Leaf: its value is its own answer.
        dec["value"] = dec.get("own_value", 0.5)
        dec["label"] = dec.get("own_label", "?")
        dec["kind"] = "leaf"
        return dec

    if isinstance(children, dict):
        # Conditional map: the node's answer selects which branch(es) to walk.
        keys = _branch_keys(q, ans, node) if q else list(children.keys())
        selected: list[dict] = []
        for k in keys:
            if k in children:
                selected.extend(_as_node_list(children[k]))
        dec["expanded"] = keys
        child_decs = evaluate_forest(selected, state) if selected else []
        dec["kind"] = "branch"
    else:
        # Fan-out list: evaluate all children, then reduce.
        child_decs = evaluate_forest(children, state)
        dec["kind"] = "fanout"

    dec["children"] = child_decs
    if child_decs:
        vals = [c["value"] for c in child_decs]
        fn = _REDUCERS.get(reduce_op, _REDUCERS["mean"])
        dec["value"] = round(fn(vals), 3)
        dec["reduce"] = reduce_op
        if reduce_op == "argmax":
            best = max(child_decs, key=lambda c: c["value"])
            dec["label"] = best.get("label", best["id"])
        elif reduce_op in ("and", "or"):
            met = [c["value"] >= 0.5 for c in child_decs]
            dec["label"] = "yes" if (all(met) if reduce_op == "and" else any(met)) else "no"
        else:
            dec["label"] = f"{dec['value']:.2f}"
    else:
        # A branch that selected no children -> fall back to the node's own answer.
        dec["value"] = dec.get("own_value", 0.5)
        dec["label"] = dec.get("own_label", "n/a")
    return dec


def evaluate(spec: dict, state) -> dict:
    return evaluate_forest([spec], state)[0]


# --- pretty trace ------------------------------------------------------------

def render(dec: dict, indent: int = 0) -> str:
    pad = "  " * indent
    flag = " [MOCK]" if dec.get("mock") else ""
    own = ""
    if "own_label" in dec and dec.get("kind") != "leaf":
        own = f"  (asked: {dec['own_label']} @ {dec['own_value']})"
    line = f"{pad}• {dec['id']}: {dec.get('label')}  [{dec.get('value')}]{own}{flag}"
    lines = [line]
    for child in dec.get("children", []):
        lines.append(render(child, indent + 1))
    return "\n".join(lines)


def _count_calls(dec: dict) -> int:
    # One batched call per non-empty sibling level: count branch/fanout nodes with children.
    n = 1 if dec.get("children") else 0
    return n + sum(_count_calls(c) for c in dec.get("children", []))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        sys.stderr.write(__doc__ or "")
        return 2
    spec_path, state = argv[0], argv[1]
    try:
        spec = json.load(open(spec_path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"could not read spec {spec_path}: {exc}\n")
        return 2

    dec = evaluate(spec, state)
    print(f"FINAL: {dec['id']} -> {dec.get('label')}  (value {dec.get('value')})")
    print(f"Jev calls (batched levels): ~{_count_calls(dec)}")
    if dec.get("mock"):
        print("MOCK mode — TYPESAFE_API_KEY unset; values are neutral placeholders.")
    print("\nTrace:")
    print(render(dec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
