---
description: Search candidate "moves" with Jev as the evaluator (chess-style) — propose moves, score each ply, look ahead, pick the best line.
argument-hint: "<the decision to search> — or a spec.json path + \"<state>\""
---

Pick the best next move by **searching with Jev as the evaluation function**: $ARGUMENTS

Think like a chess engine: **you generate the moves, Jev scores them.**

If given a spec + state, run it. Otherwise build the search from the decision described:

1. **Generate candidate moves.** Propose the 2–5 realistic next actions/approaches (the
   "moves") for the current state. Don't pre-judge — that's Jev's job.

2. **Add lookahead where it matters.** For the promising moves, propose the likely
   **replies** — especially the worst-case ones (a `"player":"them"` node) that model what
   could go wrong after the move. This is where search beats greedy eval.

3. **Score each ply with Jev.** Build the spec per `skills/jeveloper/reference/mode-search.md`
   and run it (one batched Jev call scores a whole ply in parallel):

   ```bash
   python3 skills/jeveloper/scripts/jev_search.py <spec.json> "<state>" [beam] [depth]
   ```

4. **Report** the recommended move, the **principal variation** (the line Jev's eval
   prefers), and — importantly — call out any move whose *immediate* look was good but whose
   *line* backs up badly (the traps lookahead caught). Note the Jev call count.

5. `MOCK` (no `TYPESAFE_API_KEY`) → scores are neutral 0.5 placeholders; the search shape is
   valid but not a real judgement. The search **advises** — make and verify the move yourself.

Read `skills/jeveloper/reference/mode-search.md` first.
