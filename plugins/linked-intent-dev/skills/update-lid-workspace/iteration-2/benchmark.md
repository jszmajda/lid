# update-lid eval iteration 2 — rename-verification benchmark

**Date**: 2026-05-14
**Skill**: update-lid (renamed from lid-setup)
**Iteration**: 2
**Purpose**: Verify the `lid-setup` → `update-lid` rename did not regress any iteration-1 behavior. Skill-body diff vs the previous `lid-setup/SKILL.md` is 12 lines, all confined to frontmatter / header / first two intro paragraphs; the 100+ lines of operational behavior are byte-identical.

## Summary

| Configuration | Pass rate | Assertions passed |
|---|---|---|
| **with_skill (iteration 2, renamed)** | **100%** | 13/13 |
| with_skill (iteration 1, baseline) | 100% | 13/13 |
| Delta | 0 | 0 |

**No regressions.** Every assertion that passed in iteration 1 with the `lid-setup` skill still passes with the renamed `update-lid` skill.

## Eval 0: bootstrap-empty-project

| Assertion | with_skill (iter 2) |
|---|---|
| docs/llds/ exists | ✓ |
| docs/specs/ exists | ✓ |
| docs/high-level-design.md populated from HLD template | ✓ |
| docs/planning/ NOT created | ✓ |
| CLAUDE.md has `## LID Mode: Full` | ✓ |
| CLAUDE.md has LID directives (`linked-intent-dev` or `Linked-Intent Development`) | ✓ |
| Response summarizes changes | ✓ |
| **Total** | **7/7** |

**Observations**: The renamed skill correctly dispatched to the Full bootstrap branch, honored the explicit "Use Full LID" instruction in the prompt without re-prompting, populated the HLD from the template with sections marked `*(not yet specified)*`, and omitted the arrow-overlay navigation row (no `docs/arrows/` present). Identical behavior shape to iteration 1.

## Eval 1: append-to-existing-claude-md

| Assertion | with_skill (iter 2) |
|---|---|
| Original content preserved (# My Project, ## Conventions, 3 bullets) | ✓ |
| LID directives appended | ✓ |
| `## LID Mode:` heading present | ✓ |
| Response names sections added | ✓ |
| **Total** | **4/4** |

**Observations**: Append branch executed correctly — existing content preserved verbatim, LID directives + mode marker appended, mode defaulted to Full (per skill's "If the user does not specify a mode, select Full"), Navigation table written without arrow-overlay row. The summary explicitly enumerates the sections added.

## Eval 2: idempotent-on-configured-project

| Assertion | with_skill (iter 2) |
|---|---|
| No file changes made (CLAUDE.md and HLD byte-equal to starting fixture) | ✓ |
| Response informs user what was detected | ✓ |
| **Total** | **2/2** |

**Observations**: Skill correctly entered the **Reconcile conventions** branch (not the **Inform and skip** branch — the directives in `CLAUDE.md` are truncated relative to the current template, which is convention drift). Drift was surfaced for user decision rather than auto-applied, matching iteration 1's behavior (LID-UPDATE-005, formerly LID-SETUP-005). Starting fixture preserved byte-for-byte. The "no auto-apply" eval constraint was honored.

## Timing

| Eval | Tokens | Duration (s) |
|---|---|---|
| eval-0 | 30,956 | 84.7 |
| eval-1 | 31,262 | 88.3 |
| eval-2 | 30,780 | 86.1 |
| **Total** | **93,008** | **259.1** |

## Verdict

**Rename verified.** The `lid-setup` → `update-lid` rename, the new description, the `disable-model-invocation: true` addition, and the removal of command stubs (skills are now invoked directly by name per Claude Code's skills model) did not regress any of iteration 1's previously-passing assertions. The skill's operational body — which the eval primarily tests — is unchanged from iteration 1.

## What changed since iteration 1

- Skill directory renamed: `plugins/linked-intent-dev/skills/lid-setup/` → `plugins/linked-intent-dev/skills/update-lid/`.
- `name:` frontmatter: `lid-setup` → `update-lid`.
- `description:` rewritten (removed alias mention; added "/linked-intent-dev for fresh projects" note).
- Skill body header `# LID Project Setup` → `# update-lid`.
- First two intro paragraphs rephrased to remove `/lid-setup` alias references.
- `commands/` directory removed entirely; skill is invoked directly as `/update-lid` per Claude Code's skills model.
- Spec IDs renamed: `LID-SETUP-NNN` → `LID-UPDATE-NNN` (specs file path: `docs/specs/lid-setup-specs.md` → `docs/llds/linked-intent-dev/update-lid/update-lid-specs.md`).

All other lines in `SKILL.md` are byte-identical to the previous `lid-setup/SKILL.md`.
