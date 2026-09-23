---
description: Health-check jeveloper — is it actually live in this session? Shows per-reflex live/MOCK and the exact fix for anything broken.
---

Run the jeveloper health check and report the result plainly:

```bash
python3 skills/jeveloper/scripts/jev_doctor.py
```

Then summarise for the user: is jeveloper **LIVE** (real Jev) or **MOCK/off**, which reflexes
are on, and — if any line is red (✗) — the single most important fix, stated first. If the
verdict is "NOT live", lead with that and the one action that fixes it.
