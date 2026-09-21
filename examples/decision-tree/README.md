# Worked example — a decision tree over Jev

`auto-merge.json` encodes *"is this PR safe to auto-merge?"* as a tree of Jev sub-decisions,
recursively reduced to one yes/no.

```
auto_merge            (AND)
├─ tests_green                          noul
├─ low_risk           (AND)
│  ├─ no_migrations                     noul
│  └─ no_auth_or_infra                  noul
└─ scope              (explore, ARGMAX) noul → branch
   ├─ true:  creep_justified            noul   (walked only if scope-creep is likely)
   └─ false: scope_ok                   noul   (walked only if scope looks clean)
```

Run it (keyless → every node prints `[MOCK]` with a neutral 0.5, so you can check the shape):

```bash
python3 ../../skills/jeveloper/scripts/jev_tree.py auto-merge.json \
  "PR #42: adds CSV export. CI: 8 passed. No migrations. Touches only the export module."
```

## How it behaves (illustrative, with a live key)

The `scope` node routes on its own answer, and `explore`+`band [0.35,0.65]` means an
*uncertain* scope reading walks **both** sub-branches at once; a confident reading walks
just one. The root `AND` means any single failing pillar sinks the merge:

| Scenario | tests | low_risk | scope answer → branch | **final** |
|---|---|---|---|---|
| clean PR | 0.97 | 0.95 | creep 0.08 → `scope_ok` 0.93 | **yes** 0.93 |
| failing tests | 0.12 | 0.95 | 0.08 → 0.93 | **no** 0.12 |
| justified creep | 0.97 | 0.95 | creep 0.90 → `creep_justified` 0.88 | **yes** 0.88 |
| touches auth | 0.97 | **0.05** | 0.08 → 0.93 | **no** 0.05 |

`and` reduces to the *minimum*, so the trace always shows which pillar decided it — auditable
by construction. The whole thing is ~3 batched Jev calls (root fan-out, `low_risk` fan-out,
`scope` branch), because Jev answers each level's questions in parallel.

## Make your own

Copy `auto-merge.json` and edit. Rules of thumb:
- decompose to the smallest judgements Jev can answer yes/no (or pick/score);
- `and` for "all must hold", `or` for "any suffices", `argmax` for "best branch";
- add `explore` only where walking multiple branches actually changes the outcome;
- keep the state small and specific — Jev's context budget is ~64k tokens per request.
