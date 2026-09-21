---
description: Ask Jev to pick the best option (model, subagent, approach) for a task — a fast, cheap routing decision.
argument-hint: "<the task, then the options> e.g. 'rename a symbol across 40 files: haiku sonnet opus'"
---

Use **Jev** to make a routing decision, not Claude's tokens: $ARGUMENTS

1. From the argument, identify the **task** (the state) and the **options** to choose
   among (models, subagents, strategies…). If the options aren't clear, ask once.

2. Call Jev with a Choice question via the CLI, giving each option a short `value:desc`:

   ```bash
   python3 skills/jeveloper/scripts/jev_ask.py choice "<the task/state>" \
     "Which option best fits this task?" \
     opt1:short-description opt2:short-description ...
   ```

3. Report Jev's `choice`, the per-option `probabilities`, and `confidence`. If the result
   is `"mock": true`, say the key is unset so this is a placeholder, not a real routing
   decision.

4. Treat it as **advice**: state the recommendation and proceed (or let the user decide).
   Low confidence or a near-tie → say so rather than pretending Jev was decisive.

Read `skills/jeveloper/reference/mode-route.md` if you need the routing rationale.
