---
description: Pose any raw typed question to Jev — noul (yes/no), choice (pick one), or score (ordered scale).
argument-hint: "<noul|choice|score> then the state and instructions"
---

Pose a typed question directly to **Jev**: $ARGUMENTS

Pick the question type that fits and call the CLI:

```bash
# yes/no  -> answer.noul is P(true), 0..1
python3 skills/jeveloper/scripts/jev_ask.py noul "<state>" "<statement to judge>"

# pick one -> answer.choice + per-option probabilities + confidence
python3 skills/jeveloper/scripts/jev_ask.py choice "<state>" "<the question>" \
  value1:desc value2:desc value3:desc

# ordered scale -> answer.score (continuous), lowest level first
python3 skills/jeveloper/scripts/jev_ask.py score "<state>" "<what to rate>" \
  "lowest level" "middle level" "highest level"
```

Report the typed answer as-is. If `"mock": true`, note that `TYPESAFE_API_KEY` is unset so
the answer is a neutral placeholder, not a real Jev judgement.

`state` can be plain text or JSON, up to ~64k tokens combined with the question. See
`skills/jeveloper/reference/jev-api.md` for the primitives and limits.
