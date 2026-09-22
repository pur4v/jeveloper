---
description: Enable jeveloper for this project — write .jeveloper.json, verify the Jev API key, and show a live probe.
argument-hint: "[optional: a standing goal for the Warden to judge completeness against]"
---

Set up **jeveloper** in the current project. Any argument is the standing `goal`: $ARGUMENTS

Do this in order:

1. **Choose the provider.** jeveloper can reach Jev two ways — ask (or infer) which:
   - **OpenRouter** — set `provider.use: "openrouter"`; key env `OPENROUTER_API_KEY`; model
     `~typesafe/jev-latest`.
   - **Direct** (TypeSafe native) — set `provider.use: "direct"`; key env `TYPESAFE_API_KEY`;
     model `jev-latest`.
   - **Auto** (default) — OpenRouter if `OPENROUTER_API_KEY` is set, else TypeSafe.

   Then check that the chosen provider's key is present in the environment. If not, tell the
   user jeveloper runs in inert MOCK mode until they `export` it (or a custom var named in
   `provider.api_key_env`), and continue setup anyway. **Never echo, store, or commit the
   key** — it lives only in the environment; `.jeveloper.json` records only the provider
   *choice* and the env-var *name*.

2. **Write `.jeveloper.json`** in the project root using the schema in
   `skills/jeveloper/reference/hooks.md`. Set `enabled: true`, set the `provider` block from
   step 1, set `goal` to the argument if one was given (else `""`), and keep the default
   thresholds unless the user asked otherwise. Do NOT overwrite an existing `.jeveloper.json`
   without showing the diff and confirming.

3. **Probe.** Run the client smoke test and report whether it came back live or mock:

   ```bash
   python3 skills/jeveloper/scripts/jev_client.py "tests: 3 passed, 1 skipped"
   ```

   `"mock": true` → keyless/unreachable (reflexes inert). `"mock": false` → live.

4. **Report** what's now active: which reflexes are enabled, their thresholds, the goal,
   and the one-line reminder that everything fails open. Point the user at
   `skills/jeveloper/reference/hooks.md` for tuning.

Read `skills/jeveloper/reference/hooks.md` first.
