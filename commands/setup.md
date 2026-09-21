---
description: Enable jeveloper for this project — write .jeveloper.json, verify the Jev API key, and show a live probe.
argument-hint: "[optional: a standing goal for the Warden to judge completeness against]"
---

Set up **jeveloper** in the current project. Any argument is the standing `goal`: $ARGUMENTS

Do this in order:

1. **Check the key.** Confirm `TYPESAFE_API_KEY` is set in the environment. If it is not,
   tell the user jeveloper will run in inert MOCK mode (all reflexes fail open) until they
   `export TYPESAFE_API_KEY=…` from https://console.typesafe.ai/settings/keys — then
   continue setup anyway (a keyless install is valid and safe).

2. **Write `.jeveloper.json`** in the project root using the schema in
   `skills/jeveloper/reference/hooks.md`. Set `enabled: true`, set `goal` to the argument
   if one was given (else leave `""`), and keep the default thresholds unless the user
   asked otherwise. Do NOT overwrite an existing `.jeveloper.json` without showing the diff
   and confirming.

3. **Probe.** Run the client smoke test and report whether it came back live or mock:

   ```bash
   python3 skills/jeveloper/scripts/jev_client.py "tests: 3 passed, 1 skipped"
   ```

   `"mock": true` → keyless/unreachable (reflexes inert). `"mock": false` → live.

4. **Report** what's now active: which reflexes are enabled, their thresholds, the goal,
   and the one-line reminder that everything fails open. Point the user at
   `skills/jeveloper/reference/hooks.md` for tuning.

Read `skills/jeveloper/reference/hooks.md` first.
