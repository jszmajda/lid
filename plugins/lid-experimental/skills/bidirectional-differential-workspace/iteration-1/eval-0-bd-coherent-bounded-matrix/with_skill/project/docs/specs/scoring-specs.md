# scoring specs

**LLD**: docs/llds/scoring.md
**Implementing artifacts**:
- src/scoring.ts

- [x] **SCORE-001**: When scoring an item X against a reference Y, the system SHALL assign 3 if A(X,Y) and B(X,Y); 2 if A(X,Y) and not B(X,Y); 1 if not A(X,Y) and B(X,Y); 0 if not A(X,Y) and not B(X,Y).
