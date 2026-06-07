---
parent: high-level-design
prefix: EXT
---

# Extensions

## Context and Design Philosophy

The Extensions segment owns LID's relationship with the **third-party projects that build on it** — editor integrations, language servers, CLIs, CI coherence checkers, and other tooling a minimal core deliberately does not provide. Its job is to make that ecosystem **discoverable** and to **encourage** it, while LID hosts, runs, and gatekeeps none of it.

The segment exists because of minimum-system (HLD Goal 2): every capability LID does not build is delegated to the fast-moving layer, and in practice independent projects fill that space. A minimal core is only pleasant to use if the surrounding tooling is *findable* — so discoverability is the load-bearing intent here, not a list for its own sake.

Three principles shape the component:

- **Discovery by open convention, not an operated registry.** A project becomes findable by adopting a shared, public marker — not by submitting to or being approved by LID. Anyone who follows the convention is discoverable; there is no gate. This keeps the mechanism decentralized and zero-maintenance, and matches *verticalize intent* (no second registry to keep in sync) and *LID runs on the agent, not a runtime* (no service LID operates).
- **Curated showcase, but curation never gates discovery.** A maintained `EXTENSIONS.md` highlights notable projects as an editorial signal of quality and of a living community. It is a showcase, not an approval list: a project absent from it is still discoverable through the convention. Curation adds a trust signal on top of open discovery; it does not replace it.
- **Surface, never own.** LID points at extensions; it does not host, run, vet, or endorse them. Listing is editorial, not a security or quality guarantee — a third-party extension's safety is its own concern (HLD Non-Goal *Not adversarial security review*; `SECURITY.md`).

This is a distinct tier from LID's own plugins. First-party plugins ship from this repository's marketplace; `lid-experimental` houses first-party capability under evaluation; extensions are **third-party and independent**, surfaced but never owned (HLD Architecture § 3, Distribution).

## Owned Artifacts

### The discovery convention

An extension author makes a project discoverable by:

1. **Tagging the repository with the canonical GitHub topic `linked-intent-development`.** The core `jszmajda/lid` repository also carries this topic, so `github.com/topics/linked-intent-development` is anchored by the source project and resolves to the ecosystem.
2. **Linking back to the core repository** from the project's README or docs, so a reader who arrives at an extension can trace it back to LID.

The convention is intentionally thin — a topic plus a link, no manifest, schema, or registration step. `lid` is **not** the canonical topic: it is too generic and collides with unrelated uses; `linked-intent-development` is unambiguous. (The canonical example extension, `EtaCassiopeia/lid-tooling`, already carries both topics and links back; the convention canonicalizes on the specific one.)

### `EXTENSIONS.md`

A curated, repository-root showcase of notable third-party extensions. It does two jobs:

- **Helps users find tooling** the minimal core does not provide.
- **Shows the community is real** — a trust signal `marketing-site` draws on (see Cascade).

It also documents the convention itself ("how to make your extension discoverable / get listed"), so one page serves both readers and authors. Entries are maintainer-curated (editorial), not auto-generated and not an approval gate on discovery.

`EXTENSIONS.md` lives at the repository root but is owned by *this* segment, not by `project-structure`: ownership follows intent, and its content is ecosystem intent rather than repo-meta describing the project as a whole — the same reason `README.md` is owned by `marketing-site` despite its location.

## Component Variant

Content artifact (`HLD → LLD → EARS → content + assets`), matching `marketing-site` and `project-structure`. Verification is build-time structural checks (link integrity in `EXTENSIONS.md`) plus dogfooding review when the convention or the ecosystem stance changes. There is no runtime to assert against.

## Cascade

- **`marketing-site`** surfaces the ecosystem as a **social-proof / trust signal** (evidence LID is in real use) and links to `EXTENSIONS.md` / the topic. That framing is owned by `marketing-site`; this segment owns the substance it points at. When `EXTENSIONS.md` or the convention changes materially, the marketing surface is reviewed.
- **Canonical topic change** → `EXTENSIONS.md`'s "how to get discovered" section, the core repository's own topic, and the `marketing-site` link update together.
- **HLD Architecture § 3 (third-party ecosystem stance) change** → this LLD and `EXTENSIONS.md` are reviewed for drift.

