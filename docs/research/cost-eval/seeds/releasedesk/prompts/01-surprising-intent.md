# Surprising owner intent for ReleaseDesk

You're helping design the second test project for a research study. The study measures what different ways of working with AI coding agents cost, over a sequence of changes: a bare agent, an agent with light discipline (plan first, keep notes, write tests), and spec-driven methods that write intent down before code. Each way of working builds the same small service from a brief written in the owner's words. It then makes ten scripted changes, each in a fresh session that remembers nothing but the repository. A simulated owner answers the agent's questions from a hidden list of rules. Graders check every rule from outside, by operating the running service.

## What the first test project taught us

On the first project, a lab-instrument booking service, a strong model working alone met about 88% of the rules, even with an owner who never volunteered anything. Most of the hidden rules were sensible defaults: a careful engineer guesses them from the brief, so they don't need to be asked for, written down, or remembered. The rules it consistently missed were conventions that could reasonably go either way, sitting in corners the agent never thought to raise.

So a project whose intent is guessable can't show whether eliciting, recording, and preserving intent is worth what it costs. We want the second project to also carry intent that a strong model would not guess, and that has to keep holding as the software changes.

We also have to stay fair. The study is run by the maintainer of one of the methods being compared, which asks a lot of questions and writes intent down. A project stuffed with trick rules that only asking can reveal would rig the result. Every rule has to be one a real owner of such a system could hold, for a reason they could explain, and that real organizations set both ways.

## The project

This is the proposal for the second project, ReleaseDesk, as an outside model wrote it. Treat its hidden rules and changes as a starting point, not as fixed.

### ReleaseDesk — embargoed archive publication

#### Product summary
A small archive uses ReleaseDesk to ingest text records, approve publication, and release public search results and download bundles. Publication depends on embargo dates, content approval, and takedowns, with restricted records remaining invisible to public callers.

**V1 boundary:** Plain-text attachments, structured metadata, simple substring search, one archive time zone, and ZIP bundles; approximately **1,700–2,600 lines**. No PDF extraction, OCR, or production authentication.

#### External interface
```text
POST /records                  POST /records/{id}/versions
POST /records/{id}/approve      POST /records/{id}/takedown
GET /search                    POST /bundles
GET /bundles/{id}/download
```
Fixture actors represent staff, public users, and later named researchers.

#### Hidden rules
1. A release date begins at 00:00 in the archive’s time zone; an absent date means indefinitely closed.
2. Embargo expiry is necessary but insufficient: the current content version must also be approved.
3. A folder’s default embargo is initially copied at ingest and then frozen; moving a record does not silently change it.
4. Restricted records are absent from public lists, counts, search results, filenames, and bundles—not merely blocked on direct download.
5. Replacing content invalidates approval; editing a non-policy display label does not.
6. A takedown overrides dates and approvals and must affect previously created bundles when they are downloaded.
7. Public outputs must not expose restricted provenance, blocked record IDs, or staff-only reasons.

#### Components and unwritten contracts
- **Ingest/version store:** Separates content changes from harmless metadata edits and gives each content version a stable identity.
- **Policy engine:** Answers access questions for a specific actor, version, and time.
- **Search/catalog projection:** Must not implement a weaker approximation of the policy engine.
- **Bundle service and audit trail:** Recheck access at download time; audit detail is not automatically public metadata.

#### Ten later changes
1. **Local:** Rename the public metadata label “folder” to “collection,” preserving identifiers.
2. **Depends on an earlier rule:** Add a scheduled daily release manifest, respecting local midnight and current-version approval.
3. **Refactor/upgrade:** Consolidate access decisions behind one policy interface without changing public outputs.
4. **Cross-cutting:** Grant named researchers access to selected embargoed records without making those records public.
5. **Depends on an earlier rule — mid-change clarification:** Add bundle previews. Halfway through, the owner clarifies that public previews must omit blocked items entirely; only staff may see exclusion reasons.
6. **Reversal — mid-change change of mind:** During folder-policy editing, the owner decides existing unpinned records should follow the folder’s current embargo after all, even if a stricter date makes a previously public record private again.
7. **Symptom-only bug report:** “Search no longer shows the withdrawn letter, but last week’s download link still contains it.”
8. **Local:** Rewrite CLI help text and examples without changing command behavior.
9. **Depends on an earlier rule:** Allow content replacement within an existing catalog record, ensuring old approval does not authorize the new bytes.
10. **Cross-cutting:** Require two distinct staff approvals for a sensitive collection, updating approval history, release decisions, search, and bundles.

#### Why it distinguishes approaches—and its risks
This creates many opportunities for policy drift: an endpoint, cache, export, or saved artifact can preserve an obsolete interpretation. Structured requirements should help agents identify every affected surface when publication policy changes.

Its weakness is security breadth. Keep authentication simulated and access rules explicit; do not score unspecified penetration resistance, natural-language redaction, or production-grade storage security.


## What we'd like from you

Propose 15 to 20 candidate owner rules for ReleaseDesk that are **surprising but real**. For each, every one of these must hold:

1. **Realistic.** A real archive's owner could hold it, for a reason they could give in a sentence: a donor agreement, a legal or institutional policy, a past incident, a workflow the staff rely on.
2. **Surprising.** A strong model building from a plain brief would most likely implement the opposite, or something different. Say what it would probably do instead, and why.
3. **Either way.** Real organizations choose both ways. It isn't a bug, a trick, or an arbitrary quirk.
4. **Holds over time.** At least one of the ten later changes adds a new place or operation where the rule must be respected again, ideally where the agent must stay consistent with a choice made in an earlier session. Name which changes stress it, or propose a change that would.
5. **Checkable from outside.** A grader operating the running service, without reading code, can tell whether it holds. Avoid security penetration testing, judging natural-language quality, and exact field names or formats.

Then:

- Suggest, for each rule, how the owner would disclose it: stated in the brief, stated in a later change request (perhaps long before the change that tests it), told only when asked about its topic, recognized only when the agent proposes the opposite, or realized only at a later change. Spread the rules across these. Don't make them all hidden.
- Rate each rule's risk of being guessed anyway (low, medium, high), with one line on why.
- Name three to five general patterns that make intent both surprising and durable, which we could reuse in other projects.
- Name the pitfalls: rules that would look surprising to us but that you think a strong model would in fact guess, or rules that would unfairly reward one way of working.

Write plainly. Use a numbered list for the rules, each with short labelled parts: the rule, the likely default, the owner's reason, why either way, which changes stress it, how a grader checks it, the disclosure, and the guess risk.
