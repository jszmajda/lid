# Skeleton HLD Template

For `/map-codebase`'s Phase 5 skeleton HLD generation, use the standard HLD template from the linked-intent-dev plugin:

**Template path**: `plugins/linked-intent-dev/skills/linked-intent-dev/references/hld-template.md`

## Brownfield adaptation

When drafting a skeleton HLD for a brownfield project:

- Use the same section structure as greenfield HLDs. There is no separate brownfield HLD template.
- Mark bodies `*(not yet specified)*` rather than filling with placeholder prose. Visible gaps beat invented content.
- For sections where the sweep has already produced information the user can confirm (the System Design overview, for example, may be partially inferable from the segmentation), include a short inferred summary with `[inferred]` markers so the user can later confirm or refute.
- The HLD is drafted *after* per-segment LLDs in the bottom-up flow — it emerges from what the LLDs revealed, not from top-down architecture.

## Do not modify existing HLDs

If `docs/high-level-design.md` already exists when `/map-codebase` runs, skip the skeleton-HLD step entirely. Never overwrite an existing HLD. The user may update it themselves after the mapping completes using the `linked-intent-dev` workflow.
