# Tree — compose many Jev decisions into one

A hard call is rarely a single question. `jev_tree.py` lets you express it as a **decision
tree** of smaller Jev judgements, walk the relevant branches, and **recursively reduce** the
leaves into one final decision — with a full trace you can review.

This is the on-demand counterpart to the three reflexes: the reflexes ask Jev *one* thing at
a fixed point in the loop; the tree asks *many*, structured, when a decision has parts.

## Why it fits Jev

Jev evaluates every question in a request **in parallel**. So one *level* of sibling
questions is a single batched call (~100 ms, a few thousandths of a cent). A three-level
tree with a dozen sub-decisions is ~3 calls, not 12. Exploring several branches is nearly
free, which is what makes "consider multiple decisions at once, then reduce" practical.

## The two passes

1. **Expand (top-down).** A node's answer selects which child branch(es) to walk:
   - `noul` → `"true"` / `"false"` (by `threshold`, default 0.5). With `explore` + `band`,
     walk **both** when the probability is in the uncertain band.
   - `choice` → the chosen option's branch. With `explore` + `margin`, walk every option
     within `margin` of the top probability.
   - `score` → the child-map key that best matches the chosen level.
2. **Reduce (bottom-up).** Each node folds its children with `reduce`. All values are
   normalized to **0..1** so operators compose across question types:

   | `reduce` | value | label |
   |---|---|---|
   | `and` | min(children) | "yes" iff all ≥ 0.5 |
   | `or` | max(children) | "yes" iff any ≥ 0.5 |
   | `mean` | average | the number |
   | `max` / `min` | extreme | the number |
   | `argmax` | max | the winning child's label |
   | `first` | first child | the number |

   Leaf value: `noul` → P(true); `score` → score/(levels−1); `choice` → top option prob.

## Node schema

```json
{
  "id": "unique_id",
  "question": { "type": "noul|choice|score", "instructions": "...",
                "options": {"a":"desc"}, "criteria": ["low","high"], "threshold": 0.5 },
  "children": [ <node>... ]  |  { "<branch>": <node> | [<node>...] },
  "reduce": "and|or|mean|max|min|argmax|first",
  "explore": false, "margin": 0.15, "band": [0.35, 0.65]
}
```

- A node with a **list** of children = fan-out: all evaluated, then reduced.
- A node with a **map** of children = conditional: the node's own answer picks the branch(es).
- A node with a **question and no children** = a leaf.
- A node with **children and no question** = a pure combinator (reduces its subtree).

## Run it

```bash
python3 skills/jeveloper/scripts/jev_tree.py <spec.json> "<state text or JSON>"
```

Prints the final decision, the approximate number of batched Jev calls, and an indented
trace of every node (its label, value, and — for branch nodes — what the node itself
answered and which branches it expanded). Keyless → every node is flagged `[MOCK]` with a
neutral 0.5 so you can validate the *shape* of a tree before you have a key.

Worked spec + expected traces: `examples/decision-tree/`.

## When to reach for it

- A gate/verify/route decision that genuinely has parts ("safe to auto-merge?", "is this
  release ready?", "which remediation path?").
- When you want the branches **auditable** — the trace shows exactly which sub-decision
  swung the result, instead of one opaque yes/no.

Don't build a tree for a single yes/no — that's just `/jeveloper:ask` or a reflex. And
remember the disciplines still hold: mock is no-opinion, the numbers are fast estimates, and
the tree advises — it doesn't act on its own.
