# Newcomer Tour Specs

**LLD**: docs/intent/tour/tour-design.md
**Implementing artifacts**:
- plugins/linked-intent-dev/skills/linked-intent-dev/references/tour-offer.md
- plugins/linked-intent-dev/skills/linked-intent-dev/references/tour.md
- plugins/linked-intent-dev/skills/linked-intent-dev/references/tour-topics.md
- the scenario evals carrying `TOUR-*` IDs in the eval suites of the `linked-intent-dev`, `update-lid`, and `map-codebase` skills

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

The tour is content plus behavior the agent performs. The three reference files are the artifact, and per the LID-on-LID linkage inversion this file carries the artifact pointer. When each route makes the offer, and how the workflow skill notices requests for the tour, are specified in the routes' own segments (`LID-CORE`, `LID-UPDATE`, `SCALE-MAP`). This file specifies who sees the offer, what it looks like, how answers are handled, what the tour says, and how the answer is recorded.

Terms used in the lines below:

- A **route** is one of the four ways a person reaches the offer: the workflow's Phase 1 bootstrap of a project with no LID setup; `/update-lid` on a project with no LID directives; `/map-codebase`; and the start of a person's change in a project whose instruction file has LID directives.
- **The tour's text** is the card, the opening, the notes, and the topics. Code and requirement excerpts inside fences are not part of it for the word rules.
- **LID's own terms** are "HLD", "LLD", "EARS", "high-level design", "low-level design", "sub-HLD", "pause", "ID", "LID", and the words for LID's other mechanisms (segment, cascade, overlay, mode, and the like). Ordinary words such as requirement, test, design, and code are not LID terms, even where they also describe a level.
- **Met LID before**: the harness's per-person memory holds the tour's record for this person, or other memories that show this person working with LID.
- **Took the tour**: the person saw the opening's first step. **The tour ends** when the person leaves it: by saying done or stop, by asking for work, or by answering the route after step 5 or after a topic.

---

## Files

- `[x]` **TOUR-001**: The tour SHALL ship as three files in `plugins/linked-intent-dev/skills/linked-intent-dev/references/`: `tour-offer.md`, holding who sees the offer, the offer card, how answers are handled, the wording of the memory record, and the addresses of the other two files; `tour.md`, holding the opening's five steps, the notes for the first change, the built-in example, the visual markers, and the notes' frame; and `tour-topics.md`, holding the topics, one section per topic.
- `[x]` **TOUR-002**: `tour-offer.md` SHALL be listed in the `linked-intent-dev` skill's reference list, so that the release step's assembly includes it in the workflow doc.
- `[x]` **TOUR-003**: `tour.md` and `tour-topics.md` SHALL NOT be listed in the `linked-intent-dev` skill's reference list.
- `[x]` **TOUR-004**: `tour.md` and `tour-topics.md` SHALL mark the parts that only make sense inside the agent (the **next** and **done** choices, the **trace** offer, the notes, and the instructions to the agent), so that the marketing site's build can leave those parts out.
- `[x]` **TOUR-111**: `tour-offer.md` SHALL give the address of `tour.md` and `tour-topics.md` in LID's repository as raw-file links, to be completed with the release given in the workflow doc's header.

## Who sees the offer

- `[x]` **TOUR-005**: When a route reaches its offer while a person is setting LID up, the system SHALL show the offer unless the harness's per-person memory shows that this person has met LID before.
- `[x]` **TOUR-006**: When a route reaches its offer at the start of a person's change in a project that already has LID directives, the system SHALL show the offer only if the harness keeps per-person memory that the agent may write under TOUR-082 and that memory does not show this person meeting LID before.
- `[x]` **TOUR-007**: The check of whether a person has met LID before SHALL use only the memory the harness already places in the agent's context, without searching files or running commands.
- `[x]` **TOUR-008**: The system SHALL show the offer at most once in a session, whichever route reaches it first.
- `[x]` **TOUR-009**: Only the agent conversing with the person SHALL show the offer. A subagent the agent dispatches SHALL NOT show it.

## The offer card

