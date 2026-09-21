# Check — the PostToolUse reflex

## What it does

After a matched tool returns, `check_output.py` hands Jev the tool call **and** its output
and asks two `noul` questions:

- `is_failure` — the output indicates a real failure: an error, a non-zero exit, a
  traceback, a rejected edit, or a test that **errored/was skipped rather than genuinely
  passing**.
- `misses_intent` — the result does not accomplish what the call was evidently trying to do.

`worst = max(is_failure, misses_intent)`. If `worst ≥ fail_threshold` (default 0.80), the
hook returns blocking PostToolUse feedback so Claude re-examines the result *now*, before it
builds on a bad foundation:

```json
{"decision": "block",
 "reason": "jeveloper (Jev check) flagged this tool result: the output looks like a failure (p=0.88)…"}
```

Below threshold → exit 0, silent.

## Why it's worth a call on every result

The classic agent failure is confident-but-wrong reading of output: a test suite that
prints green while silently skipping the one test that mattered, an `Edit` that "succeeded"
but changed the wrong block, a command whose real error is buried under noise. Claude
usually catches these — but not always, and a missed one compounds. A ~$0.00004, ~100 ms
check on every result is cheap insurance, and Jev's typed yes/no is exactly the shape of
"did this actually work?"

## Tuning

`.jeveloper.json → check`:

```json
{"check": {"enabled": true, "fail_threshold": 0.80}}
```

- Raise `fail_threshold` toward 0.9 if Check interrupts too eagerly; lower it in a
  correctness-critical repo where you want more scrutiny.
- The matched tools are set in `hooks/hooks.json` (default `Bash|Edit|Write|MultiEdit|Task`).
  Trim `Task` if you don't want subagent results re-judged.

## Guardrails

- Tool input and output are **truncated** (`MAX_CHARS`) to stay well under Jev's context
  budget — a huge log won't blow the request.
- `decision: block` on PostToolUse surfaces the reason to Claude as context; it does not
  undo the tool call (the side effect already happened). Check is about catching the
  problem immediately, not preventing the write.

## Fail-open cases

check disabled · keyless/mock · Jev error · both probabilities below `fail_threshold`.
