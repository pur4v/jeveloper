# Jev API reference (as used by jeveloper)

Jev is TypeSafe AI's first **System One** model: a non-autoregressive model that returns
typed probabilistic decisions in one pass instead of generating text token by token. This
file is the ground truth for how `jev_client.py` talks to it.

## Providers (auto-detected from the key that's set)

`jev_client._resolve()` picks the provider from the environment — **OpenRouter wins if both
keys are present**:

| Provider | Endpoint | Auth env | Default model |
|---|---|---|---|
| **OpenRouter** | `POST https://openrouter.ai/api/alpha/decisions` | `OPENROUTER_API_KEY` | `typesafe/jev-latest` |
| **TypeSafe native** | `POST https://api.typesafe.ai/v1/systemone` | `TYPESAFE_API_KEY` | `jev-latest` |

Override either with `JEVELOPER_API_URL` / `JEVELOPER_MODEL`. Header on both:
`Authorization: Bearer <key>`, `Content-Type: application/json`. No SDK — stdlib `urllib`
only, so the hooks need no install.

## Request

```json
{
  "model": "typesafe/jev-1.13",
  "state": { "message": "My invoice lists two seats…", "plan": "team" },
  "questions": {
    "queue": {
      "type": "choice",
      "instructions": "Which team should handle this message?",
      "criteria": {
        "billing": "Charges, invoices, refunds, seats on the bill",
        "technical": "Bugs, outages, login problems, integrations",
        "other": "Anything else"
      }
    },
    "angry": { "type": "noul", "instructions": "Is the customer angry?" }
  }
}
```

`state` may be a string or a JSON object/array of text (no images/audio/video). Questions
are evaluated **in parallel** in one request — batch several rather than making N calls.

## Question types

| Type | Purpose | Request field | 
|---|---|---|
| `noul` | yes/no truth judgement | — |
| `choice` | pick 1 of up to 255 | `criteria`: `{option: description}` |
| `score` | position on an ordered scale | `criteria`: `{level: description}`, low→high |

> The field is **`criteria`** (a map) for both `choice` and `score` — *not* `options`, and
> not a list. `jev_client.choice()/score()` build this for you; a list passed to `score()`
> is turned into an ordered `{level: level}` map.

## Response

```json
{
  "answers": {
    "queue": { "type": "choice", "probabilities": { "billing": 0.9, ... }, "confidence": 0.95 },
    "angry": { "type": "noul",   "noul": 0.88 }
  },
  "id": "gen-dec-…",
  "model": "typesafe/jev-1.13-20260917",
  "provider": "TypeSafe",
  "usage": { "input_tokens": 476, "output_tokens": 0, "cost": 0.000019992 }
}
```

- **noul** → `noul` = P(true). (Some responses instead carry `probabilities` with true/false
  keys; `noul_of()` handles both.)
- **choice** → `probabilities` per option + `confidence`. **There is no `choice` field** —
  the chosen option is the argmax; `choice_of()` computes it.
- **score** → `probabilities` over the levels + a `legend` + `confidence`; `score_of()`
  returns the expected level index (callers normalize to 0..1).
- **usage** → real `input_tokens` and `cost`. `jev_meter` records these as measured Jev spend.

## Limits & economics (why this is loop-safe)

- **Latency:** ~70–500 ms per request.
- **Context:** ~32k tokens (OpenRouter `jev-1.13`) to ~64k (native).
- **Pricing:** ~$0.042 per **million** input tokens; **output free**.

At that price a Check on every tool result or a `jev_next` on every step is effectively
free — the whole reason jeveloper can run Jev in the hot loop.

Sources: OpenRouter TypeSafe/Jev Decisions API docs and model pages (`typesafe/jev-latest`,
`typesafe/jev-1.13`), Sept 2026.
