# Search — Jev as an evaluation function (the chess analogy)

A chess engine doesn't "reason" about a position — it **generates** candidate moves, scores
each with a fast **evaluation function**, keeps the strongest, looks ahead at the likely
replies, and backs the scores up (minimax) to pick the move that leads to the best *line*.

`jev_search.py` runs that loop for an agent's decisions:

| Chess | jeveloper |
|---|---|
| position | the state |
| candidate moves | actions/approaches **Claude proposes** |
| evaluation function | **Jev** scoring each move (`score`, 0..1) |
| evaluating a whole ply | **one batched Jev call** (all moves scored in parallel) |
| move ordering / keep best | **beam** — keep Jev's top-`beam`, prune the rest |
| look ahead N plies | recurse into each kept move's `replies` |
| opponent's best reply | a `"them"` ply → **worst-case** (minimax minimizer) |
| backing scores up | minimax/expectimax backup → recommend the best *line* |

The division of labor is jeveloper's whole thesis: **Claude generates (System-2), Jev
evaluates (System-1).** Jev never invents moves; it judges the ones Claude proposes. And
because a ply is one ~100 ms call, real lookahead is cheap.

## Why lookahead matters (not just greedy eval)

The immediate best-looking move can be a trap. In the worked example
(`examples/move-search/`), "add a retry" and "fix the race" both *look* fine immediately —
but a one-ply adversarial lookahead exposes that retrying **masks a real production race**
(worst-case value 0.0), while the race fix's worst case is merely "wrong root cause" (0.5).
Minimax backs those up and recommends the race fix. Greedy eval would have missed it.

## Plies and players

Each node has a `player` that sets how its children back up:

- `"us"` (default) — **maximize**: our move; we pick the strongest.
- `"them"` — **minimize**: model the environment/failure/adversary picking the worst reply
  for us. Use this for robust "what could go wrong after this move" lookahead.
- `"chance"` — **expectimax**: score-weighted average of replies (uncertain outcomes).

A move with `replies` is an internal node (its value = the backed-up subtree). A move with
no `replies` is a leaf (its value = Jev's immediate score). Immediate scores are always used
for **move ordering and beam pruning**; lookahead only *refines* the kept moves' values.

## Spec

```json
{
  "id": "root",
  "objective": "what a good move should achieve",
  "player": "us",
  "criteria": ["losing","weak","even","promising","winning"],
  "moves": [
    { "id": "m1", "move": "do X", "replies": { "player": "them", "moves": [ ... ] } },
    { "id": "m2", "move": "do Y" }
  ]
}
```

`objective` and `criteria` are inherited by descendants unless overridden. `criteria` is the
ordered score scale (low→high), normalized to 0..1.

## Run it

```bash
python3 skills/jeveloper/scripts/jev_search.py <spec.json> "<state>" [beam] [depth]
```

Prints the recommended **best move**, the **principal variation** (the line), the beam/depth
and how many batched Jev calls it spent (hard-capped at `MAX_CALLS=64`), and a tree marked
`➤` (chosen) / `·` (pruned) with each move's immediate score and backed-up line value.
Keyless → every move scores a neutral `0.5`, flagged MOCK, so you can validate a spec's
shape offline.

## Driving it live (Claude generates the moves)

The static spec is for testing and for decisions whose options you can enumerate. In the
loop, use `/jeveloper:search`: Claude proposes the candidate moves (and their likely
replies), Jev scores each ply, and the search recommends the move with the best line. Same
discipline as everywhere else — Jev's scores are fast estimates and the search **advises**;
Claude still makes and verifies the move.
