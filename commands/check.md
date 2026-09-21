---
description: Ask Jev to verify a specific output or claim — did this actually pass / accomplish its intent?
argument-hint: "<the output, result, or claim to verify>"
---

Use **Jev** to verify this output/claim: $ARGUMENTS

1. Take the pasted output/result/claim as the **state**. If the argument is a reference
   rather than the content (e.g. "the last test run"), gather the actual output first.

2. Ask Jev the verification question(s) with a Noul via the CLI:

   ```bash
   python3 skills/jeveloper/scripts/jev_ask.py noul "<the output/claim>" \
     "This genuinely succeeded / is true (not skipped, empty, errored, or merely attempted)"
   ```

   For a richer check, run a second Noul for "does not accomplish its stated intent".

3. Report the `noul` probability plainly: e.g. "Jev: genuinely-passed p=0.34 → suspicious".
   `"mock": true` means no key, so it's a placeholder, not a verdict.

4. **Jev flags; you verify.** If Jev is doubtful, actually inspect the output and confirm
   before trusting it — the probability narrows attention, it doesn't replace looking.

Read `skills/jeveloper/reference/mode-check.md` for what Check looks for.
