# HLD

## Problem

We track package deliveries.

## History

Originally we used polling. Then we migrated to webhooks in Q2. We are planning to move to a streaming architecture in Q4, but for now webhooks remain authoritative.

## Approach

We receive webhook events from carriers and persist them.

## Changelog

- 2024-01: Initial draft with polling design.
- 2024-04: Revised for webhooks.
- 2024-07: Added retry logic section.
