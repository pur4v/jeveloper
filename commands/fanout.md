---
description: Fan a task out across REAL parallel subagents (native subagent tree), then let Jev adjudicate the outcomes and pick the winner.
argument-hint: "<the task/decision to explore in parallel>"
---

Explore several directions for the **same** task in parallel, then let **Jev** judge: $ARGUMENTS

This is jeveloper's fan-out. Unlike `/jeveloper:search` and `/jeveloper:tree` (Jev-only —
Claude proposes options as text, Jev scores them), fan-out **executes** the directions:
**Claude spawns one real subagent per branch** — so Claude Code's native subagent tree shows
them running in parallel — and **Jev adjudicates** the returned outcomes and picks the best.

Use it only when the directions are genuinely divergent and worth real subagent cost. Each
branch is a real subagent = real tokens; for a cheap "which option" pick with no execution,
use `/jeveloper:search` instead.

1. **Enumerate branches.** Propose 2–4 *distinct* approaches for the task — each a
   self-contained instruction a subagent can run on its own. Keep them genuinely different
   (different strategy/area), not cosmetic variations. Fewer, sharper branches beat many
   overlapping ones.

2. **Fan out — one real subagent per branch, all in a single message** so they run
   concurrently and appear together under `● main` in the native tree:
   - Give each Agent its branch instruction, scoped tight.
   - Ask each to return a **short structured result**: what it did, the key evidence, and a
     one-line self-assessment of how well it met the objective.

3. **Collect** each branch's returned result as it completes.

4. **Adjudicate with Jev** — score the branch *outcomes* and pick the winner in one batched
   call:

   ```bash
   python3 skills/jeveloper/scripts/jev_next.py \
     "<one-line state: N branch outcomes to compare>" \
     "<the objective the branches serve>" \
     b1:"<branch 1 outcome, ≤100 chars>" b2:"<branch 2 outcome>" ...
   ```

   Follow `chosen`. If `mock` is true (no key resolved), say so and pick yourself.

5. **Report** the winning branch, Jev's ranking of the rest (call out any branch that looked
   promising but lost on outcome), and proceed with the winner's result. Note the subagent
   count and the Jev call so the cost is visible.
