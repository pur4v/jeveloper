# Search — Jev as the evaluation function

When the decision is *"which option should I pick?"* rather than *"do these conditions
hold?"*, search it: enumerate the candidate options, have Jev score each, keep the best,
look ahead at what each leads to, and back the scores up so you choose the option with the
best *outcome* — not the best immediate look.

The division of labour is jeveloper's thesis in miniature: **Claude generates** the
candidate options (System-2), **Jev judges** them (System-1) — one batched call scores a
whole level in parallel, so lookahead is cheap.

> Analogy, not a constraint: this is the move-ordering + minimax idea a game engine uses,
> with Jev standing in for the hand-written evaluation function. Nothing here is
> game-specific — the "options" are whatever actions Claude would actually consider.

## The loop

- **Evaluate** — Jev scores each option at a node (`score`, one batched call), normalized 0..1.
- **Order + beam** — keep the top `beam` options, prune the rest.
- **Look ahead** — for a kept option with `next`, recurse; its value becomes the backed-up
  value of that subtree. The immediate score is used only for ordering/pruning.
- **Back up**, per the node's `mode`:

  | `mode` | meaning | backup |
  |---|---|---|
  | `maximize` (default) | *we* choose here | take the best child |
  | `minimize` | worst-case / adversarial / "what could go wrong" | take the worst child |
  | `average` | uncertain outcome | score-weighted average of children |

## Why lookahead beats greedy eval

The best-looking option can be a trap. In the worked example (`examples/search/`), "add a
retry" and "fix the race" both look fine immediately — but a one-step `minimize` lookahead
exposes that retrying **masks a real production race** (worst outcome 0.0), while the race
fix's worst case is merely "wrong root cause" (0.5). Backing those up recommends the race
fix. Greedy scoring would have missed it.

## Spec

```json
{
  "id": "root",
  "objective": "what a good option should achieve",
  "mode": "maximize",
  "criteria": ["very poor","poor","fair","good","excellent"],
  "options": [
    { "id": "o1", "label": "do X", "next": { "mode": "minimize", "options": [ ... ] } },
    { "id": "o2", "label": "do Y" }
  ]
}
```

- `objective` and `criteria` are inherited by descendants unless overridden. `criteria` is
  the ordered score scale (low→high), normalized to 0..1.
- An option with `next` is an internal node (value = the backed-up subtree). An option with
  no `next` is a leaf (value = Jev's immediate score).

## Run it

```bash
python3 skills/jeveloper/scripts/jev_search.py <spec.json> "<state>" [beam] [depth]
```

Prints the recommended **best option**, the **best path**, the beam/depth and how many
batched Jev calls it spent (hard-capped at `MAX_CALLS=64`), and a tree marked `➤` (chosen) /
`·` (pruned) with each option's immediate score and backed-up outcome value. Keyless → every
option scores a neutral `0.5`, flagged MOCK, so you can validate a spec's shape offline.

## Driving it live (Claude generates the options)

The static spec is for testing and for decisions whose options you can enumerate up front.
In the loop, use `/jeveloper:search`: Claude proposes the candidate options (and their likely
follow-ons), Jev scores each level, and the search recommends the option with the best
outcome. Same discipline as everywhere else — Jev's scores are fast estimates and the search
**advises**; Claude still makes and verifies the choice.
