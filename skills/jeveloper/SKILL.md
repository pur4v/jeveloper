---
name: jeveloper
description: >-
  A System-1 reflex layer for Claude Code, powered by TypeSafe AI's Jev. Jev makes fast,
  cheap, typed decisions inside the agent loop so Claude reasons less and moves more
  reliably. Use when you want an automatic guardrail on tool calls, an automatic check on
  tool output, or an automatic "are we actually done?" judge that keeps the loop honest —
  or when you want to hand a one-off routing/verification decision to a fast model instead
  of spending Claude tokens on it. Triggers: "gate my tool calls", "verify this output",
  "did this actually pass", "keep going until it's really done", "route this to the right
  model", "should I run this command", "is the task complete", "ask Jev".
---

# jeveloper

Jev is a **System One** model — fast, intuitive, one-pass, typed. Claude is System Two —
deliberate and expensive. `jeveloper` wires Jev in as Claude's **reflexes**: cheap
(~$0.042/M input tokens, output free) and quick (~70–500ms) typed judgements that fire
automatically in the agent loop, so the slow, expensive reasoner spends its effort on the
work instead of on second-guessing itself.

**The one idea: Jev is a judge.** Every capability here is the same move — hand Jev
something and ask it to judge it, then act on the verdict. The three reflexes each put one
artifact in front of the judge at a fixed point in the loop:

- **Route** (`PreToolUse`) — Jev judges the *proposed tool call* → allow / ask / deny.
- **Check** (`PostToolUse`) — Jev judges the *tool's output* → passed, or feed the concern back.
- **Warden** (`Stop`) — Jev judges *whether the task is done* → stop, or keep going.

The tree and the search are that same judge scaled up: the **tree** judges many composed
conditions and reduces them; **search** judges candidate options and looks ahead. Keep "Jev
is the judge" in mind and the whole plugin is one pattern.

Jev never generates prose. You give it **state** (text/JSON) and **typed questions**; it
returns **typed probabilistic decisions**. Three question types cover everything here:

| Type | Ask… | Get back |
|---|---|---|
| **Noul** | a yes/no | `noul`: P(true), 0–1 |
| **Choice** | pick 1 of ≤255 | `choice` + per-option `probabilities` + `confidence` |
| **Score** | position on an ordered scale | `score` (may land between levels) + `confidence` |

## When to use this skill

Reach for jeveloper when the job is *"make a fast, structured judgement in the loop and
act on it"* — not open-ended reasoning (that's Claude's job) and not prose (Jev can't).
It earns its keep on the decisions Claude makes constantly and cheaply-ish today: *is this
command safe? did that test really pass? are we done?* Jev answers those ~100× cheaper and
faster, deterministically, with a confidence number you can threshold on.

Do **not** route genuinely open-ended reasoning, code authoring, or explanation through
Jev — it returns a decision, not a solution.

## The three reflexes

| Reflex | Hook | What Jev decides | Reference |
|---|---|---|---|
| **Route** | `PreToolUse` | Is this tool call destructive / out-of-scope? (gate) — plus on-demand model/approach routing via `/jeveloper:route` | `reference/mode-route.md` |
| **Check** | `PostToolUse` | Does this tool output actually indicate success and accomplish its intent? | `reference/mode-check.md` |
| **Warden** | `Stop` | Is the task genuinely complete and verified, or should the loop continue? | `reference/mode-warden.md` |

The reflexes run as hooks (`hooks/hooks.json`, wired to the scripts in `scripts/`). Read
the relevant mode file before tuning or explaining that reflex. See `reference/hooks.md`
for how the hooks are wired, the JSON contracts, and the config knobs.

## Composing decisions — the tree

A reflex asks Jev *one* thing at a fixed point. When a decision has **parts** — "safe to
auto-merge?" = tests-green AND low-risk AND scope-ok — express it as a **decision tree**:
fan out many Jev sub-decisions, branch on their answers, and **recursively reduce** the
leaves into one final call. Because Jev answers a whole level of questions in one parallel
request, each tree level is a single cheap call, so exploring multiple branches at once is
practically free. Run trees with `/jeveloper:tree` (or `scripts/jev_tree.py`); the trace
shows exactly which sub-decision swung the result. See `reference/mode-tree.md`.

## Choosing an option — search with lookahead

