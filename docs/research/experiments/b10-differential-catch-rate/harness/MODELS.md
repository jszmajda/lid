# GPT-5.6 model IDs for the b10 harness

Discovered via `GET https://api.openai.com/v1/models` on 2026-08-02 using the
experiment account key. Exact IDs (no dated variants exist for 5.6):

| Marketing name | API model ID    |
|----------------|-----------------|
| Sol            | `gpt-5.6-sol`   |
| Terra          | `gpt-5.6-terra` |
| Luna           | `gpt-5.6-luna`  |

The API echoes the same ID back in the response `model` field (verified for
`gpt-5.6-luna`).

## Endpoint

`openai_call.py` uses the **Responses API**: `POST https://api.openai.com/v1/responses`.

Chosen over `/v1/chat/completions` because GPT-5.x are reasoning-first models
and Responses is OpenAI's primary endpoint for them: it accepts a plain
`max_output_tokens` cap (chat completions rejects `max_tokens` for these
models), reports reasoning tokens separately in usage, and carries an explicit
`status` / `incomplete_details` so truncated-by-token-cap runs are detectable.
The system prompt (`--system-file`) is sent as the `instructions` field.

## Usage fields (verbatim from the API, for cost readout)

The `usage` object copied into each harness output JSON:

- `input_tokens`
- `input_tokens_details.cached_tokens`
- `input_tokens_details.cache_write_tokens`
- `output_tokens`
- `output_tokens_details.reasoning_tokens`
- `total_tokens`

Note: `output_tokens` **includes** reasoning tokens; visible text tokens are
`output_tokens - output_tokens_details.reasoning_tokens`. Billable counts for
a cost readout are `input_tokens` (minus any cached discount) and
`output_tokens`.

## Validation

Two live calls against `gpt-5.6-luna` (2026-08-02), trivial prompts,
`--max-tokens 64`: both completed with correct text, real usage numbers
(e.g. 13 in / 5 out / 18 total, 0 reasoning tokens), latencies 2030 ms and
856 ms, and `x-request-id` captured as `request_id`.
