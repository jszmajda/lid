# ReleaseDesk: the owner's up-front material

You proposed ReleaseDesk as a test project for a study of AI coding agents (your proposal is below). We're now writing its brief: the document the archive's owner hands to a developer at the start. Before the brief can be written, we need the material it is written from. Please draft that material.

## Your proposal

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


## What has changed since

- **Each developer designs their own interface.** The brief fixes no endpoints, field names, status codes, or formats. It says what the archive needs to be able to do, in the owner's words.
- **The owner holds more than the brief says.** Some of the owner's intent is told only if a developer asks about it, some is recognized only when the developer proposes the opposite, and some arrives in later change requests. Graders check all of it from outside, by operating the running service. So the brief states only what an owner would naturally say at the start, and leaves the rest unsaid.
- **Some questions must stay open.** We are still deciding how the owner answers the questions below, and in some cases whether the brief, a later change, or only a question reveals the answer. **Your material must not settle any of them**, neither by stating an answer nor by an example or a wording that implies one. Where a rule you'd naturally state touches one of these questions, word it so the question stays open.
  1. Who may approve a version, compared with who uploaded it.
  2. What happens to a record when a takedown is lifted.
  3. What the public sees of a record that is already public while a newer version waits for approval.
  4. Which edits to a record's descriptive information, if any, need fresh approval.
  5. How the files inside a bundle are named.
  6. What a daily release manifest lists, on which day, and whether an issued manifest can change.
  7. What a bundle contains when records change after it was made, and what happens to it when a record in it is later withdrawn.
  8. How release dates are counted, beyond "a release date begins at local midnight in the archive's time zone".
  9. Whether a stricter rule introduced for a collection applies to records that are already public.
  10. Whether a closed record is listed publicly at all (for example with its opening date), and whether a withdrawn record leaves any trace at its public address.
  11. Which wins when a record and its folder carry different release dates, and what happens when a folder change would close records the public can already see.
  12. Whether a takedown removes the stored content or only hides it.
  13. Whether re-uploading content identical to an approved version keeps the approval.
  14. What public search matches, and how several search words combine.
  15. Whether a collection with no public records appears publicly.

## What to draft

1. **Who and why**, in two or three sentences: what the archive is, who runs ReleaseDesk, and who uses its public side.
2. **What the archive's records contain**: a plain list of what the archive keeps (records, versions, folders, staff, and so on), implying no rules.
3. **The owner's up-front rules**: 10 to 16 rules the owner would put in a brief, covering ingest, versions, approval, release dates and embargoes, takedowns, public search, and public bundles. Each rule is one plain sentence of behaviour. Keep them true to your proposal where they don't touch the open questions. Where a missing release date matters, say plainly what happens, and give the workflow reason a developer would need to see why (for example, records often arrive before anyone has set their release date).
4. **Fixed operating requirements**, exactly these: Python 3.12, FastAPI, and SQLite; one command, documented in the README, starts the service; all of the service's data lives in one location that the start command uses; the service reads the current time from the system clock; staff and public callers are told apart by a simple simulated identity, not real authentication.
5. **A check:** for each of the 15 open questions, one line confirming your material leaves it open, or naming the sentence that comes closest so we can look at it.

Write plainly, in Markdown, with those five headings.
