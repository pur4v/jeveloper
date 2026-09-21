# Contributing to jeveloper

Thanks for helping make Claude's reflexes faster. jeveloper is small on purpose — a Jev
client, three hooks, a skill, and docs. Keep changes in that spirit.

## Ground rules

1. **Fail open, always.** No change may let a hook block, hang, or crash the user's loop
   because jeveloper is unsure or unavailable. Every new code path needs a fail-open exit
   for: disabled, keyless/mock, network error, timeout, and below-threshold.
2. **Zero dependencies.** The scripts use only the Python standard library so the hooks run
   with no `pip install`. Don't add a third-party import to the hook path.
3. **Keyless must stay safe and useful.** With no `TYPESAFE_API_KEY`, `jev_client.ask()`
   returns `mock=true` and every reflex is silent. Preserve that.
4. **One place for the wire schema.** All Jev request/response field mapping lives in
   `jev_client.py`. If you correct it against the console docs, correct it there only.
5. **Thresholds, not magic.** New interventions must be a documented threshold on a Jev
   probability/score in `.jeveloper.json`, with the number surfaced in the reason string.

## Local checks

Run the same checks CI runs:

```bash
# byte-compile every script
python3 -m py_compile skills/jeveloper/scripts/*.py

# manifests are valid JSON
python3 -c "import json; [json.load(open(f)) for f in ('.claude-plugin/plugin.json','.claude-plugin/marketplace.json','hooks/hooks.json')]"

# keyless smoke test — hooks must fail open (exit 0, no output)
printf '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | python3 skills/jeveloper/scripts/route_gate.py; echo "exit=$?"
python3 skills/jeveloper/scripts/jev_client.py   # prints mock=true
```

## Pull requests

- Keep the diff focused; update `CHANGELOG.md` under `[Unreleased]`.
- If you touch a reflex, update its `reference/mode-*.md`.
- If you add a command or agent, keep its frontmatter `description` present (CI checks it).
- Describe the fail-open behavior of anything new in the PR.

## Commit hygiene

This project follows clean, sole-authored history: clear commit messages, no co-author or
tool-attribution trailers, and no merge commits (rebase to keep history linear). No secrets
in commits — CI and `.gitignore` guard against it, but check your diffs.
