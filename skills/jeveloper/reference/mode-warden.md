# Warden — the Stop reflex

## What it does

When Claude is about to stop, `warden.py` reconstructs the objective and recent activity
from the transcript and asks Jev:

- `completeness` (**score**) — how complete the objective is, judged only by the work shown.
- `criteria_met` (**noul**) — every acceptance criterion is met **and verified** (not merely
  attempted).
- `blocked` (**noul**) — the agent is genuinely blocked / waiting on the user.

Decision:

- `blocked ≥ 0.70` → let it stop (continuing alone won't help). Reset the counter.
- `score ≥ done_threshold` **and** `criteria_met ≥ 0.5` → let it stop. Reset the counter.
- otherwise → **block the stop** and hand Claude a note on what's missing:

```json
{"decision": "block",
 "reason": "jeveloper (Jev warden) thinks the task isn't finished (completeness 5.0/10…). Objective: …. Continue until it's truly done. (Warden pass 1/3.)"}
```

On the `Stop` event, `decision: block` forces Claude to keep going with `reason` as
guidance — turning "Claude stops when it feels done" into "the loop stops when the work is
actually done."

## The objective it judges against

1. `goal` from `.jeveloper.json`, if set (best — a stable target across the session), else
2. the most recent user request found in the transcript.

Set `goal` when you want the warden to hold Claude to a specific definition of done for a
long task; leave it empty for ad-hoc work.

## Safety rails (so it can never trap you)

- **`max_continues` (default 3):** a per-session counter in the temp dir caps how many times
  the warden may re-open the loop in a row. Hit the cap → it stops blocking and resets.
- **Fail-open** on: warden disabled · keyless/mock · Jev error · transcript unreadable ·
  score at/above threshold · `blocked` high.
- The counter resets whenever the task is judged done or blocked, so a *later* genuine
  stall still gets its full budget.

## Tuning

`.jeveloper.json → warden`:

```json
{"warden": {"enabled": true, "done_threshold": 7.0, "max_continues": 3}}
```

- Lower `done_threshold` for lenient "good enough" stops; raise it toward 9 to insist on
  fully-verified completion.
- `max_continues` 1–2 for a light nudge; higher only if you trust the loop and the goal is
  crisp.

## Note on score normalization

Jev's `score` lands on the ordered `criteria` scale you pass (here 4 levels, so ~0–3).
`warden.py` rescales a small-scale score onto 0–10 before comparing to `done_threshold`, so
the threshold is always expressed in familiar 0–10 terms regardless of how many levels the
question uses.
