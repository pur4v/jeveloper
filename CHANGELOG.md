# Changelog

All notable changes to jeveloper are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Install-time key prompt.** `plugin.json` now declares an `openrouter_api_key`
  `userConfig` field (sensitive, required), so `/plugin install jeveloper` asks for the key
  and stores it in the OS keychain — no shell export, no hand-edited `settings.json`, and it
  reaches the hooks reliably instead of depending on the launching shell's environment.
  `jev_client` and `jev_config` read the key from either the plain env var
  (`OPENROUTER_API_KEY` / `TYPESAFE_API_KEY`, still supported) or the plugin-config form
  Claude Code injects (`CLAUDE_PLUGIN_OPTION_<NAME>`), via a new `_env_key` helper. README
  quickstart updated to the prompt-based flow and the one-time restart it requires.

### Changed
- **Everything on, for every action.** With a Jev key set, jeveloper now runs the whole loop
  automatically on every turn — matching the original spec (Jev is the *first* call for
  action selection, verifies output, works the loop):
  - **drive** — a new `UserPromptSubmit` hook (`drive_inject.py`) injects a standing
    "defer to Jev" instruction each turn, so Claude enumerates options and lets `jev_next`
    pick, with no `/jeveloper:drive` command needed.
  - **route** — now **on by default** and gates **every** tool call (`hooks.json` matcher
    `*`, `route.tools: []`), not just Bash/Edit.
  - **check** / **warden** — verify every output / hold the loop open, as before.
  Master switch stays `"auto"` (on when a key is present). This is heavy by design — a Jev
  call around every action; disable any of `drive`/`route`/`check`/`warden` or narrow
  `route.tools` in `.jeveloper.json` to dial it back.

