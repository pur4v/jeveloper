---
description: Run the Jev-driven loop — Jev decides each next action, you execute it, Jev verifies the output, repeat. Offloads deliberation to cut thinking-token cost.
argument-hint: "<the objective to drive toward>"
---

Enter **driver mode**: let Jev do the deciding so you spend far fewer reasoning tokens.
Objective: $ARGUMENTS

The whole point is to **stop deliberating and defer to Jev**. Do NOT write long chains of
reasoning about what to do next — that is the token cost we are removing. Your job each step
is to *enumerate cheaply and execute*; Jev's job is to *decide*; Jev's job again is to
*verify*. It's a ping-pong.

**First:** if extended/interleaved thinking is on, note that driver mode wants it minimal —
keep your own reasoning to a terse line or two per step.

**Loop, until done:**

1. **Assess briefly.** One line on the current state. No deep analysis.
2. **Enumerate 2–5 candidate next actions** as short `id:label` pairs — the concrete things
   you could do now (a command to run, an edit to make, or a *subagent to spawn*). Don't
   pre-judge which is best; that is Jev's call.
3. **Let Jev decide:**

   ```bash
   python3 skills/jeveloper/scripts/jev_next.py "<one-line state>" "<objective>" \
     id1:"label" id2:"label" id3:"label"
   ```

   Read `chosen`. **Follow it.** Only override if the chosen action is impossible or
   malformed — and if you do, say so in one line. If `mock` is true (no key), Jev abstained:
   decide yourself this once and note it.
4. **Execute** the chosen action with a single tool call.
5. **Jev verifies automatically** (the PostToolUse Check hook). If it blocks with a concern,
   fix the specific thing and re-run — don't re-litigate the whole plan.
6. **Repeat.** The Stop/Warden hook holds the loop open until the objective is genuinely met.

**At the end**, show what the deferral bought:

```bash
python3 skills/jeveloper/scripts/jev_meter.py report
```

Report the recommended-and-executed path, and the decisions offloaded + estimated
thinking-tokens saved (say plainly it's an estimate). Driver mode fits **decision-heavy,
well-scoped** work; for open-ended design, drop back to normal mode — Jev decides, it doesn't
design. Read `skills/jeveloper/reference/mode-drive.md` first.
