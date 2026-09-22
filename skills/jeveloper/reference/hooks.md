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

  "provider": {
    "use": "auto",            // auto | openrouter | direct   (direct = TypeSafe native)
    "model": "",              // optional model-id override
    "api_url": "",            // optional endpoint override
    "api_key_env": ""         // optional: custom env var holding the key
  },

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
- `provider.use` — `auto` (default) / `openrouter` / `direct`. `JEVELOPER_PROVIDER` overrides
  it. An explicit choice never silently falls back to the other provider. Keys stay in the
  env (`api_key_env`, else the provider default).
- `goal` — optional standing objective the Warden judges completeness against.
- Per-reflex `enabled` lets you run, say, only Check + Warden and leave the gate off.
- Later sources win: DEFAULTS → `.jeveloper.json` → `JEVELOPER_ENABLED` env.

## Environment variables

| Var | Purpose | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | Jev via OpenRouter (preferred if set). Unset + no TypeSafe key → MOCK | — |
| `TYPESAFE_API_KEY` | Jev via TypeSafe native. Both unset → MOCK → all reflexes fail open | — |
| `JEVELOPER_ENABLED` | master-switch override (`1`/`0`) | (config) |
| `JEVELOPER_PROVIDER` | provider override: `auto`/`openrouter`/`direct` | (config) |
| `JEVELOPER_API_URL` | override the Jev endpoint | provider default |
| `JEVELOPER_MODEL` | override the model id | provider default |
| `JEVELOPER_TIMEOUT` | request timeout, seconds | `5` |
| `JEVELOPER_METRICS` | metrics log path | `.jeveloper/metrics.jsonl` |
| `JEVELOPER_TOKENS_PER_DECISION` | per-decision estimate for the meter | `500` |
| `JEVELOPER_DEBUG` | print fail-open reasons to stderr | off |

Provider auto-detection: `OPENROUTER_API_KEY` → OpenRouter decisions API; else
`TYPESAFE_API_KEY` → TypeSafe native; else MOCK. See `reference/jev-api.md`.

## Debugging

Run any script by hand with a sample event on stdin:

```bash
printf '{"tool_name":"Bash","tool_input":{"command":"rm -rf build"}}' \
  | JEVELOPER_ENABLED=1 JEVELOPER_DEBUG=1 \
    python3 skills/jeveloper/scripts/route_gate.py; echo "exit=$?"
```

With no key you'll see the fail-open reason (`mock/keyless`). With a key and `enabled`,
you'll see a real `permissionDecision` when Jev crosses a threshold.
