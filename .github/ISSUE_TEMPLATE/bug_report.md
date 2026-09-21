---
name: Bug report
about: A reflex misbehaved, a hook errored, or something didn't fail open
title: "[bug] "
labels: bug
---

**What happened**
<!-- Which reflex (Route / Check / Warden / a command)? What did it do? -->

**What you expected**
<!-- Especially: did it fail to fail-open? A hook should never block/hang/crash the loop. -->

**Repro**
1.
2.

Include the hook input if you have it, and run with `JEVELOPER_DEBUG=1` for the fail-open reason:

```bash
printf '<the hook JSON>' | JEVELOPER_ENABLED=1 JEVELOPER_DEBUG=1 python3 skills/jeveloper/scripts/<script>.py; echo "exit=$?"
```

**Environment**
- jeveloper version:
- Mode: live (key set) / mock (keyless)
- `.jeveloper.json` (redact nothing sensitive — it holds only thresholds):
- OS / Python version:

**Anything else**
<!-- Was a real key set? Was Jev reachable? Relevant `.jeveloper.json` thresholds? -->
