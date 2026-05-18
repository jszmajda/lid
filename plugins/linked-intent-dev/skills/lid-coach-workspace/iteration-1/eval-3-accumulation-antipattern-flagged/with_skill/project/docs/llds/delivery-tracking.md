# LLD: Delivery Tracking

## Context

We used to keep state in Redis, but now we use Postgres. The old Redis-based approach is documented below for reference.

## Previous Architecture (Redis)

We maintained a hash per shipment in Redis. This was deprecated in Q2 due to durability concerns.

## Current Architecture (Postgres)

Shipments are rows in the `shipments` table.

## Planned Architecture (Streaming)

In Q4 we plan to move to Kafka.
