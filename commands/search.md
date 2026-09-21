---
description: Search candidate options with Jev as the judge — propose options, score each level, look ahead, pick the best outcome.
argument-hint: "<the decision to search> — or a spec.json path + \"<state>\""
---

Pick the best option by **searching with Jev as the evaluator**: $ARGUMENTS

The split: **you generate the options, Jev judges them.**

If given a spec + state, run it. Otherwise build the search from the decision described:

1. **Generate candidate options.** Propose the 2–5 realistic things you could do next (the
   "options") for the current state. Don't pre-judge — that's Jev's job.

2. **Add lookahead where it matters.** For the promising options, propose the likely
   follow-on (`next`) — especially the worst-case outcomes (a `"mode":"minimize"` node) that
   model what could go wrong. This is where search beats scoring options in isolation.

3. **Score each level with Jev.** Build the spec per `skills/jeveloper/reference/mode-search.md`
   and run it (one batched Jev call judges a whole level in parallel):

   ```bash
   python3 skills/jeveloper/scripts/jev_search.py <spec.json> "<state>" [beam] [depth]
   ```

4. **Report** the recommended option, the **best path**, and — importantly — call out any
   option whose *immediate* look was good but whose *outcome* backs up badly (the traps
   lookahead caught). Note the Jev call count.

5. `MOCK` (no `TYPESAFE_API_KEY`) → scores are neutral 0.5 placeholders; the search shape is
   valid but not a real judgement. The search **advises** — make and verify the choice yourself.

Read `skills/jeveloper/reference/mode-search.md` first.
