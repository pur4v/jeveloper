# Worked example — option search with Jev as the judge

`fix-flaky-test.json` searches *"how do I fix this flaky test?"* — three candidate options,
each with a one-step **worst-case** lookahead (`"mode":"minimize"` = assume the least
favorable outcome).

```
fix_flaky_test                    (maximize)
├─ add_retry        "retry 3×"     → minimize: [ masks_race | slows_ci ]
├─ fix_race         "fix the race" → minimize: [ wrong_root_cause | perf_regression ]
└─ delete_test      "delete it"
```

Run it (keyless → every option scores a neutral `0.5`, flagged MOCK):

```bash
python3 ../../skills/jeveloper/scripts/jev_search.py fix-flaky-test.json \
  "Test test_checkout_race fails ~1 in 8 runs; touches a shared cart cache." 2 3
```

## Why the answer isn't the greedy one (illustrative scores)

| Option | now | worst outcome | backed-up value |
|---|---|---|---|
| `add_retry` | 0.50 | `masks_race` **0.00** | **0.00** |
| `fix_race` | **1.00** | `wrong_root_cause` 0.50 | **0.50** ← best |
| `delete_test` | 0.00 | — | pruned by beam=2 |

Judged only on the immediate look, `fix_race` ranks top and `add_retry` second — both seem
acceptable. But the `"minimize"` node (worst-case lookahead) exposes that **retrying masks a
real production race** (worst outcome 0.00), a trap a single look would miss. `fix_race`
backs up to 0.50, so the search recommends it with best path `fix_race → wrong_root_cause`,
and the trace shows exactly which outcome pinned each option's value. `delete_test` never
gets a lookahead — beam pruning drops it first.

The whole search here is a handful of batched Jev calls (one per node visited), because Jev
judges every option at a level in parallel.

## Make your own

- 2–5 candidate options per node — the things Claude would actually consider doing.
- Add `next` only to the options worth looking past; use `"mode":"minimize"` for worst-case
  robustness, `"average"` for uncertain outcomes, `"maximize"` for your own follow-up choice.
- Tune `beam` (how many options survive per level) and `depth` (how far to look) on the CLI.
- Keep `objective` sharp — it's what Jev judges every option against.
