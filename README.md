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

### Why — and how it saves you money 💸

Claude's most expensive tokens are the ones it burns **deliberating** — *is this safe? did that
pass? which approach? are we done?* Those are cheap, structured, repeatable judgements — exactly
Jev's shape (~100× cheaper, ~100 ms, typed, never prose). jeveloper routes each of them to Jev so
Claude **reasons less and executes more**:

- **Offload the deciding.** Claude throws candidate paths; Jev scores each and hands back the
  best as a "DO NEXT" directive Claude just runs — instead of Claude spending reasoning tokens
  choosing (`jev_path` / `jev_next`).
- **Enforced, not optional.** The first action of each turn is blocked until Jev has actually
  been consulted, so the decision is genuinely offloaded — not skipped when Claude feels rushed.
- **Catch failures instantly** — a skipped-but-green test, a wrong edit, a buried error — so
  Claude never reasons on top of a broken state.
- **Stop when the work is truly done**, not on a hunch — no extra "just checking" turns.

Every Jev call is **metered**, so the saving is *reported* by `/jeveloper:stats`, not asserted.
It wins most on decision-heavy, well-scoped work; generation itself can't be offloaded (Jev
decides — it doesn't write code).

---

## Quickstart

```
/plugin marketplace add pur4v/jeveloper
/plugin install jeveloper
```

