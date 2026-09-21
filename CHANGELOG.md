# Changelog

All notable changes to jeveloper are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- Jev's request field names for `choice`/`score` options follow public examples and are not
  yet confirmed against the console docs; they are isolated in `jev_client.py` for a
  one-line fix. The default keyless MOCK path does not depend on them.

[Unreleased]: https://github.com/pur4v/jeveloper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pur4v/jeveloper/releases/tag/v0.1.0
