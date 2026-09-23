---
description: Deep-reasoning mode — reason thoroughly and let Jev evaluate with lookahead (search/tree) instead of a fast pick. For hard, high-stakes, or ambiguous decisions.
argument-hint: "<the hard decision / task to reason deeply about>"
---

Reason deeply about this, with **Jev as the lookahead evaluator** — rigour over token-thrift:
$ARGUMENTS

Unlike the default fast reflex (a one-shot `jev_path` pick that saves tokens), deep mode thinks
the problem through and evaluates the whole decision tree:

1. **Reason through the problem** — state the real trade-offs and constraints; don't shortcut.
2. **Enumerate candidate paths AND their likely follow-ons** (including the worst cases).
3. **Evaluate with lookahead** — one batched Jev call per level:

   ```bash
   python3 skills/jeveloper/scripts/jev_search.py <spec.json> "<state>" [beam] [depth]
   # or, to compose many sub-decisions into one:
   python3 skills/jeveloper/scripts/jev_tree.py <spec.json> "<state or JSON>"
   ```

4. **Act on the backed-up best *outcome*** — the option that wins after lookahead, not the one
   that only looks best right now. Report the recommended path, the trace (which sub-decision
   swung it), and the Jev call count. Prefix Jev-derived lines with `⟦Jev⟧`.

To make deep reasoning the default for a project, set `"deep": {"enabled": true}` in
`.jeveloper.json` (or export `JEVELOPER_DEEP=1`); otherwise the fast, token-thrifty reflex path
stays the default.
