We're designing a research study comparing how different ways of working with AI coding agents perform as software is changed over time. We look at two things: what the work costs, and how faithfully the software keeps doing what its owner intended. The approaches range from using an agent with no special process, through lightweight discipline (planning first, writing tests, keeping notes), to structured spec-driven development methods that keep requirement and design documents next to the code.

In each run, an agent builds a small application from a product brief, then makes a sequence of 8 to 15 changes to it. Each change happens in a fresh session, so the agent remembers nothing from earlier sessions beyond what is in the repository. A simulated product owner holds a fuller, hidden description of what they want. The owner answers the agent's questions from it, and sometimes changes their mind or clarifies partway through a change. Model-based graders then check whether the running software still matches everything the owner has asked for so far.

Please propose 5 candidate project domains for this study. A good candidate has:

- rules that matter but aren't obvious from reading the code: exceptions, edge cases, and invariants that apply across the whole system. Examples are whether a deadline counts business days, and in whose time zone a day ends.
- at least three components, with contracts between them that a developer would normally leave unwritten.
- requirements that will later conflict with each other, or earlier decisions that a later change will reverse.
- a natural external interface, either a command-line tool or an HTTP API, small enough to describe in a brief.
- room for a realistic mix of later changes. Some should be purely local (a label, a field, a dependency upgrade). Some should depend on rules stated much earlier. Some should cut across the whole system, and some should be reported only as a symptom.
- a first version of about 1,000 to 3,000 lines of code that can be built cheaply, and that can grow over the changes.
- a domain that isn't a common tutorial example such as a to-do list, a blog, or a chat app, because models may have memorized standard solutions.

For each candidate, give:

1. A name and a two-sentence product summary.
2. The external interface, in a few lines.
3. Five to eight hidden rules that a product owner would care about but might not state up front.
4. The components, and the unwritten contracts between them.
5. A sketch of 10 later changes, each labelled with its kind: local, depends on an earlier rule, cross-cutting, reversal, symptom-only bug report, or refactor/upgrade. Include one change of mind and one clarification that the owner delivers partway through a change.
6. Why this project would tell the approaches apart, and what could make it a poor test. For example, it might be too easy for a strong model, depend too much on specialist domain knowledge, or be too large to build cheaply.

Finish with a short ranking of your five, with a sentence on why your top choice is the best test.