### Fixed
- **Key bridge: `jev_path`/`jev_next`/`jev_ask` are now live, not mock.** Claude Code injects the
  plugin key only into **hook** processes (`CLAUDE_PLUGIN_OPTION_<NAME>`), never into the **Bash**
  shell where Claude runs the Jev CLIs — so they always came back mock ("no API key") even with a
  key configured, and Jev never actually scored. The UserPromptSubmit hook (which has the key)
  now caches it to `~/.config/claude/.jeveloper-key` (0600, in the user config dir — never the
  project, so it can't be committed), and `jev_client` reads that as a fallback. Works in every
  terminal automatically, since the hook refreshes it each turn — no `export` needed.

### Added
- **Colour-coded Jev output (`jev_color.py`).** Jev's lines are now cyan and tagged `⟦Jev⟧`,
  mock/advisory is yellow, and errors are red — so a user can tell Jev's output from Claude's
  prose (default colour) and from errors at a glance. The CLIs print a coloured `⟦Jev⟧` banner
  to **stderr** while keeping **stdout clean JSON** (still parseable); `jev_doctor` is fully
  colourised. Honours `NO_COLOR` / `JEVELOPER_NO_COLOR`.
- **Human-in-the-loop key fallback (`jev_setkey.py`).** If Jev still can't find a key (mock),
  the driver asks the user to paste their OpenRouter/TypeSafe key and — only with explicit
  permission — stores it via `jev_setkey.py`, making Jev live in this and every future terminal.
- **`jev_path` — Jev's output is the marching order.** At each state Claude throws 2–6 candidate
  situations/paths; Jev **scores every one in a single batched call**; `jev_path` ranks them,
  picks the `best`, and emits a `directive` ("DO NEXT → …") that Claude executes without
  re-deliberating. Output is `{scores (0..1), ranking, best, directive, confidence, mock}`. The
  always-on driver and the Jev-first gate now point here (throw paths → score → best →
  directive → act), and `/jeveloper:path` invokes it explicitly. `jev_next` gains a matching
  `directive` field for simple either/or picks. This is the "state → structured scored options →
  best path drives the next action" loop.

### Fixed
- **Warden no longer loops on non-task objectives.** The Stop hook took the latest user turn
  as the objective and blocked the stop whenever Jev judged it incomplete — misfiring three
  ways with no real work to do: a bare greeting ("hi"); a tool-only user turn that `_flatten`
  renders as `(tool_result)`; and the warden's own feedback, which lands in the transcript as
  a user turn, so each pass re-ingested the previous block as the new objective — a runaway
  that only released at `max_continues`. The warden now fails open when the objective is
  trivial (greeting, two-word remark), a synthetic placeholder (tool-only turn, image-only
  turn, or the no-goal fallback), or its own feedback text, and no longer treats a
  placeholder-only turn as the user's request. It guards real work only, and only when no explicit `goal` is configured.
- **Warden ignores system-injected turns.** Task notifications (subagent results), system
  reminders, and its own Stop-hook feedback all land in the transcript as `user` turns, so the
  warden could latch onto one — e.g. a returned capability table — as the objective and block
  the stop. It now skips any turn carrying an injection marker (`<system-reminder>`,
  `<task-notification>`, `<tool-use-id>`, `</note>`, `Stop hook feedback:`) when choosing the
  objective, and treats such content as trivial if it ever slips through.
- **Warden no longer blocks answered questions.** For a pure question objective (ends with
  "?"), the "completeness of the work shown" model doesn't fit — there is no work to grade,
  just the assistant's answer, so Jev scores it low and the warden held the stop. The warden
  now releases any question objective unconditionally; it exists to catch unfinished *work*,
  and a question is answered in the reply, not verified in the transcript.
- **Warden: gate on completeness alone.** The stop was gated on completeness AND a `met`
  "everything verified in recent activity" check, but `met` reads systematically low for
  text/advice turns that have nothing to verify — repeatedly holding finished work. The `met`
  hard-veto is dropped: the stop is allowed once completeness ≥ `done_threshold`. Completeness
  already encodes verification (top rung is "done AND verified"), so genuinely unfinished work
  scores below the threshold and is still held; `met` now only colours the reason line.

### Added
- **Jev-first gate (enforced offloading).** To actually offload deliberation to Jev instead of
  relying on Claude to volunteer, the PreToolUse gate now **blocks the first substantive action
  of each turn** — `Edit`, `Write`, `MultiEdit`, `NotebookEdit`, `Bash`, and `Task` by default —
  until Jev has been consulted (`jev_next`/`jev_ask` has run this turn). Claude sees the deny
  reason, runs `jev_next` to pick the action, then retries; no user prompt, no explicit command.
  Read-only tools (Read/Grep/Glob) are never gated, and the `jev_next`/`jev_ask` consult command
  itself is exempt so it can't deadlock its own gate. The per-turn marker lives under
  `<project>/.jeveloper/consult.turn` (cwd-based, like the metrics log — NOT the temp dir, since
  the Bash sandbox and hook processes see different TMPDIRs) and is re-armed each turn by the
  UserPromptSubmit hook. Enforced only while `drive` is on; tune with `route.consult_first`
  (default true) and `route.consult_tools`. Costs no extra Jev call itself.
- **Fan-out mode (`/jeveloper:fanout`).** Explore several directions for the *same* task by
  spawning one **real subagent per branch** — so Claude Code's native subagent tree shows them
  running in parallel — then let **Jev adjudicate** the returned outcomes and pick the winner.
  Complements the Jev-only `search`/`tree` (which score text options without executing them);
  fan-out actually runs each branch. Real subagents = real tokens, so it's for genuinely
  divergent directions worth the cost.
- **Zero-command by default.** The always-on driver now triggers fan-out and self-diagnosis on
  its own — no need to type `/jeveloper:fanout` or `/jeveloper:doctor`. The `UserPromptSubmit`
  hook detects compare/explore/"several approaches" prompts and injects a mandatory
  **"FAN OUT REQUIRED"** directive for them (a hook can't spawn subagents itself, so this is the
  strongest automatic lever), so the parallel-subagent behaviour fires without the user asking.
  The doctor runs when Jev's own decisions keep coming back mock/inert. The commands remain for
  explicit use.
- **Health check (`/jeveloper:doctor`, `jev_doctor.py`).** One shot: master switch, key
  detection, a real live probe, each reflex's on/off + live/MOCK state, config-file validity,
  and hook registration — with the exact fix for every red line. Targets jeveloper's biggest
  hazard: a mistyped key or unregistered hook silently making the whole plugin do nothing.
- **Live Jev status spinners.** Each Jev hook now sets `statusMessage`, so Claude Code shows a
  labelled spinner while the call runs — `⚡ Jev checking this action…` (route),
  `⚡ Jev verifying the result…` (check), `⚡ Jev judging if the task is done…` (warden) — making
  Jev's inline latency visible instead of a silent pause. Takes effect after a session reload,
  since hook registration is read once at startup. (An inline end-of-turn *summary* line isn't
  possible: a `Stop` hook has no user-visible message channel; only `terminalSequence`
  bell/notification is available there.)
- **Per-kind Jev meter.** The route, check, and warden hooks now tag their Jev calls with a
  `kind` (`route`/`check`/`warden`) instead of the default `ask`, so the meter and
  `/jeveloper:stats` break down calls, decisions, live calls, and real spend **per kind**
  rather than lumping everything together.
- **`demo.sh` / `/jeveloper:demo`** — run a few real Jev decisions (skipped-test check, model
  routing, next-action pick, an auto-merge tree) and print the measured cost, in one command.
- **Selectable provider** — users can add **OpenRouter** or **direct** (TypeSafe native), by
  config or env. `.jeveloper.json` gains a `provider` block (`use: auto|openrouter|direct`,
  optional `model`/`api_url`/`api_key_env`); `JEVELOPER_PROVIDER` overrides it; `/jeveloper:setup`
  records the choice + env-var name (never the key). An explicit choice never silently falls
  back to the other provider. `jev_client` auto-detects when `use: auto`:
  `OPENROUTER_API_KEY` → OpenRouter Decisions API (`/api/alpha/decisions`, model
  `~typesafe/jev-latest`), else `TYPESAFE_API_KEY` → TypeSafe native, else MOCK. Request/
  response schema pinned to OpenRouter's confirmed shape (`criteria` map for `choice`/
  `score`; responses carry `probabilities`+`confidence`, chosen = argmax), read defensively
  via `choice_of`/`score_of`/`noul_of`. Real `usage.cost`/`input_tokens` are captured and
  reported by the meter as measured Jev spend.