When the decision is *"which option do I pick?"* rather than *"do these conditions hold?"*,
search it: **Claude proposes** candidate options, **Jev judges** each (one batched, parallel
call), a **beam** keeps the strongest and prunes the rest, lookahead recurses into each
option's likely follow-on (`next`), and the node's `mode` — `maximize` / `minimize`
(worst-case) / `average` — backs the scores up so the recommended option is the one with the
best *outcome*, not the best immediate look. That last part is the payoff: it catches the
option that looks fine now but backs up badly. (If it helps: it's move-ordering + minimax
with Jev as the evaluation function — but nothing about it is game-specific.) Run with
`/jeveloper:search` (or `scripts/jev_search.py`). See `reference/mode-search.md`.

## Driver mode — Jev decides, Claude executes, Jev verifies

The reflexes/tree/search let Claude *consult* Jev. **Driver mode** (`/jeveloper:drive`) puts
Jev in the driver's seat to cut Claude's thinking-token cost: instead of deliberating what to
do, Claude cheaply **enumerates** 2–5 candidate next actions, `jev_next` (a `choice`) **picks
one**, Claude **executes** it, the Check hook **verifies** the output, and the loop repeats
until the Warden hook says the objective is met — a continuous ping-pong with Jev. Selecting
*which subagent* to spawn is just one such decision. Every decision is metered
(`/jeveloper:stats`) so the token saving is reported, not asserted — honestly, as an
*estimate*, and only on decision-heavy work (generation can't be offloaded; Jev decides, it
doesn't write). See `reference/mode-drive.md`.

## The disciplines (non-negotiable)

1. **Fail OPEN, always.** A reflex must never block the user because *jeveloper itself*
   is unsure or unavailable. Disabled, keyless (mock), Jev unreachable, an error, or a
   judgement below threshold → the hook exits 0 with no decision and the loop proceeds.
   A guardrail that breaks the workflow when it breaks is worse than no guardrail.

2. **Keyless is inert, not broken.** With no `TYPESAFE_API_KEY`, `jev_client.py` returns
   clearly-flagged MOCK answers and every reflex fails open. The plugin installs safe and
   does *nothing* until you both set a key and enable it (`/jeveloper:setup`).

3. **Act on confidence, not vibes.** Every gate/check/continue decision is a threshold on
   a Jev probability or score, configured in `.jeveloper.json`. No hidden heuristics.
   Surface the number in the reason string so the user sees *why* Jev intervened.

4. **The reflex is a signal, not a verdict.** When Check or Warden blocks, it hands Claude
   a concern to re-examine — Claude still decides. jeveloper narrows attention; it does not
   overrule the reasoner.

## Enabling it

Installing the plugin registers the hooks but leaves them **off** (`enabled: false`).
To turn jeveloper on for a project:

1. `export TYPESAFE_API_KEY=...` (from console.typesafe.ai/settings/keys).
2. Run `/jeveloper:setup` — it writes `.jeveloper.json` (thresholds + master switch),
   confirms the key resolves, and shows a live mock/real probe.

Tune `.jeveloper.json` per project: which tools Route gates, the Check fail threshold, the
Warden `done_threshold` and `max_continues`, and an optional standing `goal` the Warden
judges completeness against. Full schema in `reference/hooks.md`.

## On-demand decisions (no hook needed)

Beyond the automatic reflexes, hand Jev a single decision with:

- `/jeveloper:route` — Jev picks among options you give it (models, subagents, approaches).
- `/jeveloper:check` — Jev verifies a specific output or claim you paste in.
- `/jeveloper:ask` — pose any raw typed question (noul/choice/score).
- `/jeveloper:tree` — compose many sub-decisions into one, branched and recursively reduced.
- `/jeveloper:search` — search candidate *options* with Jev as the judge (beam + lookahead).
- `/jeveloper:drive` — run the Jev-driven loop (Jev decides → execute → Jev verifies → repeat).
- `/jeveloper:stats` — decisions offloaded to Jev + estimated thinking-tokens saved.

All three shell out to `scripts/jev_ask.py`, which prints the typed answer (mock when
keyless). Use them when *you* want a fast structured call without spending Claude tokens
deliberating.

## Output principles

- Lead with the decision and the number: "Jev: unsafe p=0.91 → denied", not a paragraph.
- Name the reflex and the threshold it crossed, so the intervention is auditable.
- When mock/keyless, say so plainly — a mock answer is "no opinion", never a real 0.5.
- Never present a Jev probability as a fact. It is a fast estimate; Claude verifies.
