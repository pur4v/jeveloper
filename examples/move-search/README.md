# Worked example — search with Jev as the evaluator

`fix-flaky-test.json` treats *"how do I fix this flaky test?"* like a chess position: three
candidate moves, each with an adversarial one-ply lookahead (`"player":"them"` = worst-case).

```
fix_flaky_test                    (us: maximize)
├─ add_retry        "retry 3×"     → them: [ masks_race | slows_ci ]
├─ fix_race         "fix the race" → them: [ wrong_root_cause | perf_regression ]
└─ delete_test      "delete it"
```

Run it (keyless → every move scores a neutral `0.5`, flagged MOCK):

```bash
python3 ../../skills/jeveloper/scripts/jev_search.py fix-flaky-test.json \
  "Test test_checkout_race fails ~1 in 8 runs; touches a shared cart cache." 2 3
```

## Why the answer isn't the greedy one (illustrative scores)

| Move | immediate | worst-case reply | backed-up line |
|---|---|---|---|
| `add_retry` | 0.50 | `masks_race` **0.00** | **0.00** |
| `fix_race` | **1.00** | `wrong_root_cause` 0.50 | **0.50** ← best line |
| `delete_test` | 0.00 | — | pruned by beam=2 |

Greedy immediate eval ranks `fix_race` top and `add_retry` second — both look acceptable.
But the `"them"` ply (minimax minimizer) exposes that **retrying masks a real production
race** (worst case 0.00), a trap a single-ply look would miss. `fix_race` backs up to 0.50,
so the search recommends it with principal variation `fix_race → wrong_root_cause`, and the
trace shows exactly which reply pinned each move's value. `delete_test` never gets a
lookahead — beam pruning drops it first.

The whole search here is a handful of batched Jev calls (one per ply visited), because Jev
scores every move at a ply in parallel.

## Make your own

- 2–5 candidate moves per node — the actions Claude would actually consider.
- Add `replies` only to the moves worth looking past; use `"player":"them"` for worst-case
  robustness, `"chance"` for uncertain outcomes.
- Tune `beam` (how many moves survive per ply) and `depth` (how far to look) on the CLI.
- Keep `objective` sharp — it's what Jev scores every move against.