- **Driver mode** (`/jeveloper:drive`, `skills/jeveloper/scripts/jev_next.py`) — puts Jev in
  the driver's seat to cut Claude's thinking-token cost: Claude cheaply enumerates candidate
  next actions, `jev_next` (a `choice`) picks one, Claude executes it, the Check hook
  verifies the output, and the loop repeats until the Warden is satisfied — a continuous
  ping-pong. Subagent selection is just a `jev_next` decision. See `reference/mode-drive.md`.
- **Decision meter** (`skills/jeveloper/scripts/jev_meter.py`, `/jeveloper:stats`) — every
  Jev call is recorded (`kind`, decisions, live/mock) to `.jeveloper/metrics.jsonl`, and the
  report estimates thinking-tokens saved (`live_decisions × JEVELOPER_TOKENS_PER_DECISION`,
  default 500), clearly labelled an estimate; mock calls offloaded nothing and are excluded.
  `jev_client.ask()` now takes a `kind` tag and meters every call best-effort.
- **Option search / Jev-as-evaluator** (`skills/jeveloper/scripts/jev_search.py`,
  `/jeveloper:search`) — Claude proposes candidate options, Jev judges each in one batched
  parallel call, a **beam** keeps the top-k, lookahead recurses into each option's `next`,
  and the node's `mode` (`maximize`/`minimize`/`average`) backs the scores up so the
  recommended option has the best *outcome*, not just the best immediate look. Hard-capped at
  `MAX_CALLS=64` per search. Ships with `reference/mode-search.md` and a worked
  `examples/search/` (a flaky-test fix where a worst-case lookahead flips the greedy choice).
  Domain-neutral vocabulary — the game-engine framing is only an analogy in the docs.
- **"Jev is the judge"** framing threaded through the skill and README: the three reflexes,
  the tree, and the search are all one pattern — hand Jev an artifact, act on its verdict.
- **Decision trees** (`skills/jeveloper/scripts/jev_tree.py`, `/jeveloper:tree`) — compose
  many Jev sub-decisions into one: fan out questions, branch on the answers (`noul`
  true/false with an uncertain-`band`, `choice` by option with a `margin`, `score` by
  level), and **recursively reduce** the leaves via `and`/`or`/`mean`/`max`/`min`/`argmax`/
  `first`. Each tree level is one batched (parallel) Jev call, so exploring multiple
  branches at once stays cheap. Ships with `reference/mode-tree.md` and a worked spec +
  expected traces in `examples/decision-tree/`.

## [0.1.0] — 2026-09-21

First public release.

### Added
- **The jeveloper skill** (`skills/jeveloper/`) — a System-1 reflex layer that wires
  TypeSafe AI's **Jev** into the Claude Code agent loop, with three reflexes and four
  disciplines (fail-open, keyless-is-inert, act-on-confidence, signal-not-verdict).
- **Three reflexes**, wired as hooks in `hooks/hooks.json`:
  - **Route** (`PreToolUse`, `route_gate.py`) — Jev safety-gates destructive/out-of-scope
    tool calls (deny/ask on a confidence threshold).
  - **Check** (`PostToolUse`, `check_output.py`) — Jev verifies tool output and feeds real
    failures / missed intent back to Claude.
  - **Warden** (`Stop`, `warden.py`) — Jev judges task completeness and re-opens the loop
    until the work is genuinely done, with a per-session `max_continues` cap.
- **Zero-dependency Jev client** (`jev_client.py`) — stdlib-only `POST /v1/systemone` with
  `noul`/`choice`/`score` builders and a keyless MOCK path so hooks fail open.
- **Config** (`jev_config.py`, `.jeveloper.json`) — master switch (ships OFF), per-reflex
  toggles, thresholds, and an optional standing `goal`.
- **Progressive-disclosure reference docs** (`skills/jeveloper/reference/`): `jev-api`,
  `mode-route`, `mode-check`, `mode-warden`, `hooks`.
- **Slash commands**: `/jeveloper:setup`, `/jeveloper:route`, `/jeveloper:check`,
  `/jeveloper:ask` (on-demand typed decisions via `jev_ask.py`).
- **Sub-agent**: `jev-adjudicator` (batched typed verification).
- **Plugin packaging**: `.claude-plugin/plugin.json` + `marketplace.json`
  (`/plugin marketplace add pur4v/jeveloper`).
- **Fictional worked example** under `examples/loop-walkthrough/`.
- Project docs: `README`, `SECURITY`, `CONTRIBUTING`, `CODE_OF_CONDUCT`, and CI.

### Known limitations
- Jev's `choice`/`score` request field names followed public examples and were not yet
  confirmed against provider docs (isolated in `jev_client.py`). *Resolved in Unreleased:
  pinned to OpenRouter's Decisions API (`criteria` map; argmax `choice`).*

[Unreleased]: https://github.com/pur4v/jeveloper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pur4v/jeveloper/releases/tag/v0.1.0
