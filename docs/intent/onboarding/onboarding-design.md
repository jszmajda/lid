---
parent: high-level-design
prefix: ONB
---

# Sub-HLD: Onboarding

## Context and Design Philosophy

Onboarding is the material people read or watch to understand LID: the marketing site and the repository README, the newcomer tour, the examples of what people have built, and the recording that shows one change moving through every level. LID is quick to adopt and needs no deep understanding to start, so most people learn it by using it, in conversation with their agent. This subtree serves the other way in: a person who would rather come and read, whether they are deciding to try LID or want to understand it better after months of use. It is the realization of HLD Goal 5 (*Make LID legible to people who learn it by reading, from first contact to deeper understanding*), and it is load-bearing intent like any other part of the tree: what it claims must stay true of the system it describes.

This document is a **sub-HLD**: an HLD-shaped node in LID's design tree that owns no EARS of its own. It holds what its children share: the reader they are written for, the rule that their claims trace to the HLD, the voice they speak in, the one example they all use, and how the site presents content another segment owns. Its children are:

- **`marketing-site`** (`docs/intent/onboarding/marketing-site/marketing-site-design.md`, segment `ONB-SITE`): the website and the repository README.
- **`tour`** (`docs/intent/onboarding/tour/tour-design.md`, segment `ONB-TOUR`): the short introduction LID offers inside the agent, and its topics.
- **`cascade-recording`** (`docs/intent/onboarding/cascade-recording/cascade-recording-design.md`, segment `ONB-REC`): the repository tool that records the home page's cascade demo.

The node roots the `ONB` prefix, so `grep ONB` gathers the whole subtree. Terms like *arrow*, *segment*, *cascade*, and *sub-HLD* are defined in the HLD's Glossary.

## The Reader

Every child is written for a person who has chosen to learn LID by reading. That person may not have adopted LID yet, may be setting it up, or may have used it for a long time and want to know why it works the way it does. What they share is the medium: they read a page, a document, or a short message, or watch a recording, rather than learning from the workflow's stops as they work.

The children are written so a reader at any depth gets something from them. The first screen of any page assumes no vocabulary, and depth sits a click or a scroll further on. Learning by use, through the workflow's stops and the coach's reviews, is the skills' work, not this subtree's; where the two meet, such as the tour's offer inside the agent, the tour owns what is read and the workflow skill owns when it is offered.

## Claims Trace to the HLD

Everything in this subtree makes claims about LID, and each claim traces to the HLD section or LLD that makes it true. A child that says LID does something LID does not do fails Goal 5 as cleanly as a broken test fails its spec. Each child records, in its own design doc, where the claims it makes trace. When the HLD or a plugin LLD changes, the children whose claims depend on it are reviewed in the same change.

## Voice

**Share, not oversell.** Onboarding speaks like a colleague who has found an approach that works for them and is showing it to someone, not like a vendor. It names LID's price as plainly as its payoff, and it never claims that agent-written code is trustworthy because LID was used: it claims only what the mechanism does.

**Show the thing before naming it.** The reader has not learned LID's words. A term earns its place only after the thing it names has been shown; first mentions are plain English, and words that describe LID to its maintainers stay out.

**Each child keeps its own word rules where its medium needs them.** The tour has rules for text read inside an agent; the site has a copy register for its pages. Both sit under these two.

## The Shared Example: a 30-Day Free Trial

The children follow one example, so a reader who meets LID in more than one place meets one story. It is a request most people have met as users of software, small enough to trace briefly at each level, and vague in a way a careful reader notices at once. The example belongs here because three children depend on it:

- **The request:** "Give new users a 30-day free trial."
- **What it leaves to the agent:** when the trial starts, what happens when it ends, whether someone can start a second trial, and when exactly day 30 ends.
- **The boundary it follows down:** when day 30 ends, and in whose time zone. Someone who signs up at 11 p.m. on the 1st, in Tokyo, is about to find out.
- **The tenet that settles it:** "Customer delight over perfect cost management: when a choice could go either way, we lean toward the customer." Its opposite is a choice another business could reasonably make, which is what makes it a tenet; it rules out ending trials at the server's midnight.
- **The settled line:** the trial ends 720 hours after signup, so everyone gets exactly 30 days.

The tour walks this example through its opening steps; the home page traces it through its explainers to one requirement, its test, and its code; the cascade recording drives a real agent through a change to it in a small project whose files match the home page. Each child decides how much of the example it shows and in what form. When any of the five points above changes, all three children change in the same change.

## Content the Site Presents

The site is onboarding's web surface, and it presents content that other segments own. The `tour` segment's steps and topics are the first case: the site's build reads them from the tour's own files and renders them as a page. The rule for every such case is the same: **the owning segment owns the words and their claims; the site owns the route, the navigation, the layout, and the look.** The site never edits or paraphrases content it presents, and its own copy register does not apply to that content. Material for practitioners, when it arrives, follows the same rule from wherever it lives.

## Component Map

| Leaf | Segment | Concern |
|---|---|---|
| `marketing-site` | `ONB-SITE` | The site's pages, navigation, look, and build, and the repository README. Owns `docs/intent/onboarding/marketing-site/marketing-site-specs.md`. |
| `tour` | `ONB-TOUR` | The introduction offered inside the agent: the offer, the five steps, the topics, and the notes. Owns `docs/intent/onboarding/tour/tour-specs.md`. |
| `cascade-recording` | `ONB-REC` | The tool that records the home page's cascade demo in a trial project that matches the page. Owns `docs/intent/onboarding/cascade-recording/cascade-recording-specs.md`. |

## Cascade

- **HLD Goal 5, or the tenets *Friendly over exacting when introducing LID* and *Introduce LID fast*, change:** every child is reviewed.
- **The shared example changes:** all three children change together (see above).
- **A plugin LLD changes a capability onboarding describes:** the children whose claims mention it are reviewed in the same change.
- **Within a child:** cascade runs free inside the child's segment; a change that reaches a sibling pauses, as everywhere in LID.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| How to group the material people read to learn LID | A sub-HLD, `onboarding`, over `marketing-site`, `tour`, and `cascade-recording` | Keep them as flat siblings under the HLD; name the group "documentation" | The three share a reader, a voice, an example, and a claims rule, which flat siblings could only coordinate sideways. "Documentation" suggests reference material to look things up in; this subtree introduces and explains, starting from a reader who knows nothing. |
| Where the shared example lives | Here, in the parent | In the `tour` segment, with the others following it | A decision lives at the lowest node whose subtree contains everything it affects, and the example affects all three children. |
| Which example | A 30-day free trial | The marketing site's account-scoped sign-in; a tax holding period; a split bill | Most people have met a free trial as users. The question of when day 30 ends, and in whose time zone, is concrete and has a real cost when guessed wrong. The site's sign-in example traces cleanly but has no natural boundary question to show a pause catching. |
| Who owns content the site shows | The segment that owns its substance; the site owns its presentation | The site owns all text it shows | One source per piece of content: the tour stays the same inside the agent and on the page, and future guides can live beside the skills that carry them. |

## References

- `docs/high-level-design.md`: Goal 5; Tenets (*Friendly over exacting when introducing LID*, *Introduce LID fast*, *Name for any English reader*, *Intent attaches at the lowest node that dominates it*); Key Design Decisions (*Introducing LID inside the agent*, *Content artifacts*).
- The three child design docs listed in *Component Map*.
