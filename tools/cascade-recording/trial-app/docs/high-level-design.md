# High-Level Design

## Problem

People decide whether a subscription app is worth paying for by using it, and many won't sign up for one they can't try first.

## Goals

New users can try the app free for 30 days before they pay.

## Tenets

- **Customer delight over perfect cost management.** When a choice could go either way, we lean toward the customer.

## Architecture

A TypeScript service. Its one component so far is the trial (`docs/intent/trial/`): when a new user's free trial starts, what it allows while it runs, and when it ends.
