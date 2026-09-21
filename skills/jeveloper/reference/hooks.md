# Hooks, wiring, and config

## How the reflexes are wired

`hooks/hooks.json` (at the plugin root) registers three Claude Code hooks when the plugin
is installed. Each runs a stdlib-only Python script via `${CLAUDE_PLUGIN_ROOT}`:

| Event | Matcher | Script |
|---|---|---|
| `PreToolUse` | `Bash\|Edit\|Write\|MultiEdit\|NotebookEdit` | `scripts/route_gate.py` |
| `PostToolUse` | `Bash\|Edit\|Write\|MultiEdit\|Task` | `scripts/check_output.py` |
| `Stop` | (all) | `scripts/warden.py` |

Registration ≠ activation. Every script first loads config and **exits 0 immediately** if
jeveloper (or that reflex) is disabled — which is the default. So installing the plugin is
inert until you opt in.

## Hook I/O contracts used

- **PreToolUse** reads `{tool_name, tool_input, …}`; may return
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow|deny|ask", "permissionDecisionReason": "…"}}`.
- **PostToolUse** reads `{tool_name, tool_input, tool_response, …}`; may return
  `{"decision": "block", "reason": "…"}` to surface feedback to Claude.
- **Stop** reads `{session_id, transcript_path, stop_hook_active, …}`; may return
  `{"decision": "block", "reason": "…"}` to force continuation.

In all cases, exit 0 with no stdout = "no opinion, proceed normally". jeveloper leans on
that path hard (see the fail-open discipline).

## `.jeveloper.json` — full schema

Lives in the **project root** (the cwd Claude runs in). Written by `/jeveloper:setup`.

```json
{
  "enabled": true,
  "goal": "Ship the CSV export endpoint with tests and docs",

  "route": {
    "enabled": true,
    "tools": ["Bash"],
    "deny_threshold": 0.85,
    "ask_threshold": 0.60
  },
  "check": {
    "enabled": true,
    "fail_threshold": 0.80
  },
  "warden": {
    "enabled": true,
    "done_threshold": 7.0,
    "max_continues": 3
  }
}
```

- `enabled` — master switch. Ships `false`. `JEVELOPER_ENABLED=1`/`0` overrides it.
- `goal` — optional standing objective the Warden judges completeness against.
- Per-reflex `enabled` lets you run, say, only Check + Warden and leave the gate off.
- Later sources win: DEFAULTS → `.jeveloper.json` → `JEVELOPER_ENABLED` env.

## Environment variables

| Var | Purpose | Default |
|---|---|---|
| `TYPESAFE_API_KEY` | Jev auth. Unset → MOCK mode → all reflexes fail open | — |
| `JEVELOPER_ENABLED` | master-switch override (`1`/`0`) | (config) |
| `JEVELOPER_API_URL` | Jev endpoint | `https://api.typesafe.ai/v1/systemone` |
| `JEVELOPER_MODEL` | model id | `jev-latest` |
| `JEVELOPER_TIMEOUT` | request timeout, seconds | `5` |
| `JEVELOPER_DEBUG` | print fail-open reasons to stderr | off |

## Debugging

Run any script by hand with a sample event on stdin:

```bash
printf '{"tool_name":"Bash","tool_input":{"command":"rm -rf build"}}' \
  | JEVELOPER_ENABLED=1 JEVELOPER_DEBUG=1 \
    python3 skills/jeveloper/scripts/route_gate.py; echo "exit=$?"
```

With no key you'll see the fail-open reason (`mock/keyless`). With a key and `enabled`,
you'll see a real `permissionDecision` when Jev crosses a threshold.
