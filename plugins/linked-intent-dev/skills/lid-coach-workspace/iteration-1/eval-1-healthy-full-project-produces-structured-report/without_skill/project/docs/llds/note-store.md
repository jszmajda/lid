# LLD: Note Store

## Context

The note store is the local persistence layer for plain-text notes. It supports create, read, update, delete, and list operations, with an event log recording every mutation.

## Architecture

Flat directory of one file per note, indexed by a SQLite database for fast listing and search.

## Behaviors

Note creation writes the file and appends a create event. Note deletion removes the file and appends a delete event. The event log is append-only; compaction is out of scope for v1.

## Decisions & Alternatives

| Decision | Chosen | Rationale |
|---|---|---|
| Storage | Filesystem + SQLite | Simple, grep-friendly, survives across app upgrades. |
| Event log | Append-only JSONL | Simplest durable log; no schema evolution needed v1. |
