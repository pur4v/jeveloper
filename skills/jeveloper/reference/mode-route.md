# Route — the PreToolUse reflex (+ on-demand routing)

## The honest architecture

Claude Code does **not** let an external model pick Claude's tools — Claude decides its own
tool calls internally, and no hook can substitute a different choice. So "use Jev for tool
selection" splits into two truthful pieces:

1. **The gate (automatic, `PreToolUse`).** A hook cannot *choose* the tool, but it can
   **veto** a dangerous or off-goal one *before it executes*. That is `route_gate.py`.
2. **The router (on-demand, `/jeveloper:route`).** Choosing *among approaches* — which
   model, which subagent, which of several strategies — is a decision Claude makes while
   reasoning. jeveloper exposes it as a command Claude (or you) can call, not a hook that
   silently rewrites the plan.

Don't pretend the gate is doing routing. It is a safety veto with a confidence number.

## The gate: `route_gate.py`

For each matched tool call (default: `Bash`), Jev is asked two `noul` questions against the
tool input + the configured `goal`:

- `unsafe` — destructive/irreversible (deletes/overwrites, force-push, drops resources,
  exfiltrates secrets, touches systems outside the project).
- `out_of_scope` — unrelated to, or working against, the stated goal.

`risk = max(unsafe, out_of_scope)`, then:

| risk | decision |
|---|---|
| ≥ `deny_threshold` (0.85) | `deny` — the call is blocked, reason surfaced |
| ≥ `ask_threshold` (0.60) | `ask` — the user is prompted to confirm |
| below | silent allow (hook exits 0) |

Output uses the `PreToolUse` contract:

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse",
  "permissionDecision": "deny|ask|allow",
  "permissionDecisionReason": "jeveloper (Jev gate): …p=0.91"}}
```

### Tuning

`.jeveloper.json → route`:

```json
{"route": {"enabled": true, "tools": ["Bash"], "deny_threshold": 0.85, "ask_threshold": 0.60}}
```

- `tools`: which tool names the gate applies to (empty = all it receives). Keep this
  narrow — gating `Read`/`Grep` adds latency for no safety benefit.
- Raise thresholds if the gate is noisy; lower them for a locked-down repo.

### Fail-open cases (exit 0, no decision)

route disabled · tool not in `tools` · keyless/mock · Jev error · risk below `ask_threshold`.

## The router: `/jeveloper:route`

Give Jev a `choice` and let it pick. Canonical use is model/effort routing:

```
jev_ask.py choice "Rename a symbol across 40 files, mechanical" \
  "Which model tier fits this task?" \
  haiku:cheap-and-fast sonnet:balanced opus:hardest-reasoning
```

Jev returns the `choice` plus per-option `probabilities` and a `confidence`. Use it to
send the boring 80% of tasks to a cheap path and reserve the expensive reasoner for the
20% that need it. This is advisory — Claude acts on the recommendation.