Install **prompts you for your OpenRouter API key** (get one at
[openrouter.ai/keys](https://openrouter.ai/keys)) and stores it securely in your OS keychain
— never in the repo or in `settings.json`. Then **restart Claude Code once** so the hooks
load (a plugin's hooks only register at startup).

> Prefer TypeSafe's native API, or driving the key from your shell? Export
> `OPENROUTER_API_KEY` (or `TYPESAFE_API_KEY`) instead of using the prompt — jeveloper reads
> either. Change the stored key later with `claude plugin configure jeveloper` +
> `/reload-plugins`.

**That's it.** With a key set, jeveloper runs the whole loop through Jev, automatically, on
every turn — no command, no config:

- **Jev decides** each next action — Claude throws candidate paths, Jev scores them and returns
  the best as a directive (`jev_path`); the turn's first action is **blocked until Jev is
  consulted**, so the deciding is really offloaded,
- **Jev gates** every tool call (can deny/ask on something destructive),
- **Jev verifies** every tool's output,
- **Jev holds the loop open** until the work is genuinely done, and
- **Jev fans out** — a "compare N approaches" prompt spawns one real subagent per approach (in
  the native subagent tree) and Jev adjudicates the winner.

Jev's own output is **colour-coded** (cyan `⟦Jev⟧`, yellow for mock, red for errors) so you can
tell Jev from Claude at a glance. No key found? Jev asks you for one and — with your permission —
stores it so it's live in every terminal (`/jeveloper:doctor` to check status).

- **See it work in one command:** `bash demo.sh` (or `/jeveloper:demo`)
- **What did it cost:** `/jeveloper:stats`

No key? Everything still runs, silently (MOCK mode) — nothing breaks. It's heavy by design
(a Jev call around every action); dial it back per project in `.jeveloper.json` (disable a
reflex, or narrow `route.tools`) if you want less.

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

## Deep reasoning mode 🧠

Driver mode above optimises for *thrift* — a fast reflex pick, minimal deliberation. When a
decision is hard, high-stakes, or ambiguous, flip it: **deep reasoning mode** trades tokens for
rigour. Instead of a one-shot `jev_path` pick, Claude reasons the problem through and Jev
evaluates the whole decision tree with **lookahead** — proposing candidate paths *and* their
likely follow-ons, scoring each level in one batched call, and backing the value up so the
chosen path is the best *outcome*, not the option that merely looks best right now.

- **One-off:** `/jeveloper:deep <the hard decision>`
- **Always-on for a project:** `"deep": {"enabled": true}` in `.jeveloper.json` (or `JEVELOPER_DEEP=1`)

Off by default — the fast, token-saving path stays the default; deep mode is the escape hatch
for the decisions that deserve it. Built on `/jeveloper:search` (beam + lookahead) and
`/jeveloper:tree` (composed sub-decisions).

## One idea: Jev is the judge

Every capability is the same move — put something in front of Jev and act on its verdict.
The reflexes each hand the judge one artifact at a fixed point in the loop; the tree and
search are that judge scaled up.

## The three reflexes

| Reflex | Hook | Jev decides | You get |
|---|---|---|---|
| 🛑 **Route** | `PreToolUse` (all tools) | is this call destructive / off-goal? | a fast **safety gate** that denies/asks before a risky tool runs — plus on-demand model routing via `/jeveloper:route` |
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
2. **Keyless is inert, not broken.** No Jev key (`OPENROUTER_API_KEY`/`TYPESAFE_API_KEY`) →
   MOCK answers → every reflex silent. Set a key and the whole loop (drive + route + check +
   warden) turns on automatically, on every turn — no command, no config.
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

## Configure (optional)

You don't need to configure anything — a key in the env is enough. When you *want* to tune,
drop a `.jeveloper.json` in the project root (all fields optional):

```json
{
  "goal": "the standing objective the Warden judges 'done' against",
  "provider": { "use": "auto" },          // auto | openrouter | direct
  "drive":  { "enabled": true },          // Jev decides every action (set false to stop driving)
  "route":  { "enabled": true, "tools": [] },  // gate every tool; narrow tools, or false to disable
  "check":  { "enabled": true, "fail_threshold": 0.80 },
  "warden": { "enabled": true, "done_threshold": 7.0, "max_continues": 3 }
}
```

All four run by default with a key. Set any to `false` (or narrow `route.tools`) to dial it
back — this is a lot of Jev calls by design.

The key always stays in the **environment** (`OPENROUTER_API_KEY` / `TYPESAFE_API_KEY`),
never in this file. Provider auto-detects (OpenRouter if its key is set, else TypeSafe);
force one with `provider.use` or `JEVELOPER_PROVIDER`. Full schema:
[`skills/jeveloper/reference/hooks.md`](skills/jeveloper/reference/hooks.md). `/jeveloper:setup`
can write this for you, but it's optional.

## On-demand (no hooks needed)

| Command | Does |
|---|---|
| `/jeveloper:route` | Jev picks among options (models, subagents, approaches) |
| `/jeveloper:check` | Jev verifies an output/claim you paste in |
| `/jeveloper:ask` | any raw typed question — `noul` / `choice` / `score` |
| `/jeveloper:tree` | compose many sub-decisions into one — branched + recursively reduced |
| `/jeveloper:search` | search candidate *options* with Jev as the judge — beam + lookahead |
| `/jeveloper:path` | throw candidate paths → Jev scores each → best returned as a "DO NEXT" directive |
| `/jeveloper:fanout` | spawn one real subagent per approach (native tree) → Jev adjudicates the winner |
| `/jeveloper:drive` | run the Jev-driven loop — Jev decides → you execute → Jev verifies → repeat |
| `/jeveloper:deep` | **deep reasoning** — think it through + Jev lookahead (search/tree) instead of a fast pick |
| `/jeveloper:doctor` | health check — live vs MOCK per reflex, with the exact fix for each problem |
| `/jeveloper:stats` | decisions offloaded to Jev + estimated thinking-tokens saved |
| `/jeveloper:demo` | run a few live Jev decisions and show the measured cost |

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
                        OPENROUTER_API_KEY / TYPESAFE_API_KEY?  no → MOCK → every reflex fails open
```

See a full fictional session in
[`examples/loop-walkthrough/`](examples/loop-walkthrough/README.md).

## What's in the box

```
jeveloper/
├── .claude-plugin/       plugin.json + marketplace.json
├── hooks/hooks.json      registers all four hooks (auto-on with a key: drive+route+check+warden)
├── skills/jeveloper/
│   ├── SKILL.md          the skill (reflexes + tree + search + drive)
│   ├── reference/        jev-api · hooks · mode-route · mode-check · mode-warden · mode-tree · mode-search · mode-drive
│   └── scripts/          jev_client · jev_config · jev_meter · drive_inject · route_gate · check_output · warden
│                         · jev_ask · jev_tree · jev_search · jev_next
├── commands/             /jeveloper: setup · route · check · ask · tree · search · drive · stats · demo
├── agents/               jev-adjudicator (batch typed verification)
├── demo.sh               one-command live demo
└── examples/             loop-walkthrough · decision-tree · search
```

Zero dependencies — the scripts use only the Python standard library, so the hooks run with
no `pip install`.

## Status & caveats

Jev is new (public early access, Sept 2026). The request/response schema is pinned to
**OpenRouter's Decisions API**, verified live: `choice`'s `criteria` is a **map** but
`score`'s is an **array**; `choice`/`score` responses return `probabilities`+`confidence`
(chosen = argmax) and `score` also a scalar `score`+`legend`. `jev_client.py` reads all of it
defensively. Set `OPENROUTER_API_KEY` (preferred) or `TYPESAFE_API_KEY`; until then
everything runs in safe MOCK mode. The thinking-token savings in driver mode are an estimate
until benchmarked with a real key (Jev's own spend *is* measured, from the API `usage`). See
[`skills/jeveloper/reference/jev-api.md`](skills/jeveloper/reference/jev-api.md).

## License

MIT — see [LICENSE](LICENSE).
