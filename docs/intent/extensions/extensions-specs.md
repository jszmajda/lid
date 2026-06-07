# Extensions Specs

**LLD**: docs/intent/extensions/extensions-design.md
**Implementing artifacts**:
- EXTENSIONS.md
- the `linked-intent-development` GitHub topic on the core repository (configuration)

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## EXTENSIONS.md

- `[x]` **EXT-001**: An `EXTENSIONS.md` file SHALL exist at the repository root as a curated showcase of third-party projects that extend LID. Its content is owned by this segment, not by `project-structure`, although the file sits at the repository root.
- `[x]` **EXT-002**: `EXTENSIONS.md` SHALL state that listing is an editorial showcase, not a security or quality endorsement — consistent with the HLD Non-Goal *Not adversarial security review* and `SECURITY.md`, a listed extension's safety and quality remain the user's own assessment.
- `[x]` **EXT-003**: `EXTENSIONS.md` SHALL include a "how to get listed / make your extension discoverable" section documenting the discovery convention for extension authors.

## Discovery convention

- `[x]` **EXT-004**: An extension repository SHALL become discoverable by tagging itself with the canonical GitHub topic `linked-intent-development` and linking back to the core repository. There SHALL be no submission or approval step for discoverability.
- `[x]` **EXT-005**: The canonical topic SHALL be `linked-intent-development` (not `lid`, which is too generic), and the core `jszmajda/lid` repository SHALL carry that topic so the topic page is anchored by the source project.
- `[x]` **EXT-006**: Curation of `EXTENSIONS.md` SHALL NOT gate discovery — a project's discoverability through the convention SHALL NOT depend on being listed in `EXTENSIONS.md`.

## Verification

- `[ ]` **EXT-007**: A repository check SHALL flag broken links in `EXTENSIONS.md`. Deferred — no CI link-checking is wired yet; tracked alongside the `PROJ-STRUCT-039`–`041` build-check backlog.
