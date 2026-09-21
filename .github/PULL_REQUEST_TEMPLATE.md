<!-- Thanks for contributing to jeveloper! Keep it small and fail-open. -->

## What & why

<!-- One or two sentences: what does this change and why. -->

## Checklist

- [ ] Fails **open** on every new path (disabled, keyless/mock, network error, timeout, below-threshold)
- [ ] No new third-party imports in the hook path (stdlib only)
- [ ] Keyless MOCK behavior preserved (`jev_client.ask()` returns `mock=true` with no key)
- [ ] Any Jev wire-schema change is isolated to `jev_client.py`
- [ ] New interventions are a documented threshold surfaced in the reason string
- [ ] Updated the relevant `reference/mode-*.md` if a reflex changed
- [ ] Updated `CHANGELOG.md` under `[Unreleased]`
- [ ] `python3 -m py_compile skills/jeveloper/scripts/*.py` passes; keyless smoke test passes
- [ ] No secrets in the diff; commit history is clean (no attribution trailers, no merge commits)

## Fail-open behavior of anything new

<!-- Describe how a new reflex/path behaves when Jev is unsure or unreachable. -->
