---
description: See jeveloper work in one shot — run a few live Jev decisions and show the measured cost.
argument-hint: ""
---

Show the user jeveloper working, in one step. Run the demo script and report the output:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/demo.sh"
```

It runs a handful of real Jev decisions (is a skipped test a pass? which model for a
mechanical task? pick the next action; should this PR auto-merge?) and prints the measured
Jev cost. If no key is set it runs in MOCK mode — tell the user to
`export OPENROUTER_API_KEY=…` (or `TYPESAFE_API_KEY`) to see real answers.

Keep your summary to the punchline per decision (the number and what it means), not a wall
of JSON.
