---
description: Show the Jev decision meter — how many decisions were offloaded to Jev and the estimated thinking-tokens saved.
argument-hint: "[reset]"
---

Show how much deliberation jeveloper has handed to Jev: $ARGUMENTS

```bash
python3 skills/jeveloper/scripts/jev_meter.py report
```

Report the numbers plainly:
- **Jev calls** (live vs. mock) and **decisions offloaded** (live vs. mock), broken down by
  kind (next / check / warden / route / tree / search).
- **Estimated thinking-tokens saved** — and say clearly it's an *estimate* from an assumed
  per-decision cost (`JEVELOPER_TOKENS_PER_DECISION`, default 500), not a measurement. Mock
  calls offloaded nothing and are excluded.

If the argument is `reset`, clear the meter first: `python3 skills/jeveloper/scripts/jev_meter.py reset`.

The log lives at `.jeveloper/metrics.jsonl` (or `$JEVELOPER_METRICS`).
