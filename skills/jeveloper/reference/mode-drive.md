# Drive — the Jev-driven loop (offload deliberation)

Driver mode is the full ping-pong: **Jev decides the next action, Claude executes it, Jev
verifies the output, repeat.** The reflexes/tree/search let Claude *consult* Jev; driver mode
puts Jev **in the driver's seat** so Claude stops spending reasoning tokens on decisions.

**It's always-on with a key** — the `UserPromptSubmit` hook (`drive_inject.py`) injects the
standing "defer to Jev" instruction into every turn, so this happens automatically without
running any command. `/jeveloper:drive` is just the manual/explicit form. Turn it off with
`{"drive": {"enabled": false}}` in `.jeveloper.json`.

```
objective ─▶ Claude enumerates 2–5 candidate actions (cheap, no deep reasoning)
                     │
                     ▼
              jev_next.py  ── Jev picks one (choice, ~100ms) ──▶ chosen action
                     │
                     ▼
             Claude executes it (one tool call)
                     │
                     ▼
        Check hook ── Jev verifies the output ──▶ ok? loop.  problem? fix + re-run.
                     │
                     ▼   (on stop)
        Warden hook ── Jev judges completion ──▶ done? stop.  not done? keep going.
                     │
                 jev_meter records every decision → /jeveloper:stats
```

## Why this reduces thinking-token cost (and where it doesn't)

Claude's expensive tokens are the *reasoning it spends deciding what to do*. Driver mode
replaces deep chain-of-thought with **shallow enumeration + a Jev `choice`**: Claude lists a
few candidate actions (cheap) and Jev selects (≈free), so the deliberation is offloaded.

Be honest about the ceiling:
- Claude still must read state, propose options, and execute tools — there's a floor.
- **Generation can't be offloaded.** Jev decides; it does not write code or prose. Driver
  mode saves on *deciding*, not on *doing*.
- Every Check/Warden **block costs a turn.** On verification-heavy work the extra turns can
  offset the deliberation saved. Driver mode wins on **decision-heavy, well-scoped** tasks;
  for open-ended design, use normal mode.
- The saving is **estimated, not measured** (see below). Treat it as directional until you
  benchmark against a real key.

## Following Jev vs. overriding

Claude Code cannot *force* Claude to obey an external decision, so driver mode is a
**prompted discipline**: follow `chosen` unless it is impossible or malformed, and say so in
one line when you deviate. If `mock` is true (no key), Jev abstained — decide once, locally,
and note it. This keeps the loop safe (fail-open) while still handing Jev the wheel whenever
it actually has an opinion.

## Subagent selection is just a decision

"Which subagent should handle this?" is a `jev_next` call whose candidate actions are agent
types. No special machinery — spawning the right subagent is the same choice as picking any
other next action.

## Measuring it — the meter

`jev_client.ask()` records every Jev call (best-effort) to `.jeveloper/metrics.jsonl`:
`{kind, calls, decisions, mock}`. `/jeveloper:stats` (or `scripts/jev_meter.py report`)
summarizes: Jev calls (live/mock), decisions offloaded, and an **estimate** of thinking
tokens saved = `live_decisions × JEVELOPER_TOKENS_PER_DECISION` (default 500). Mock calls
offloaded nothing and are excluded. The per-decision figure is an assumption you set, not a
measurement of Claude's counterfactual reasoning — the report says so.

## Config

`.jeveloper.json` (or env):
- `JEVELOPER_TOKENS_PER_DECISION` — the per-decision estimate for the meter (default 500).
- `JEVELOPER_METRICS` — override the metrics log path.
- The Check and Warden reflexes must be enabled for the verify/loop legs to fire; see
  `reference/hooks.md`.
