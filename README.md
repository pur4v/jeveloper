<div align="center">

<img src="banner.png" alt="jeveloper" width="100%" />

# jeveloper ⚡

**A System-1 reflex layer for Claude Code, powered by [Jev](https://www.typesafe.ai).**

[![CI](https://github.com/pur4v/jeveloper/actions/workflows/ci.yml/badge.svg)](https://github.com/pur4v/jeveloper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Skill](https://img.shields.io/badge/Claude-Agent%20Skill-8A63D2)](https://docs.claude.com/en/docs/agents-and-tools/agent-skills)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-000000)](https://docs.claude.com/en/docs/claude-code)

</div>

Jev is a **System One** model from TypeSafe AI — fast, intuitive, one-pass, and *typed*.
It doesn't write prose; it takes state + typed questions and returns typed probabilistic
decisions in ~70–500 ms for ~$0.042 per **million** input tokens (output free). Claude is
System Two: deliberate, powerful, expensive.

`jeveloper` wires Jev in as Claude's **reflexes** — cheap, instant judgements that fire
automatically in the agent loop so the slow reasoner spends its effort on the work instead
of on second-guessing every step: *is this command safe? did that test really pass? are we
actually done?*

---

## The three reflexes

| Reflex | Hook | Jev decides | You get |
|---|---|---|---|
| 🛑 **Route** | `PreToolUse` | is this call destructive / off-goal? | a fast **safety gate** that denies/asks before a risky tool runs — plus on-demand model routing via `/jeveloper:route` |
| 🔎 **Check** | `PostToolUse` | did this output *actually* succeed & do its job? | the skipped-but-green test, the wrong edit, the buried error — **caught immediately** and fed back to Claude |
| 🧭 **Warden** | `Stop` | is the task genuinely complete & verified? | the loop stops when the **work** is done, not when Claude first feels finished |

## Why Jev, and why in the loop

The decisions above happen constantly and want a *fast, structured, thresholdable* answer —
exactly Jev's shape. At its price and latency you can afford to ask on **every** tool result
and **every** stop. It's ~100× cheaper and faster than an LLM classification call, returns a
calibrated probability you can threshold on, and never hallucinates prose because it never
emits prose.

## The disciplines

1. **Fail OPEN, always.** Disabled, keyless, Jev down, an error, or below threshold → the
   hook exits 0 and the loop proceeds untouched. A guardrail that breaks *your* work when
   *it* breaks is worse than none.
2. **Keyless is inert, not broken.** No `TYPESAFE_API_KEY` → MOCK answers → every reflex
   silent. Installing the plugin does nothing until you set a key **and** opt in.
3. **Act on confidence, not vibes.** Every intervention is a threshold on a Jev probability
   or score, set in `.jeveloper.json`, with the number shown in the reason.
4. **The reflex is a signal, not a verdict.** Check/Warden hand Claude a concern to
   re-examine — Claude still decides. jeveloper narrows attention; it doesn't overrule.

## Install

```
/plugin marketplace add pur4v/jeveloper
/plugin install jeveloper
```

Or use just the skill: copy `skills/jeveloper/` into your `.claude/skills/`.

## Enable (per project)

```bash
export TYPESAFE_API_KEY=…        # from console.typesafe.ai/settings/keys
```
```
/jeveloper:setup "optional standing goal for the Warden"
```

`/jeveloper:setup` writes `.jeveloper.json` (thresholds + master switch), verifies the key,
and runs a live/mock probe. Tune anything in `.jeveloper.json` — see
[`skills/jeveloper/reference/hooks.md`](skills/jeveloper/reference/hooks.md).

## On-demand (no hooks needed)

| Command | Does |
|---|---|
| `/jeveloper:route` | Jev picks among options (models, subagents, approaches) |
| `/jeveloper:check` | Jev verifies an output/claim you paste in |
| `/jeveloper:ask` | any raw typed question — `noul` / `choice` / `score` |
| `/jeveloper:tree` | compose many sub-decisions into one — branched + recursively reduced |

### Decision trees

A hard call is rarely one question. `/jeveloper:tree` (and `scripts/jev_tree.py`) evaluates
a **tree** of Jev sub-decisions — fan them out, branch on the answers, and **recursively
reduce** the leaves to one final decision with a full, auditable trace. Jev answers each
tree *level* in one parallel request, so a dozen sub-decisions cost ~3 batched calls and
exploring multiple branches at once is nearly free. See
[`skills/jeveloper/reference/mode-tree.md`](skills/jeveloper/reference/mode-tree.md) and the
worked spec in [`examples/decision-tree/`](examples/decision-tree/README.md).

## How it fits together

```
                       ┌─────────────────────────── Claude Code loop ───────────────────────────┐
                       │                                                                          │
  user task ──▶ Claude reasons ──▶ tool call ──[PreToolUse]──▶ tool runs ──[PostToolUse]──▶ … ──[Stop]
                       │                 │                             │                      │
                       │             route_gate.py                check_output.py          warden.py
                       │                 │                             │                      │
                       └────────────── Jev (System One) — noul / choice / score, ~100ms ───────┘
                                     TYPESAFE_API_KEY?  no → MOCK → every reflex fails open
```

See a full fictional session in
[`examples/loop-walkthrough/`](examples/loop-walkthrough/README.md).

## What's in the box

```
jeveloper/
├── .claude-plugin/       plugin.json + marketplace.json
├── hooks/hooks.json      registers the three reflexes (inert until enabled)
├── skills/jeveloper/
│   ├── SKILL.md          the skill (three reflexes + disciplines)
│   ├── reference/        jev-api · mode-route · mode-check · mode-warden · hooks
│   └── scripts/          jev_client · jev_config · route_gate · check_output · warden · jev_ask · jev_tree
├── commands/             /jeveloper: setup · route · check · ask · tree
├── agents/               jev-adjudicator (batch typed verification)
└── examples/             loop-walkthrough · decision-tree
```

Zero dependencies — the scripts use only the Python standard library, so the hooks run with
no `pip install`.

## Status & caveats

Jev is new (public early access, Sept 2026). The `noul`/response schema is pinned to
TypeSafe's public examples; the exact request field for **choice/score options** is not
fully documented yet and is isolated in `jev_client.py` so it's a one-line fix once you have
the console docs. Until a key is set, everything runs in safe MOCK mode. See
[`skills/jeveloper/reference/jev-api.md`](skills/jeveloper/reference/jev-api.md).

## License

MIT — see [LICENSE](LICENSE).
