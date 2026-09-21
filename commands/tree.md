---
description: Evaluate a decision TREE over Jev — many sub-decisions, branched and recursively reduced to one answer.
argument-hint: "<spec.json path> \"<state>\"  — or describe the decision and I'll build the tree"
---

Make a composed decision with **Jev**: $ARGUMENTS

If given a spec path + state, run it. If given a decision to make in prose, first **build
the tree**, then run it.

1. **Get or build the spec.** A decision tree is JSON per the schema in
   `skills/jeveloper/reference/mode-tree.md`: nodes with a Jev `question`
   (`noul`/`choice`/`score`), `children` (a list = fan-out, or a map = branch on the
   answer), and a `reduce` op (`and`/`or`/`mean`/`argmax`/…). Decompose the decision into
   the smallest sub-judgements that Jev can answer, and pick the reduce that matches the
   logic ("all must hold" → `and`; "best of" → `argmax`). Use `explore`+`band`/`margin` to
   walk more than one branch when a sub-decision is uncertain.

2. **Run it:**

   ```bash
   python3 skills/jeveloper/scripts/jev_tree.py <spec.json> "<state text or JSON>"
   ```

3. **Report** the final decision and value, then the **trace** — call out which
   sub-decision swung the result, not just the top-line yes/no. Note the (batched) Jev call
   count so the cost is visible.

4. `[MOCK]` on nodes means `TYPESAFE_API_KEY` is unset: the tree's *shape* is valid but the
   0.5 values are placeholders, not judgements. Say so. And remember the tree **advises** —
   confirm anything consequential before acting on it.

Read `skills/jeveloper/reference/mode-tree.md` first if you're building a spec.
