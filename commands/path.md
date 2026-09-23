---
description: Throw several candidate paths at Jev, get each scored, and act on the best — Jev's output is the marching order.
argument-hint: "<the state/decision> and the candidate paths to weigh"
---

Decide the next move by **scoring candidate paths with Jev, then executing the best**: $ARGUMENTS

The split: **you throw the situations, Jev scores them, you execute the best path.**

1. **Throw 2–6 candidate paths.** From the current state, propose the distinct situations/moves
   you could take next. Don't pre-judge them — that's Jev's job.

2. **Score + pick with Jev** (one batched call scores every path):

   ```bash
   python3 skills/jeveloper/scripts/jev_path.py "<state>" "<objective>" s1:"path 1" s2:"path 2" ...
   ```

3. **Execute the `directive`.** Jev returns per-path `scores` (0..1), the `ranking`, the `best`,
   and a `directive` ("DO NEXT → …"). Do exactly that as your next action; the Check hook then
   verifies. Do not re-deliberate the lower-scored paths.

4. `mock` true (no key) → scores are 0.5 placeholders; the shape is valid but not a real
   judgement, so decide yourself and say so.
