# Worked example — the three reflexes firing in one loop

A fictional session that shows Route, Check, and Warden doing their jobs. Probabilities are
illustrative (what a well-calibrated Jev *might* return); with no `TYPESAFE_API_KEY` every
reflex here would instead fail open and stay silent.

**Task given to Claude:** *"Add a `/health` endpoint to the API and make sure the tests pass."*
`.jeveloper.json` has `goal: "Add a /health endpoint with a passing test"`, all reflexes on.

---

### 1. Route gates a stray command (`PreToolUse`)

Claude, cleaning up, tries:

```bash
git reset --hard HEAD~5
```

`route_gate.py` → Jev:
- `unsafe` p=**0.93** (irreversible history rewrite), `out_of_scope` p=0.71.
- `risk = 0.93 ≥ deny_threshold (0.85)` →

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse",
  "permissionDecision": "deny",
  "permissionDecisionReason": "jeveloper (Jev gate): looks destructive/irreversible (p=0.93); out-of-scope (p=0.71)"}}
```

Claude sees the denial, drops the reset, and moves on. The `git add`/`Edit` calls it makes
next score low risk and pass silently.

---

### 2. Check catches a hollow test pass (`PostToolUse`)

Claude runs the suite:

```
$ pytest -q
5 passed, 1 skipped in 0.42s
```

It's about to treat this as green. `check_output.py` → Jev:
- `is_failure` p=**0.82** (the one relevant test was *skipped*, not passed), `misses_intent` p=0.55.
- `0.82 ≥ fail_threshold (0.80)` →

```json
{"decision": "block",
 "reason": "jeveloper (Jev check) flagged this tool result: the output looks like a failure/error (p=0.82). Re-read the output and confirm it truly succeeded before continuing; fix and retry if it did not."}
```

Claude re-reads, finds `test_health` is `@pytest.mark.skip`, removes the skip, fixes the
fixture, and re-runs to a real `6 passed`.

---

### 3. Warden keeps the loop honest (`Stop`)

Claude wires the route and the test, then tries to stop. `warden.py` reconstructs the
objective + activity → Jev:
- `completeness` score ≈ **1.8/3 → 6.0/10** (endpoint added, but no test asserting the
  200/body yet — the earlier fix only un-skipped a stub), `criteria_met` p=0.40, `blocked` p=0.05.
- `6.0 < done_threshold (7.0)` and `criteria_met < 0.5` →

```json
{"decision": "block",
 "reason": "jeveloper (Jev warden) thinks the task isn't finished (completeness 6.0/10, criteria-met p=0.40). Objective: Add a /health endpoint with a passing test. … continue until it's truly done. (Warden pass 1/3.)"}
```

Claude adds a real assertion (`resp.status == 200`, body `{"status":"ok"}`), re-runs green.
On the next stop, Jev returns completeness 9.3/10, `criteria_met` p=0.94 → the warden stays
silent, resets its counter, and the session ends — **done because the work is done, not
because Claude stopped typing.**

---

### If the key were unset

Every step above would be a silent exit-0: the `git reset` would run, the skipped test
would pass unchallenged, and Claude would stop when it first felt finished. That's the
fail-open contract — jeveloper only ever *adds* judgement, never removes the default path.
