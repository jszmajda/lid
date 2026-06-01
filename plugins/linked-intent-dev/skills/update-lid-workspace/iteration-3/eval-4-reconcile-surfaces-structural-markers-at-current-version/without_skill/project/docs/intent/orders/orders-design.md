---
parent: high-level-design
prefix: ORDER
---
# sub-HLD: Orders

Orders group the storefront's order lifecycle and its refund sub-flow under one
parent intent. This node owns no EARS directly; its specs live in the leaf
children below.

## Children

- **lifecycle** (`ORDER-LIFECYCLE`) — creating and tracking an order through its states.
- **refund** (`ORDER-REFUND`) — the refund sub-flow against a placed order.
