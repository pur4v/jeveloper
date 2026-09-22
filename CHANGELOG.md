# Changelog

All notable changes to jeveloper are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **OpenRouter provider** — `jev_client` now auto-detects the provider from the environment:
  `OPENROUTER_API_KEY` → OpenRouter Decisions API (`/api/alpha/decisions`, model
  `typesafe/jev-latest`), else `TYPESAFE_API_KEY` → TypeSafe native, else MOCK. Request/
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