- `[x]` **TOUR-010**: The offer SHALL appear as a card at the top of the route's first message to the person, whatever that message asks.
- `[x]` **TOUR-011**: The message the route would otherwise have sent SHALL follow the card in the same message, unchanged, introduced as the way to keep moving, so that the card never holds up the route, including in a session where nobody answers.
- `[x]` **TOUR-012**: The card SHALL contain, in order: a bold heading suited to the moment (asking whether the person is new to LID when they are setting LID up, or saying that the project uses LID when they are joining it); a short paragraph explaining what LID does; and a line giving the word **tour** for the walk-through in the agent and the link to the marketing site's tour page.
- `[x]` **TOUR-013**: The card's paragraph SHALL explain, in full sentences, that before any code exists the agent writes the person's request down in layers and shows each layer to the person and waits for them, so that a wrong guess can be corrected while it is still a sentence, and that every test and every piece of code points back to the requirement it serves, so that when something changes later the agent can find every piece connected to it.
- `[x]` **TOUR-014**: The card's paragraph SHALL run to about five sentences and SHALL use no LID term other than "LID".
- `[x]` **TOUR-015**: The card SHALL be a Markdown blockquote whose bold heading starts with one emoji.

## Answers

- `[x]` **TOUR-016**: When the person replies "tour" or "yes" to the card, or otherwise asks for the introduction, the system SHALL start the opening.
- `[x]` **TOUR-112**: When a reply could answer either the card or the route's own question, such as a bare "yes" when the route has also asked a yes-or-no question, the system SHALL ask the person in one short question which they meant.
- `[x]` **TOUR-090**: When the person replies to the card with a question about the tour or about LID, the system SHALL answer it briefly, offer the matching topic where there is one, and keep the offer open, recording nothing yet.
- `[x]` **TOUR-018**: When the person says "not now", or carries on with the work (answering the route's question, approving a draft, or any other reply that continues the work), the system SHALL treat the offer as declined.
- `[x]` **TOUR-020**: When the person says they already know LID, the system SHALL treat it as a decline.
- `[x]` **TOUR-019**: When the offer is declined, the route SHALL proceed as it would have without the card, apart from the clause about the record (TOUR-083, TOUR-107).
- `[x]` **TOUR-021**: When a person asks for the tour or one of its topics at any time, the system SHALL give it, whether or not they declined the offer.
- `[x]` **TOUR-017**: When the tour or a topic ends, the system SHALL return the person to where the route paused. When no route was paused, the system SHALL return to whatever the person was doing.
- `[x]` **TOUR-089**: When returning the person to a route, the system SHALL ask a short pending question again in full, and for a long pending draft SHALL give a one-line pointer to the draft and repeat only the question that goes with it.
- `[x]` **TOUR-129**: While the person keeps exploring, by asking questions about LID or reading topics, the system SHALL end only the first answer in that stretch with a one-line reminder of the pending question, and SHALL bring the full pending question back when the person says done, asks for work, or answers it.

## The opening

- `[x]` **TOUR-022**: The opening SHALL consist of five steps, each delivered as one message of about one terminal screen (roughly 30 lines at 80 columns, as a guide), except step 4, which MAY run to about two.
- `[x]` **TOUR-023**: Each of steps 1 to 4 SHALL end with two bold choices, written as plain text and not through a host's structured-question tool: **next**, with a few words saying what the next step covers, and **done**, with a few words saying where it returns the person.
- `[x]` **TOUR-113**: Each step SHALL start with a bold title line that gives the step's place in the tour (such as "Tour 2 of 5") and what the step covers.
- `[x]` **TOUR-024**: When the person asks a question about a step, or about LID, during the tour, the system SHALL answer it briefly and then offer that step's choices again.
- `[x]` **TOUR-025**: When the person replies "done" or "stop", or asks for work to be done, during the tour, the system SHALL end the tour and return the person to the route, handling any request as their reply to the route.
- `[x]` **TOUR-091**: During the tour, the system SHALL read any other reply for its meaning, as a person would, rather than requiring an exact word.
- `[x]` **TOUR-026**: Step 1 SHALL open with the question "how do you know your agent built what you meant?"
- `[x]` **TOUR-027**: Step 1 SHALL explain that when a request leaves something unsaid, the agent fills the gap with a plausible guess, that what it builds can be close to what the person meant without being what they meant, and that when the person comes back in a later session, the agent there does not remember why the code was built the way it was.
- `[x]` **TOUR-028**: Step 1 SHALL show the levels LID writes intent down in (high-level design, low-level designs, EARS requirements, tests, and code), with a sentence on what each holds, introducing EARS with an example of its pattern such as "When a user signs in, the system shall…", and saying that tests are written before the code and run first, so each test is shown to fail until the code exists.
- `[x]` **TOUR-114**: Step 1 SHALL say that intent flows down the levels in one direction only after it has shown the levels.
- `[x]` **TOUR-029**: Step 1 SHALL show, with a short tree drawing that appears before the term "sub-HLD" is used, that the design levels can branch: a larger project gives a part with enough depth its own mid-level design (a sub-HLD) with smaller designs beneath it, as deep as the project needs.
- `[x]` **TOUR-030**: Step 2 SHALL take the built-in example's request and list the decisions it hands to the agent without saying so.
- `[x]` **TOUR-031**: Step 2 SHALL follow the example's boundary question through the designs: a line of the high-level design stating the intent; the agent's first draft of the low-level design, containing its guess about the boundary; and the person's correction at the pause after that draft, shown as a before-and-after change, after which the low-level design pins the boundary exactly.
- `[x]` **TOUR-092**: Step 4 SHALL explain the requirement's ID in one sentence before the ID is first used.
- `[x]` **TOUR-032**: In step 4, a one-line chain of the five levels SHALL appear as plain text above each level's excerpt, with that level in bold.
- `[x]` **TOUR-033**: Step 4 SHALL show the written-out result of searching for the example's requirement ID, labelled as what that search returns in a project built from the example, and presented as what the agent finds when that requirement changes.
- `[x]` **TOUR-093**: Steps 2 and 4 SHALL NOT search the person's project.
- `[x]` **TOUR-034**: Step 2 SHALL explain that the workflow stops after each level to show the person what the agent thinks they meant before anything is built on it, that the person says go when it matches, and that a correction is written into the document so a later session starts from it.
- `[x]` **TOUR-115**: Step 3 SHALL explain that a tenet is a one-line tie-breaker in the high-level design for decisions nobody has thought of yet, saying which way to lean when a choice could reasonably go either way.
- `[x]` **TOUR-116**: Step 3 SHALL explain the difference between a tenet and a statement that settles nothing, using the test that a real tenet's opposite is a choice another project could reasonably make, with one example of each.
- `[x]` **TOUR-117**: Step 3 SHALL show a tenet for the built-in example and how it would have settled the example's boundary question before anyone asked it.
- `[x]` **TOUR-118**: Step 4 SHALL follow the example from the settled design down the rest of the levels with a short excerpt at each: the requirement line with its ID, a test written before the code and run first to show it fails, which refers to the ID, and the code that refers to the same ID.
- `[x]` **TOUR-119**: Step 4 SHALL explain that when a requirement changes, the agent searches for its ID to find every test and every piece of code that depends on it, even when they are spread across many files, so that related pieces are not missed.
- `[x]` **TOUR-120**: Step 4 SHALL explain that the work of the later levels is often handed to the agent, with a fresh reviewing agent that never saw the conversation checking it for requirements that could be read more than one way, so that unstated assumptions come to light before they become surprises in the code, and that the person's work there shifts to reviewing and spot-checking.
- `[x]` **TOUR-035**: Step 4 SHALL explain that the person can skip a pause, going on without reviewing it while the next pause still comes, or skip a level, leaving that document out, and that the agent then says what skipping risks and does what the person asked.
- `[x]` **TOUR-036**: Step 5 SHALL say what the person gets: a change made once in a design flows down through the requirements, tests, and code; the agent finds everything a change touches; over time the documents become what the person works in, while the agent builds the code from them; and the checks cover only what has been written down.
- `[x]` **TOUR-037**: Step 5 SHALL say what LID costs the person: more reading before any code exists.
- `[x]` **TOUR-121**: Step 5 SHALL list the tools LID offers, with a line on when each is used: `/linked-intent-dev`, `/update-lid`, `/map-codebase`, `/arrow-maintenance`, `/lid-coach`, and the opt-in experiments.
- `[x]` **TOUR-038**: When the person is joining a project, step 5 SHALL say they can type **trace** to see one of the project's own requirements traced.
- `[x]` **TOUR-042**: Step 5 SHALL be one message that lists the tools, then a few of the topics by their titles with an offer to list the rest, and then returns the person to the route, with the pending question repeated.
- `[x]` **TOUR-039**: When the person types **trace**, the system SHALL pick a requirement ID that both a test and code refer to, search for it, and show the results in the agent's own message.
- `[x]` **TOUR-040**: If no requirement in the project is referred to by both a test and code, the system SHALL say so in one sentence instead of tracing.
- `[x]` **TOUR-041**: When the person answers the route instead of typing **trace**, the system SHALL treat it as no.

## The built-in example

- `[x]` **TOUR-043**: The example SHALL be the request "Give new users a 30-day free trial."
- `[x]` **TOUR-044**: The example SHALL list these decisions the request hands over without saying so: when the trial starts, what happens when it ends, whether someone can start a second trial with a new email address, and when exactly day 30 ends.
- `[x]` **TOUR-045**: The boundary question the example follows down SHALL be when day 30 ends and in whose time zone.
- `[x]` **TOUR-046**: The agent's first draft of the example's low-level design SHALL contain a plausible guess (the trial ends at midnight at the end of day 30, in the server's time zone), and the before-and-after change SHALL replace it with the settled line: the trial ends 720 hours after signup.
- `[x]` **TOUR-122**: The example's tenet SHALL be "customer delight over perfect cost management" (when a choice could go either way, lean toward the customer), and the statement that settles nothing SHALL be one whose opposite nobody would choose, such as "write good code".
- `[x]` **TOUR-047**: The example's excerpts at each level, its IDs, test, code, and search result SHALL be written out in `tour.md`.
- `[x]` **TOUR-094**: The example's test and code SHALL be written in TypeScript.

## Going further

- `[x]` **TOUR-048**: When the person picks a topic, the system SHALL present only that topic's section of `tour-topics.md`.
- `[x]` **TOUR-049**: The message that presents a topic SHALL end by listing the topics again, and SHALL mention the pending question only as TOUR-129 allows.
- `[x]` **TOUR-050**: Each topic SHALL be about one or two terminal screens and SHALL say what the capability is for and when a person would reach for it.
- `[x]` **TOUR-097**: Each topic SHALL have a title in plain words, and SHALL introduce LID's term for its subject inside the topic.
- `[x]` **TOUR-095**: Each topic SHALL explain every LID term it uses, so that a person who has not seen the opening can follow it.
- `[x]` **TOUR-051**: Each topic SHALL point to the skill or document that holds its detail, with a link to LID's repository on GitHub.
- `[x]` **TOUR-096**: Every claim in a topic SHALL trace to the HLD or to the design doc of the segment that owns the capability.
- `[x]` **TOUR-052**: The topics SHALL cover: how the levels narrow the possible solutions down to the one the person wants; the design tree and when a part gets its own sub-HLD; tenets in more depth; decision docs and Decisions rows; writing documents a newcomer can read without the conversation that produced them; where product documents such as PRDs fit relative to the high-level design; cascade and why it pauses between segments; bug fixes following the same chain; who checks each level; letting some judgment go; capability flags; Full and Scoped modes; `/map-codebase`; the arrow-maintenance overlay and its audits; `/update-lid`; `/lid-coach`; the review-depth experiment; the blind-differential experiment; and the vendored workflow doc.
- `[x]` **TOUR-123**: The topic on narrowing SHALL include a drawing of nested rings over a field of possible solutions, closing in on the solution the person wants, with each ring's label set into the ring's own line, and SHALL explain that changing a document moves a ring.
- `[x]` **TOUR-053**: When a change adds or retires a skill, a command, or an experiment in a LID plugin, the same change SHALL add or remove the matching topic.
- `[x]` **TOUR-098**: When a change alters how a capability that has a topic works, the same change SHALL review that topic.
- `[x]` **TOUR-099**: When a change alters when or how the workflow pauses, what a level holds, or how a change flows down, the same change SHALL review `tour.md`, including the notes.
- `[x]` **TOUR-054**: A topic SHALL explain a capability, and SHALL NOT be a how-to guide for applying LID to a particular situation.

## Notes during the first change

- `[x]` **TOUR-055**: For the rest of a session in which a person saw at least the first step of the tour, the system SHALL add a note the first time each of these happens: the first phase stop; the first requirement with an ID; the first test written before its code; the first edit to an existing higher document that flows down to lower ones; and the end of the first change, when the workflow's final checks pass.
- `[x]` **TOUR-056**: The note at the first phase stop SHALL list the ways through it: agree, correct, answer a question the agent asked, or skip it, in which case the agent says what skipping risks.
- `[x]` **TOUR-100**: The note at the first requirement with an ID SHALL say that the ID is how the agent will find this requirement's test and code when the requirement changes.
- `[x]` **TOUR-101**: The note at the first test written before its code SHALL say that the test fails on purpose until the code exists.
- `[x]` **TOUR-057**: The note at the end of the first change SHALL search for one of the change's requirement IDs and show the results in the agent's own message, as what the agent will find when that requirement changes.
- `[x]` **TOUR-058**: If the requirement, its test, or its code is missing from that search because the person skipped that level, the note SHALL say so.
- `[x]` **TOUR-059**: Each note SHALL appear at most once in a session.
- `[x]` **TOUR-102**: Each note SHALL run to about two sentences, plus the search results for the note at the end of the first change.
- `[x]` **TOUR-103**: Every note SHALL use the same visual frame, defined in `tour.md`.
- `[x]` **TOUR-060**: A note SHALL NOT add a pause, delay a phase's work, or replace anything a phase presents.
- `[x]` **TOUR-104**: When a person who declined takes the tour later in the same session, the system SHALL add notes for the moments still ahead.
- `[x]` **TOUR-061**: The system SHALL NOT add notes for a person who declined the tour and has not taken it since, or for a person who received only the link to the tour page.

## Claims

- `[x]` **TOUR-062**: Each claim in the card, the opening, and the notes SHALL trace to one of the sections listed in the LLD's *What the tour claims* table.
- `[x]` **TOUR-063**: Before the tour ships, a claim that traces to none of those sections SHALL be removed, or the section it traces to SHALL be added to the table.

## Words

- `[x]` **TOUR-064**: The tour's text SHALL be written in full, connected sentences that explain each idea instead of compressing it, at about a grade 8–11 reading level measured on the prose.
- `[x]` **TOUR-124**: The tour's text SHALL be spoken by the agent in the first person, as itself.
- `[x]` **TOUR-125**: The tour's text SHALL state each idea where it is used, instead of leaving out words the reader has to rebuild from an earlier sentence.
- `[x]` **TOUR-126**: The tour's text SHALL give human verbs (remember, know, decide) only to things that act, such as the agent, a person, or a team, and not to a session, a file, or a project.
- `[x]` **TOUR-127**: The tour's text SHALL introduce a new kind of document with a short example of what it looks like.
- `[x]` **TOUR-128**: The tour's text SHALL show a structure before describing it or giving it a term.
- `[x]` **TOUR-065**: In the card, the opening, and the notes, LID's own terms SHALL be limited to the words for the five levels, "sub-HLD", "pause", "ID", and "LID", each explained in plain words where it first appears.
- `[x]` **TOUR-066**: A topic MAY use LID's terms for the capability it explains, and SHALL explain each in plain words where it first appears in that topic.
- `[x]` **TOUR-067**: The tour's text SHALL NOT say "you must".
- `[x]` **TOUR-105**: The tour's text SHALL hedge the way a practitioner does ("usually", "most of the time").
- `[x]` **TOUR-068**: The tour's text SHALL contain no colloquial idiom, slang, memes, or jokes. Plain figurative verbs any reader follows, such as "flows down" and "points back", are allowed.
- `[x]` **TOUR-069**: Each sentence of the tour's text SHALL start with its idea: no lead-in announcing the idea before stating it, and no trailing clause rating it.
- `[x]` **TOUR-070**: The tour's text SHALL NOT use "name" as a verb for referring to, stating, or labelling something.
- `[x]` **TOUR-071**: The tour's text SHALL contain none of these constructions: "isn't X — it's Y" pivots; runs of short maxims; announced counts that package what follows ("three things to know"); "load-bearing"; "lands" in its figurative sense. Counts that describe structure, such as "the chain of five levels", are allowed.
- `[x]` **TOUR-072**: The tour's text SHALL contain no first-person stories from LID's maintainer.

## How it looks

- `[x]` **TOUR-073**: Italics and strikethrough SHALL NOT carry meaning in the tour's text.
- `[x]` **TOUR-074**: A line shown before and after a change SHALL appear in a `diff` fence, and the example's test and code SHALL appear in language-tagged fences.
- `[x]` **TOUR-075**: Drawings, such as the tree in step 1, SHALL appear only inside `text` fences, at no more than 60 characters wide.
- `[x]` **TOUR-076**: Emoji SHALL be limited to characters that Unicode gives East Asian Width *W*, from Unicode 13.0 or earlier, whose shape and color read clearly at terminal size. Variation-selector forms, joined sequences, and emoji added after Unicode 13.0 SHALL NOT be used.
- `[x]` **TOUR-077**: An emoji SHALL appear only at the start of a line of flowing text, beside a word that carries the meaning, and never inside a table, a drawn box, or a fenced drawing. A Markdown blockquote counts as flowing text.
- `[x]` **TOUR-078**: The tour SHALL NOT use raw terminal escape codes, and SHALL NOT rely on the host showing command output. Search results SHALL be shown in the agent's own message.
- `[x]` **TOUR-079**: Each level SHALL have one visual marker, defined in `tour.md` and used the same way in every step, note, and topic. A marker SHALL always appear with its level's word. The word MAY appear without the marker.
- `[x]` **TOUR-080**: When a change alters the tour's visual devices (the card's form, the chain line, the markers, the notes' frame, the fences, or the drawings), a person SHALL check the result by eye before the change ships, on Claude Code's terminal (including a terminal that does not draw italics, at the width of a tablet held upright), on one rich-text host, and on the marketing site's tour page, and SHALL record the check in the pull request.

## Recording the answer

- `[x]` **TOUR-081**: The system SHALL record in the harness's per-person memory that this person has met the LID tour, as "took it" or "declined", using the wording `tour-offer.md` fixes.
- `[x]` **TOUR-083**: When the offer is declined, the system SHALL write the record when the route's current step finishes, and SHALL mention it in that message.
- `[x]` **TOUR-106**: When the person took the tour, the system SHALL write the record when the tour ends, and SHALL mention it in the message where the record is written.
- `[x]` **TOUR-107**: The system SHALL mention a record only after its write succeeds, in one short clause. If there is no such memory, or the write fails or is refused, the system SHALL say nothing about remembering.
- `[x]` **TOUR-082**: The system SHALL write the record only where the harness's own memory instructions in the agent's context allow saving facts about the user, and SHALL follow the harness's rule when it asks before memory writes.
- `[x]` **TOUR-084**: The system SHALL NOT record the person's answer in the project's files.
- `[x]` **TOUR-085**: When a person whose record says "declined" takes the tour, the system SHALL change the record to "took it".

## Hosts without a plugin system

- `[x]` **TOUR-086**: Where the agent follows the vendored workflow doc instead of the `linked-intent-dev` skill, when the person asks for the tour, the system SHALL fetch `tour.md` from the link `tour-offer.md` gives.
- `[x]` **TOUR-087**: Where the agent follows the vendored workflow doc, when the person asks for a topic, the system SHALL fetch `tour-topics.md` from the link `tour-offer.md` gives.
- `[x]` **TOUR-088**: If the agent cannot get `tour.md` (it has no way to fetch, the fetch fails, or the fetch is refused), the system SHALL point the person to the marketing site's tour page.
- `[x]` **TOUR-108**: If the agent cannot get `tour.md`, the system SHALL record that the person took the tour.
- `[x]` **TOUR-109**: If the agent cannot get `tour.md`, the system SHALL continue the route without waiting.
- `[x]` **TOUR-110**: If the agent cannot get `tour-topics.md`, the system SHALL point the person to the topics on the marketing site's tour page and leave the record unchanged.
