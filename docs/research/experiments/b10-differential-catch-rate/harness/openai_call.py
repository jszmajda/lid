#!/usr/bin/env python3
"""Minimal OpenAI Responses API caller for the b10 experiment harness.

Stdlib only (urllib, json, argparse). Single call per invocation.

Usage:
    openai_call.py --model <model-id> --prompt-file <path> --out <path> \
        [--max-tokens N] [--system-file <path>]

Writes a JSON object to --out with: text, usage (verbatim from the API),
latency_ms, model (as echoed by the API), request_id (x-request-id header,
falling back to the response body id). On terminal failure, writes an error
JSON to --out and exits nonzero.

Auth: reads the API key from the CHATGPT_EXPERIMENTS env var if set,
otherwise from ~/.secrets.conf (shell KEY=value format, quotes tolerated).
The key is never printed or written anywhere.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://api.openai.com/v1/responses"
MAX_ATTEMPTS = 5
SECRETS_PATH = os.path.expanduser("~/.secrets.conf")
KEY_NAME = "CHATGPT_EXPERIMENTS"


def load_api_key():
    val = os.environ.get(KEY_NAME)
    if val and val.strip():
        return val.strip()
    try:
        with open(SECRETS_PATH) as f:
            for line in f:
                m = re.match(
                    r"^(?:export\s+)?" + KEY_NAME + r"\s*=\s*(.*)$", line.strip()
                )
                if m:
                    v = m.group(1).strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                        v = v[1:-1]
                    if v:
                        return v
    except OSError as e:
        raise SystemExit(f"cannot read {SECRETS_PATH}: {e.strerror}")
    raise SystemExit(
        f"{KEY_NAME} not found in environment or {SECRETS_PATH}"
    )


def scrub(text, key):
    """Remove the key from any text that might be printed or written."""
    return text.replace(key, "<REDACTED>") if key else text


def extract_text(body):
    """Concatenate all output_text content from a Responses API body."""
    parts = []
    for item in body.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
    return "".join(parts)


def call_api(key, payload):
    """POST with retry on 429/5xx. Returns (body_dict, request_id, latency_ms).

    Raises RuntimeError (message already scrubbed) on terminal failure.
    """
    data = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(
            API_URL,
            data=data,
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                latency_ms = int((time.monotonic() - start) * 1000)
                body = json.load(resp)
                request_id = resp.headers.get("x-request-id") or body.get("id")
                return body, request_id, latency_ms
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:2000]
            last_err = scrub(f"HTTP {e.code}: {detail}", key)
            if e.code == 429 or 500 <= e.code < 600:
                if attempt < MAX_ATTEMPTS:
                    retry_after = e.headers.get("Retry-After")
                    try:
                        delay = float(retry_after)
                    except (TypeError, ValueError):
                        delay = min(2 ** (attempt - 1), 30)
                    time.sleep(delay)
                    continue
            else:
                break  # non-retryable status
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = scrub(f"{type(e).__name__}: {e}", key)
            if attempt < MAX_ATTEMPTS:
                time.sleep(min(2 ** (attempt - 1), 30))
                continue
    raise RuntimeError(last_err or "request failed")


def main():
    ap = argparse.ArgumentParser(description="Single OpenAI Responses API call.")
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--system-file", default=None)
    args = ap.parse_args()

    with open(args.prompt_file) as f:
        prompt = f.read()

    payload = {
        "model": args.model,
        "input": [{"role": "user", "content": prompt}],
    }
    if args.max_tokens is not None:
        payload["max_output_tokens"] = args.max_tokens
    if args.system_file:
        with open(args.system_file) as f:
            payload["instructions"] = f.read()

    key = load_api_key()
    try:
        body, request_id, latency_ms = call_api(key, payload)
    except RuntimeError as e:
        err = {"error": str(e), "model_requested": args.model}
        with open(args.out, "w") as f:
            json.dump(err, f, indent=2)
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    result = {
        "text": extract_text(body),
        "usage": body.get("usage"),
        "latency_ms": latency_ms,
        "model": body.get("model"),
        "request_id": request_id,
    }
    # Flag truncation/incompleteness so downstream analysis can filter it.
    status = body.get("status")
    if status and status != "completed":
        result["status"] = status
        if body.get("incomplete_details"):
            result["incomplete_details"] = body["incomplete_details"]

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
