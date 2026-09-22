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

## Driver mode — offload the *deciding* to Jev ⚡

The reflexes below are guardrails around Claude. **Driver mode** (`/jeveloper:drive`) flips
the relationship to cut Claude's most expensive tokens — the *reasoning it spends deciding
what to do*:

```
objective ─▶ Claude enumerates 2–5 candidate actions (cheap — no deep reasoning)
                 │
            jev_next ── Jev picks one (choice, ~100 ms, ~free)
                 │
            Claude executes the chosen action
                 │
            Check hook ── Jev verifies the output ──▶ ok → loop · problem → fix + re-run
                 │
            Warden hook ── Jev judges completion ──▶ done → stop · not done → keep going
```

A continuous ping-pong: **Jev decides, Claude executes, Jev verifies, repeat.** Picking
*which subagent to spawn* is just one such decision. Every decision is metered, so the
saving is reported by `/jeveloper:stats`, not asserted.

Honest limits: generation can't be offloaded (Jev decides, it doesn't write code), each
verify-block costs a turn, and the token saving is an **estimate** until benchmarked with a
real key. It wins on **decision-heavy, well-scoped** work. See
[`skills/jeveloper/reference/mode-drive.md`](skills/jeveloper/reference/mode-drive.md).

## One idea: Jev is the judge

Every capability is the same move — put something in front of Jev and act on its verdict.
The reflexes each hand the judge one artifact at a fixed point in the loop; the tree and
search are that judge scaled up.

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
# pick ONE provider — key stays in the env, never in a file:
export OPENROUTER_API_KEY=sk-or-…   # Jev via OpenRouter (model typesafe/jev-latest)
#   …or…
export TYPESAFE_API_KEY=…           # Jev direct (TypeSafe native)
```
```
/jeveloper:setup "optional standing goal for the Warden"
```

`/jeveloper:setup` records the **provider choice** (`auto` / `openrouter` / `direct`) and the
env-var *name* in `.jeveloper.json` — never the key itself — then verifies and probes it.
Auto-detect uses OpenRouter if its key is set, else TypeSafe; force one with
`provider.use` or `JEVELOPER_PROVIDER`.

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
| `/jeveloper:search` | search candidate *options* with Jev as the judge — beam + lookahead |
| `/jeveloper:drive` | run the Jev-driven loop — Jev decides → you execute → Jev verifies → repeat |
| `/jeveloper:stats` | decisions offloaded to Jev + estimated thinking-tokens saved |

### Decision trees

A hard call is rarely one question. `/jeveloper:tree` (and `scripts/jev_tree.py`) evaluates
a **tree** of Jev sub-decisions — fan them out, branch on the answers, and **recursively
reduce** the leaves to one final decision with a full, auditable trace. Jev answers each
tree *level* in one parallel request, so a dozen sub-decisions cost ~3 batched calls and
exploring multiple branches at once is nearly free. See
[`skills/jeveloper/reference/mode-tree.md`](skills/jeveloper/reference/mode-tree.md) and the
worked spec in [`examples/decision-tree/`](examples/decision-tree/README.md).

### Option search — Jev as the evaluation function

Sometimes the question isn't *"do these conditions hold?"* but *"which option do I pick?"*.
`/jeveloper:search` (and `scripts/jev_search.py`): **Claude proposes** candidate options,
**Jev judges** each (one batched, parallel call), a **beam** keeps the strongest, lookahead
recurses into each option's likely follow-on (a `"minimize"` node models the worst case), and
the scores **back up** — so the recommended option is the one with the best *outcome*,
catching the option that looks fine now but backs up badly. See
[`skills/jeveloper/reference/mode-search.md`](skills/jeveloper/reference/mode-search.md) and
[`examples/search/`](examples/search/README.md).

It's ordinary lookahead search — the move-ordering + minimax idea, with **Jev as the
evaluation function** instead of a hand-written one. Nothing about it is game-specific; the
"options" are whatever actions Claude would actually consider.

|  | generate | evaluate | prune | look ahead | decide |
|---|---|---|---|---|---|
| **search** | options **Claude proposes** | **Jev** (`score`, one call per level) | **beam** (top-k) | recurse into `next` (`minimize` = worst-case) | best *outcome*, not best immediate look |

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
│   └── scripts/          jev_client · jev_config · jev_meter · route_gate · check_output · warden
│                         · jev_ask · jev_tree · jev_search · jev_next
├── commands/             /jeveloper: setup · route · check · ask · tree · search · drive · stats
├── agents/               jev-adjudicator (batch typed verification)
└── examples/             loop-walkthrough · decision-tree · search
```

Zero dependencies — the scripts use only the Python standard library, so the hooks run with
no `pip install`.

## Status & caveats

Jev is new (public early access, Sept 2026). The request/response schema is pinned to
**OpenRouter's Decisions API** (`choice`/`score` use a `criteria` map; `choice`/`score`
responses return `probabilities`+`confidence`, chosen = argmax) and `jev_client.py` reads it
defensively. Set `OPENROUTER_API_KEY` (preferred) or `TYPESAFE_API_KEY`; until then
everything runs in safe MOCK mode. The thinking-token savings in driver mode are an estimate
until benchmarked with a real key (Jev's own spend *is* measured, from the API `usage`). See
[`skills/jeveloper/reference/jev-api.md`](skills/jeveloper/reference/jev-api.md).

## License

MIT — see [LICENSE](LICENSE).
