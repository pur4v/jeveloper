# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Instead, use GitHub's
[private vulnerability reporting](https://github.com/pur4v/jeveloper/security/advisories/new)
on this repository, or contact the maintainer at https://github.com/pur4v. You'll get an
acknowledgement within a few days and a fix or mitigation timeline after triage.

## Security model — what jeveloper does and doesn't do

jeveloper runs as Claude Code **hooks** and shells out to a third-party API (TypeSafe AI's
Jev). Keep these properties in mind:

- **Your key.** `TYPESAFE_API_KEY` is read from the environment and sent only to the Jev
  endpoint (`JEVELOPER_API_URL`, default `https://api.typesafe.ai/v1/systemone`) as a Bearer
  header. It is never written to disk by this plugin, never logged, and never placed in a
  URL. `.jeveloper.json` holds only thresholds — never the key. `.gitignore` excludes
  `.env`, `*.key`, and `.jeveloper.json`.

- **What leaves your machine.** When a reflex is enabled and a key is set, the relevant
  **state is sent to Jev**: tool commands + a truncated slice of tool output (Check), the
  tool input + project goal (Route), and a truncated slice of your **transcript** (Warden).
  If your commands or output contain secrets or sensitive data, that data is transmitted to
  TypeSafe. Treat the Jev endpoint like any other cloud API in your threat model. Disable
  the relevant reflex (or jeveloper entirely) in repos where that is unacceptable.

- **Fail-open is intentional.** Every reflex exits 0 (no opinion) on error, timeout, missing
  key, or low confidence. This means jeveloper **will not block** a dangerous action it was
  simply unsure about or couldn't reach Jev to evaluate. It is a best-effort assistant, **not
  a security control** — do not rely on the Route gate as your only defense against
  destructive commands.

- **Advisory, not authoritative.** Jev returns probabilities. Check/Warden feedback is a
  prompt for Claude to re-examine, not a hard guarantee of correctness or completion.

- **Never gate on secrets you don't want sent.** If you enable the Route gate on tools whose
  inputs embed credentials, those inputs are sent to Jev for judgement.

## Supported versions

Only the latest `0.x` release receives fixes while the project is pre-1.0.
