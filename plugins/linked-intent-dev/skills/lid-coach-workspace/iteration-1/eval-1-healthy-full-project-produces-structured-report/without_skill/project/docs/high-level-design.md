# High-Level Design: Note-taking App

## Problem

Users need a low-friction way to capture thoughts across devices.

## Approach

A local-first note store with cloud sync. Notes are plain text files; sync is a background reconciliation over an append-only event log.

## Target Users

Individual knowledge workers on mobile and desktop.

## Architecture

Client-side store, event-log sync server, resolver service for conflicts.

## Key Design Decisions

Local-first over cloud-first: users work offline, conflicts reconcile on reconnect.

## Goals

Low latency capture. Offline by default. No vendor lock-in on note format.

## Non-Goals

Real-time collaborative editing. Rich media beyond plain text.
