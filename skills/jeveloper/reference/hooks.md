# Hooks, wiring, and config

## How the reflexes are wired

`hooks/hooks.json` (at the plugin root) registers four Claude Code hooks when the plugin
is installed. Each runs a stdlib-only Python script via `${CLAUDE_PLUGIN_ROOT}`:

| Event | Matcher | Script | Role |
|---|---|---|---|
| `UserPromptSubmit` | (all) | `scripts/drive_inject.py` | **drive** — inject "defer to Jev" each turn |
| `PreToolUse` | `*` (all tools) | `scripts/route_gate.py` | **route** — gate the call |
| `PostToolUse` | `*` (all tools) | `scripts/check_output.py` | **check** — verify the output |
| `Stop` | (all) | `scripts/warden.py` | **warden** — hold the loop open |

Registration ≠ activation. Every script first loads config and **exits 0 immediately** if
jeveloper (or that reflex) is disabled. The master switch defaults to `"auto"` → **on when a
Jev key is in the environment**, off otherwise — so a fresh install is inert until a key is
set, then **all four** (drive + route + check + warden) activate automatically, on every
tool and every turn.

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

All fields are optional — a key in the env is enough to run. Values shown are the defaults.

```json
{
  "enabled": "auto",          // auto = on when a Jev key is set; or true / false to force
  "goal": "Ship the CSV export endpoint with tests and docs",

  "provider": {
    "use": "auto",            // auto | openrouter | direct   (direct = TypeSafe native)
    "model": "",              // optional model-id override
    "api_url": "",            // optional endpoint override
    "api_key_env": ""         // optional: custom env var holding the key
  },

  "drive":  { "enabled": true },   // Jev decides every action (injected each turn)
  "route": {
    "enabled": true,          // gate every tool call
    "tools": [],              // [] = every tool the "*" matcher sends; narrow to reduce cost
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

- `enabled` — master switch. Defaults to `"auto"` (on when a Jev key is present). Set `true`/
  `false` to force; `JEVELOPER_ENABLED=1`/`0` overrides everything.
- `provider.use` — `auto` (default) / `openrouter` / `direct`. `JEVELOPER_PROVIDER` overrides
  it. An explicit choice never silently falls back to the other provider. Keys stay in the
  env (`api_key_env`, else the provider default).
- `drive.enabled` — Jev drives every turn (default true). Set false to stop the injected
  "defer to Jev" instruction and go back to Claude deciding on its own.
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
