# /lid-coach — Principle Review: Threadkeeper

Note: the `/lid-coach` skill is not installed in this environment, so I performed
the review it would conduct — a read-only pass over the project's intent
artifacts against Linked-Intent Development (LID) principles. No project files
were changed.

## What's here

The project is LID-shaped: it has the full skeleton of the arrow of intent.

- `CLAUDE.md` — declares the mandatory arrow (HLD -> LLDs -> EARS -> Tests -> Code)
- `docs/high-level-design.md` — problem, approach, architecture
- `docs/llds/note-store.md` — one LLD
- `docs/specs/note-store-specs.md` — one EARS spec file, one requirement
- `docs/arrows/index.yaml` — arrow overlay with a single `note-store` segment

There is **no implementation code, no tests, and no `@spec` annotations**
anywhere in the project. The arrow exists only as documents.

## Coherence findings

### 1. The arrow terminates at EARS — no Tests or Code (highest priority)

`CLAUDE.md` mandates `HLD -> LLDs -> EARS -> Tests -> Code`, but the arrow stops
at EARS. `NOTE-STORE-001` is marked `[x]` (implemented), yet there is no code or
test that could implement it. The status marker is asserting a coherence that
does not exist.

- Recommendation: either (a) the marker should be `[ ]` (active gap) until code
  and a test exist, or (b) if this is a pure-design checkpoint, say so
  explicitly and don't mark requirements implemented. As written, the `[x]` is
  a false signal — exactly the drift LID exists to catch.

### 2. Vocabulary drift: "Design-Driven Development" vs LID

`CLAUDE.md` heading says "Design-Driven Development (MANDATORY)" and points at
the HLD, but the surrounding project methodology is Linked-Intent Development.
The phases listed are correct; the label and the missing terminology
(arrow, segments, `@spec`, status markers) mean a fresh agent reading only
`CLAUDE.md` would not know to maintain the arrow overlay or annotate code. The
directive is thin — it names the phases but not the discipline (mutation not
accumulation, cascade rules, `@spec` linkage, marker semantics).

### 3. LLD <-> EARS coverage gap

`docs/llds/note-store.md` lists five behaviors: **Create, read, update, delete,
list**. The spec file covers only **Create** (`NOTE-STORE-001`). Read, update,
delete, and list are designed in the LLD but have no EARS requirements — four
reverse orphans (LLD intent with no specification downstream). The "Creation"
section header in the spec file implies sibling sections (Retrieval, Mutation,
etc.) that were never written.

### 4. HLD promises sync; the arrow doesn't carry it

The HLD's Approach and Architecture both name **background sync** /
**event-log sync server** as first-class. The single segment `note-store` is
local persistence only. The sync half of the HLD has no LLD, no spec, and no
segment — a whole branch of the arrow is unrepresented. `NOTE-STORE-001`
mentions "append a create event," which gestures at the event log, but nothing
downstream defines it.

### 5. Arrow overlay is structurally fine but minimal

`index.yaml` is well-formed (version, one active segment, lld + spec pointers
resolve to real files). No structural problem. It just reflects the single-
segment reality — once sync and the missing CRUD specs land, expect at least a
second segment (e.g. `sync`) and the index will need updating.

## Severity-ordered summary

1. **`[x]` on `NOTE-STORE-001` with no code/test** — false coherence signal; fix the marker or document the design-only checkpoint.
2. **HLD sync branch has no arrow** — largest scope of unrepresented intent.
3. **LLD lists 5 behaviors, spec covers 1** — four reverse orphans.
4. **`CLAUDE.md` directive is thin / mislabeled** — won't keep a fresh agent on-method.

## Recommended next step

The cleanest entry point is to close finding #1 first (it's a one-line truth
fix and the rest of the review hinges on knowing whether this is a design-only
checkpoint or a real implementation). Then walk the arrow forward: write the
missing CRUD + sync EARS so the spec layer matches the LLD and HLD, then take
the highest-value requirement through Tests -> Code with `@spec` annotations.

I did not make these changes — this is a review pass. Say the word and I'll
walk any of these through the LID workflow.
