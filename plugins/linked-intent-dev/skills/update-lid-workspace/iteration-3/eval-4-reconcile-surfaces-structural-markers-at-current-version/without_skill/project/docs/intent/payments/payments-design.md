---
parent: high-level-design
prefix: PAY
---
# LLD: Payments

Handles charges and the processing fees recorded against them. The processing fee is a facet of a charge, not a separate intent, so its specs live in this leaf under the `PAY-FEE-*` within-leaf facet rather than a sibling namespace.