The segment is a leaf; nothing downstream depends on it.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Discovery mechanism | Open convention (canonical GitHub topic + link-back) plus a curated `EXTENSIONS.md` showcase | A registry LID operates/approves; an `awesome-lid` list only; nothing | Open convention is decentralized, zero-maintenance, and self-organizing — no gate, no service (minimum-system; *LID runs on the agent, not a runtime*). The curated showcase adds an editorial trust signal on top without gating discovery. A LID-operated registry adds surface and a gatekeeping role LID does not want; an awesome-list-only approach loses the in-repo, cascade-coherent home. |
| Canonical topic | `linked-intent-development` | `lid`; accept both as canonical | Unambiguous; `lid` is too generic and collides with unrelated uses. Real extensions already use both; canonicalizing on the specific one (and carrying it on the core repo) anchors a clean topic page. |
| `EXTENSIONS.md` ownership | This segment, though the file sits at the repository root | `project-structure` (as a repo-meta artifact) | Ownership follows intent: the file's content is ecosystem intent, not repo-meta describing the project as a whole. Parallels `README.md` → `marketing-site`. |
| Curation posture | Editorial showcase that never gates discovery | Comprehensive auto-generated registry; gatekept inclusion list; no curation | Editorial curation gives a quality and community signal; keeping discovery open via the convention means a project's findability never depends on being listed. Auto-generation is tooling LID does not carry; a gatekept list makes LID an approver. |
| Node name / prefix | `extensions` / `EXT` | `ecosystem` / `ECO` | Concrete (matches `EXTENSIONS.md`), parallels LID's first-party "plugins" vs. third-party "extensions," resists scope creep, and reserves "ecosystem" as the natural name for a future outward-face parent sub-HLD. |
| Social-proof ownership | `marketing-site` owns the trust-signal framing; this segment owns the substance (convention + showcase) | This segment owns the social-proof framing too | Intent attaches at the lowest dominating node: cultivation is the substance and is upstream; using the ecosystem as conversion proof is a downstream use, so it cascades to `marketing-site` (which already points at examples for the same purpose). |
| Component variant | Content artifact | Behavioral skill; standalone variant without EARS | Owned artifacts are content and configuration, not behavior; matches the sibling content-artifact segments and keeps linkage uniform. |

## Open Questions & Future Decisions

### Resolved

1. ✅ Node name / prefix: `extensions` / `EXT`.
2. ✅ Discovery by open convention (canonical topic `linked-intent-development` + link-back) plus a curated `EXTENSIONS.md`.
3. ✅ `EXTENSIONS.md` owned by this segment though it sits at the repository root.
4. ✅ Content-artifact variant.
5. ✅ Social-proof framing owned by `marketing-site`; substance owned here.

### Deferred

1. **Outward-face sub-HLD.** If outward-facing intent accretes — more examples-as-a-node, case studies, community programs — promote `marketing-site` + `extensions` under an "ecosystem" sub-HLD via the re-parent lifecycle event. Not warranted at two children.
2. **Strength of the link-back marker.** Today the convention asks only for a README link to the core repository. Whether to define a firmer marker (a badge, a metadata key) is deferred until the convention sees real use.
3. **`EXTENSIONS.md` inclusion bar and hygiene.** The editorial criteria for listing, and how unmaintained entries are pruned, start light and firm up from experience.
4. **How authors request listing.** Whether listing is by PR, by issue, or by maintainer discovery via the topic is deferred; the convention makes a project discoverable regardless of listing.

## References

- `docs/high-level-design.md` — Goal 2 (minimum-system); Architecture § 3 (Distribution / third-party ecosystem); *Minimum-system discipline — the why*; Non-Goal *Not a factory*.
- `docs/intent/marketing-site/marketing-site-design.md` — consumes the ecosystem as a trust signal (the social-proof framing).
- `EXTENSIONS.md` — owned artifact.
- `docs/intent/extensions/extensions-specs.md` — EARS specs for this component.
- `EtaCassiopeia/lid-tooling` — canonical real-world example extension.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — LLD structure this document follows.
