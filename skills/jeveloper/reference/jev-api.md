# Jev API reference (as used by jeveloper)

Jev is TypeSafe AI's first **System One** model: a non-autoregressive model that returns
typed probabilistic decisions in one pass instead of generating text token by token. This
file is the ground truth for how `jev_client.py` talks to it.

## Endpoint & auth

- `POST https://api.typesafe.ai/v1/systemone`
- Header: `Authorization: Bearer $TYPESAFE_API_KEY` (key from
  https://console.typesafe.ai/settings/keys)
- Official SDKs exist (`pip install typesafe-sdk`, `npm i @typesafe-ai/sdk`), but jeveloper
  deliberately uses **stdlib `urllib` only** so the hooks run with no install step.

Override for testing via env: `JEVELOPER_API_URL`, `JEVELOPER_MODEL` (default `jev-latest`),
`JEVELOPER_TIMEOUT` (seconds, default 5).

## Request shape

```json
{
  "model": "jev-latest",
  "state": "…text… or a JSON object/array of text (no images/audio/video)",
  "questions": {
    "is_urgent": { "type": "noul", "instructions": "The message conveys urgency" }
  }
}
```

`state` may be a string, a JSON object, or an array of strings. Questions are evaluated
**in parallel** in a single request — batch several rather than making N calls.

## Question types

| Type | Purpose | Extra fields | Answer fields |
|---|---|---|---|
| `noul` | yes/no truth judgement | — | `noul` (0–1) |
| `choice` | pick 1 of up to 255 options | option set | `choice`, `probabilities`, `confidence` |
| `score` | position on a 2–10 level ordered scale | ordered `criteria` | `score` (continuous), `confidence` |

## Response shape

```json
{
  "answers": {
    "is_urgent": { "type": "noul", "noul": 0.999 }
  }
}
```

`jev_client.py` reads `answers`, and tolerates a flat top-level object as a fallback.

## Limits & economics (why this is loop-safe)

- **Latency:** ~70–500 ms per request.
- **Context:** ~64k tokens combined (state + all questions).
- **Choice:** up to 255 options.
- **Pricing:** ~$0.042 per **million** input tokens; **output free**.
- **Rate:** ~250k tokens/s, ~1,200 req/min.

At that price a Check on every tool result or a Warden on every stop is effectively free,
which is the whole reason jeveloper can afford to run in the hot loop.

## ⚠️ Wire-schema caveat

TypeSafe's public writeups pin down `noul` (`{"type","instructions"}` → `{"noul":…}`) and
the response envelope, but the exact request field name for **choice options** and
**score criteria** is not fully documented publicly. `jev_client.py` keeps all request
construction in `_question_wire()` / the builder functions so there is exactly one place to
correct once you have a key and the console docs. Until then the keyless MOCK path runs and
nothing depends on the unverified fields.

Sources: TypeSafe AI announcements and third-party guides (heise, DataCamp, MindStudio,
LangChain, DEV) — September 2026. Verify against the console before trusting live numbers.
