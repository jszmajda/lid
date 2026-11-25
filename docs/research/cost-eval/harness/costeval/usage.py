"""Token usage of Claude Code sessions, read from their records.

There are two sources, and the plumbing test showed they agree to the token:

- A session's result record (the last `result` line of `claude -p --output-format
  stream-json`). Its `modelUsage` and `total_cost_usd` include subagents. After
  `--resume` they are cumulative for the whole session, so the cost of one turn
  is the difference between consecutive results. Its top-level `usage` field
  covers only the main thread and is never used.
- The session's transcripts on disk: the main transcript plus every file in its
  `subagents/` folder. They are the fallback for a run that ended without a
  result record, because failed runs count.

Dollars are not computed here. Claude Code's own estimate is kept as
`reported_cost_usd`; reports price the tokens from a dated price table.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path


class NotCumulative(ValueError):
    """A later result reports less of something than an earlier one."""


@dataclass(frozen=True)
class TokenCounts:
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write_5m: int = 0
    cache_write_1h: int = 0

    @property
    def cache_write(self) -> int:
        return self.cache_write_5m + self.cache_write_1h

    def __add__(self, other: TokenCounts) -> TokenCounts:
        return TokenCounts(*(getattr(self, f.name) + getattr(other, f.name) for f in fields(self)))

    def __sub__(self, other: TokenCounts) -> TokenCounts:
        return TokenCounts(*(getattr(self, f.name) - getattr(other, f.name) for f in fields(self)))

    def any_negative(self) -> bool:
        return any(getattr(self, f.name) < 0 for f in fields(self))


@dataclass(frozen=True)
class Usage:
    """Tokens by model, plus Claude Code's own dollar estimate when the source has one."""

    models: dict[str, TokenCounts] = field(default_factory=dict)
    reported_cost_usd: float | None = None

    def total(self) -> TokenCounts:
        out = TokenCounts()
        for counts in self.models.values():
            out = out + counts
        return out


@dataclass(frozen=True)
class StreamSummary:
    session_id: str | None
    usage: Usage | None
    is_error: bool | None
    result: dict | None


def _split_writes(total: int, five_min: int | None, one_hour: int | None) -> tuple[int, int]:
    # Records without the lifetime split are treated as five-minute writes, the default lifetime.
    if five_min is None and one_hour is None:
        return total, 0
    return five_min or 0, one_hour or 0


def from_result(record: dict) -> Usage:
    """Usage from one result record's `modelUsage` and `total_cost_usd`."""
    models = {}
    for model, entry in (record.get("modelUsage") or {}).items():
        w5, w1 = _split_writes(
            entry.get("cacheCreationInputTokens", 0),
            entry.get("cacheCreationEphemeral5mInputTokens"),
            entry.get("cacheCreationEphemeral1hInputTokens"),
        )
        models[model] = TokenCounts(
            input=entry.get("inputTokens", 0),
            output=entry.get("outputTokens", 0),
            cache_read=entry.get("cacheReadInputTokens", 0),
            cache_write_5m=w5,
            cache_write_1h=w1,
        )
    return Usage(models=models, reported_cost_usd=record.get("total_cost_usd"))


def turn_delta(previous: Usage | None, current: Usage) -> Usage:
    """The usage of one turn, given the session's cumulative results before and after it."""
    if previous is None:
        return current
    missing = set(previous.models) - set(current.models)
    if missing:
        raise NotCumulative(f"models missing from the later result: {sorted(missing)}")
    models = {}
    for model, counts in current.models.items():
        d = counts - previous.models.get(model, TokenCounts())
        if d.any_negative():
            raise NotCumulative(f"{model}: a counter went down ({d})")
        models[model] = d
    cost = None
    if current.reported_cost_usd is not None and previous.reported_cost_usd is not None:
        cost = current.reported_cost_usd - previous.reported_cost_usd
    return Usage(models=models, reported_cost_usd=cost)


def _json_lines(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def from_stream(path: Path) -> StreamSummary:
    """The session ID and last result of one `claude -p` stream-json output file."""
    session_id = None
    last_result = None
    for rec in _json_lines(Path(path)):
        session_id = rec.get("session_id", session_id)
        if rec.get("type") == "result":
            last_result = rec
    if last_result is None:
        return StreamSummary(session_id=session_id, usage=None, is_error=None, result=None)
    return StreamSummary(
        session_id=session_id,
        usage=from_result(last_result),
        is_error=bool(last_result.get("is_error")),
        result=last_result,
    )


def from_transcripts(main_transcript: Path) -> Usage:
    """Usage summed over a session's main transcript and its subagents' transcripts.

    A message can be written to a transcript more than once, so each message ID counts once.
    """
    main_transcript = Path(main_transcript)
    paths = [main_transcript]
    sub_dir = main_transcript.with_suffix("") / "subagents"
    if sub_dir.is_dir():
        paths += sorted(sub_dir.glob("*.jsonl"))
    seen: dict[str, tuple[str, TokenCounts]] = {}
    for path in paths:
        for rec in _json_lines(path):
            msg = rec.get("message") or {}
            u = msg.get("usage")
            if rec.get("type") != "assistant" or not u or not msg.get("id"):
                continue
            split = u.get("cache_creation") or {}
            w5, w1 = _split_writes(
                u.get("cache_creation_input_tokens", 0),
                split.get("ephemeral_5m_input_tokens"),
                split.get("ephemeral_1h_input_tokens"),
            )
            seen[f"{path.name}:{msg['id']}"] = (msg.get("model", "unknown"), TokenCounts(
                input=u.get("input_tokens", 0),
                output=u.get("output_tokens", 0),
                cache_read=u.get("cache_read_input_tokens", 0),
                cache_write_5m=w5,
                cache_write_1h=w1,
            ))
    models: dict[str, TokenCounts] = {}
    for model, counts in seen.values():
        models[model] = models.get(model, TokenCounts()) + counts
    return Usage(models=models, reported_cost_usd=None)
