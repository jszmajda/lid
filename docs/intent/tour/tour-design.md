---
parent: high-level-design
prefix: TOUR
---

# LLD: Newcomer Tour

## Context and Design Philosophy

The tour is the short introduction LID offers a person the first time they meet it inside their coding agent: when they set LID up in a project, or when they start work in a project that already runs it (HLD § Key Design Decisions, *Introducing LID inside the agent*; Goal 5). This segment owns how the offer is presented and answered, what the tour says, the topics a person can go further into afterward, the short notes it adds during the person's first change, how it looks on each host, how the person's answer is recorded, and the content of the marketing site's tour page. *When* the offer is made is the HLD's rule. Each route that makes the offer carries that rule as a requirement in its own segment, and points to this segment's files for everything else.

The person meeting LID this way is usually in the middle of something. They asked their agent to build a thing, or they opened a ticket in a project their team runs on LID. They are about to be asked LID-specific questions, or held at a pause they did not expect. These principles shape the tour around that moment:

- **Friendly over exacting.** The agent talks like a colleague who is showing someone how they work and wants them to understand it (HLD tenet *Friendly over exacting when introducing LID*). It answers what the person asks, leaves room for their questions, and treats the tour's limits (a screen, a few sentences) as guides rather than measurements.
- **Fast over tailored.** The tour uses one built-in example rather than researching the person's own project, and keeps its length to a few short messages (HLD tenet *Introduce LID fast*). A person joining a project often does not yet understand that project well enough for it to make a clear example, and researching it would cost turns and tokens before the person learns anything.
- **Never in the way.** The offer sits at the top of the message the person would have received anyway. Carrying on with the work declines it, and nothing waits for an answer to it.
- **Easy to understand on first read.** The tour is written in full, connected sentences that explain each idea instead of compressing it, so a person reading quickly in the middle of other work understands it the first time.
- **Show first, then give the term, where that costs nothing.** The person is ready to act, so the tour can introduce the words for the levels of the chain early. It still shows each idea in the example before giving it a term, and it explains what a pause is for at the moment the first real pause happens.
- **Color carries meaning.** Every visual device marks something the person needs to tell apart: which level of the chain they are looking at, what changed in a requirement, where a pause is. Decoration that marks nothing is left out.
- **Honest about the cost.** The tour says what LID asks of the person (more reading before code exists) alongside what it gives them, in the marketing site's register: no claim the HLD does not support.
- **It describes the workflow as the workflow currently behaves.** The tour is downstream of the `linked-intent-dev` workflow. When the workflow changes how or when it pauses, this segment's content is reviewed in the same change. The tour leans on what a pause is *for* (seeing what the agent thinks you meant before anything is built on it) more than on how often pauses happen, so less of it goes stale when pacing changes.

Terms like *arrow*, *cascade*, and *segment* are defined in the HLD's Glossary.

## Component Variant

Content artifact (`HLD → LLD → EARS → content + assets`), as for `marketing-site` and `extensions`, with one addition: the offer, the answers, and the notes are behavior the agent performs. The segment's artifacts are three shipped files in the workflow skill's references:

- **`tour-offer.md`**: who sees the offer, the offer card's wording, how each answer is handled, the wording of the memory record, and the links to the other two files for hosts that must fetch them. It is short, and it is listed among the workflow skill's references, so the release step assembles it into the workflow doc for hosts without a plugin system.
- **`tour.md`**: the tour itself (the five steps), the notes for the first change, the built-in example, the visual markers, and the notes' frame. It is not listed, so it stays out of the workflow doc.
- **`tour-topics.md`**: the topics a person can go further into, one section per topic. It is not listed either.

The marketing site builds its tour page from the steps in `tour.md` and the topics in `tour-topics.md`. The `marketing-site` segment owns that page, and this segment owns what it says.

Each route that makes the offer carries a short passage in its own skill: a check of whether the person may be new, and a pointer to `tour-offer.md`. The workflow skill also notices when a person asks for the tour or a topic at any other time. Those passages, and the requirements behind them, belong to the routes' own segments.

Verification:

- **Scenario evals** in the eval suites of the skills that make the offer (the workflow skill, `update-lid`, `map-codebase`). They check that the card appears at the top of the first message on each route, that the route's own message still follows in the same message, that carrying on proceeds as before, that saying yes to the card starts the tour and then returns to the pending question, and that asking for the tour later gives it. Their assertions carry `TOUR-*` spec IDs under the plugin's eval-metadata convention, so the coverage audit counts them toward this segment. The evals also confirm that the three files exist.
- **Content check.** Most of this segment's requirements describe fixed text: the steps, the example, the words, the looks. A blind reader given only the three tour files and this segment's specs checks each of those requirements against the files. Reading the files is a stronger test of static text than running scenarios, and it is the content's test in the tests-first sense: the specs exist before the files, and the check fails until the files meet them.
- **Claim review.** Every claim in the card and the tour traces to an HLD section (*What the tour claims* below), every claim in a topic traces to the HLD or to the design doc of the segment that owns the capability (*Going further* below), and the review that keeps the marketing site coherent with the HLD covers the tour the same way.
- **Packaging checks** keep every line of the three files within the plugin's line limit, and confirm that `tour.md` and `tour-topics.md` stay out of the workflow skill's reference list, and so out of the assembled workflow doc.
- **The site build** confirms that the tour page builds from `tour.md` and `tour-topics.md`.
- **Rendering by inspection.** When the tour's visual devices change, a person checks them on the hosts listed under *How it looks*, because no automated check sees what a host draws.

## Offering the tour

### When and where the offer appears

The HLD sets the timing: before the first LID-specific choice or pause the person meets. Each route realizes that as one requirement in its own segment. On every route the offer sits at the top of the route's first message to the person, whatever that message asks:

| Route | Who | Its first message usually |
|---|---|---|
| `/linked-intent-dev` on a project with no LID setup (Phase 1 bootstrap) | the person setting LID up | asks the mode question |
| `/update-lid` on a project with no LID directives (full bootstrap, or appending directives to an existing instruction file) | the person setting LID up | proposes the setup, before anything is written |
| `/map-codebase`, unless its own check of the project sends the person to `/arrow-maintenance` | the person setting LID up on existing code | warns that mapping is costly and asks its first question (whether to keep or replace existing docs, or whether to map the whole project or only parts of it), and so comes before the sweep |
| The start of a change in a project that already has LID directives | a person joining the project | presents the phase's first output, or asks its first question |

In Scoped mode, when the workflow has to ask whether a change is in scope, the offer waits until the answer puts the change in scope, so a person is never offered the tour on a change LID does not handle. Anything a route does before its first message, such as creating a directory, is unaffected. `/map-codebase` always counts as setting LID up, even on a project that already has some LID docs.

`update-lid` makes no offer when another skill invoked it with the mode already decided (as `map-codebase` does at the end of its run), when the workflow's Phase 1 applies its bootstrap branch inline (the workflow makes the offer), or on a project that already has LID directives (reconciling conventions, a version walk, a mode change). `map-codebase` makes no offer when its check sends the person to `/arrow-maintenance`, as it does for a project that already has full LID docs, or when the `linked-intent-dev` skill is not installed.

The offer appears at most once in a session, whichever route reaches it first. Only the agent talking with the person shows it. A subagent that the agent dispatches never does. In a run with nobody answering, such as an automated eval, the card appears and the run carries on, as it would for any person who carried on.

### Who sees it

The route's passage makes a cheap first check: whether the memory the harness already places in the agent's context shows that this person has met LID before. The tour's own record is the usual sign, and other memories that show the person working with LID count too. The check does not search for anything. If the memory shows it, there is no offer. Otherwise the agent reads `tour-offer.md`, which applies these conditions:

- **Setting up.** The person sees the offer unless the harness's per-person memory shows that they have met LID before. Without such memory, they see it at every setup. Setup is rare for any one person, and carrying on declines it.
- **Joining.** The person sees the offer only when the harness keeps per-person memory that the agent may write (*Recording the answer*), and that memory does not show them meeting LID before. Without such memory, nothing is offered, because nothing could stop the offer from returning at every change (HLD § *Harness capabilities*).

In Scoped mode, a change outside the declared scope does not engage the workflow, so it does not reach the offer. The offer comes on the person's first change inside the scope.

### The card

The offer is a card at the top of the message:

1. **A bold heading** that fits the moment. When the person is setting LID up it asks whether they are new to LID. When they are joining it says that this project uses LID.
2. **A short paragraph** that explains, in full sentences, what LID does. The person says what they want. Before any code exists, the agent writes that down in layers (why the project exists, how each part works, and one-line requirements that a test can check), shows each layer to the person, and waits for them, so a wrong guess is caught while it is still a sentence. Every test and every piece of code points back to the requirement it serves, so when something changes later, the agent can find every piece connected to it, even across many files. The paragraph runs to about five sentences and uses no LID term other than "LID" itself.
3. **A line with the two ways in**: the word **tour**, which starts the walk-through in the agent, and the link to the marketing site's tour page.

The route's own message follows the card unchanged, introduced as the way to keep moving ("Or, to keep moving: …"). The card's exact wording lives in `tour-offer.md` and is held to *Words* below.

### The answer

The person answers the way they would answer a colleague, and the agent reads the answer the same way:

- **A yes**, meaning "tour", "yes" to the heading's question, or any other request for the introduction, starts the tour (*What the tour says*). When the tour ends, the agent returns the person to the route (*Returning to the route* below).
- **A reply that could answer either the card or the route's own question**, such as a bare "yes" when the route has asked a yes-or-no question too, gets a short question back asking which they meant, as a colleague would ask.
- **A question about the tour or about LID** ("how long is it?", "what does Scoped mean?", "how does cascade work?") gets a short answer, with an offer of the matching topic where there is one. The offer stays open, and nothing is recorded yet.
- **A no** declines: "not now", saying they already know LID, or carrying on with the work (answering the route's question, approving a draft, or anything else that continues). The route proceeds as it would have without the card, with one addition: a short clause about the record (*Recording the answer*).
- **Asking for the tour or a topic later**, in this session or any other, starts it then (*Asking at any time* below).

### Returning to the route

The person has taken the tour once they have seen its first step, and the tour ends when they leave it: by saying done or stop, by asking for work, or by answering the route after step 5 or after a topic. When the tour or a topic ends, the agent brings the person back to where the route paused. When the pending item is a short question, such as the mode or scope question, the agent asks it again in full. When it is a long draft, the agent gives a one-line pointer to the draft and repeats only the question that goes with it. A new request the person made during the tour is handled as their reply to the route.

**Letting the person explore.** While the person keeps exploring, by asking questions or reading topics, the agent doesn't keep pulling them back. The first answer in that stretch ends with a one-line reminder of what's waiting ("The photo app questions are still open whenever you're ready"). Later answers in the same stretch leave it out. The full pending question comes back when the person says done, asks for work, or answers it.

### Asking at any time

A person can ask for the tour, or for a topic, whenever they want, for example to remind themselves how part of LID works. The workflow skill notices these requests (its description covers them) and reads `tour.md` or the matching section of `tour-topics.md`. A question about how one part of LID works gets a short answer and the offer of the matching topic. That is the only part of the tour that is always loaded on a plugin host: a clause in the workflow skill's description. In a session where the workflow skill is already loaded, which is most sessions in a LID project, answering costs only the tour file. When the person asked outside a route, *Returning to the route* has nothing to return to, and the agent goes back to whatever they were doing.

## What the tour says

### The opening

The opening has five steps. Each step is one message of about one terminal screen (roughly 30 lines at 80 columns, as a guide); step 4, which carries the example's requirement, test, code, and search result, may run to about two. Each step starts with a bold title line that says where the person is in the tour and what the step covers ("Tour 2 of 5: writing the design down"). Steps 1 to 4 end with two choices in bold, written as plain text rather than through a host's structured-question tool: **next**, with a few words saying what the next step covers, and **done**, with a few words saying where it returns the person.

The person can talk to the tour the way they would talk to a colleague. A question about the step, or about LID, gets a short answer, followed by the step's choices again. "Done", "stop", or a request for work ends the tour, and the agent returns the person to the route (*Returning to the route*). Anything else, such as "ok" or "go on", the agent reads for its meaning, as a person would.

1. **The question and the levels.** The step opens with the question the marketing site opens with: how do you know your agent built what you meant? It explains the problem in plain words: when a request leaves something unsaid, the agent fills the gap with a plausible guess; what it builds can be close to what the person meant without being what they meant; and when the person comes back in a later session, the agent there does not remember why the code was built the way it was. It then shows the levels LID writes intent down in, with a sentence on what each holds: the high-level design (why the project exists and what it must get right), the low-level designs (how each part works), EARS requirements (one line each, in a fixed pattern most people have seen, such as "When a user signs in, the system shall…"), tests written before the code and run first, so each test is shown to fail until the code exists, which proves it measures something; and the code. Only after showing the levels does the step say that intent flows down them in one direction, from the broad idea to the code. It ends by showing that the design levels can branch. A small project has one high-level design over a few low-level designs. In a larger one, a part with enough depth gets its own mid-level design (a sub-HLD) with smaller designs beneath it, and that can repeat as deep as the project needs. A short tree drawing shows this before the term is used.
2. **Writing the design down.** The step takes one deliberately vague request (*The built-in example* below) and lists the decisions it hands to the agent without saying so. It picks the last of them, a question about where a boundary falls, and shows how the designs settle it: a line of the high-level design states the intent, the agent's first draft of the low-level design contains its plausible guess about the boundary, and at the pause after that draft the person corrects it, shown as a before-and-after change. The low-level design now pins the boundary exactly. The step then explains what a pause is for: the workflow stops after each level and shows the person what the agent thinks they meant, before anything is built on it. When it matches, the person says go. When it does not, they correct it, and the correction is written into the document, so a later session starts from the person's words instead of from the guess. Most of the person's attention in LID goes here, to reading and correcting the designs.
3. **Tenets.** A tenet is a one-line tie-breaker in the high-level design for decisions nobody has thought of yet: it says which way to lean when a choice could reasonably go either way. The step explains how a tenet differs from a principle with the test LID uses: a real tenet's opposite is a choice another project could reasonably make, while a statement whose opposite is absurd settles nothing. It shows one of each, then shows a tenet for the example (*The built-in example*) and how that tenet would have settled the boundary question before anyone asked it.
4. **The rest of the loop.** From the settled design, the agent writes the requirements, the tests, and the code. The step follows the example the rest of the way down, with a short excerpt at each level: the requirement line, with its ID explained in one sentence before the ID is used; a test, written before the code and run first to show it fails, that refers to the ID; and the code that refers to the same ID. Above each excerpt, a one-line chain of the five levels shows where the example is, with that level in bold. The step then explains what the IDs are for. When a requirement changes later, the agent searches for its ID to find every test and every piece of code that depends on it, even when they are spread across many files in a large codebase, so related pieces do not get missed. That is a large part of why a LID project stays easy to change over time. The step shows what that search returns for the example, written out in `tour.md` and labelled as such, so the step never searches the person's project. It explains that this part of the work is often handed to the agent, with a fresh reviewing agent that never saw the conversation checking it. That reviewer looks for places where a requirement could be read more than one way, which is how assumptions nobody stated come to light before they turn into surprises in the code. The person's work here shifts to reviewing and spot-checking. It ends with what the person stays in charge of: they can skip a pause, going on without reviewing it (the next pause still comes), or skip a level, leaving that document out. Either way the agent tells them what that risks and then does what they asked.
5. **What LID gives you, what it costs, and where to go next.** This step is one message. What the person gets: a change made once in a design flows down through the requirements, tests, and code; the agent finds everything a change touches; and over time the documents become what the person works in, while the agent builds the code from them. The checks cover what has been written down, and nothing else. What it costs: more reading before any code exists. The step then lists the tools LID offers, with a line on when each is used: `/linked-intent-dev` for every change (it usually starts on its own), `/update-lid` to set a project up or bring its LID setup up to date, `/map-codebase` to start LID on an existing codebase, `/arrow-maintenance` for finding your way around and checking a large project, `/lid-coach` for advice on how the person is using LID, and the opt-in experiments. For a person joining a project, the step says they can type **trace** to see one of the project's own requirements traced the same way. The step then lists a few of the topics by their plain-word titles and offers to list the rest (*Going further*), and returns the person to the route, with the pending question repeated. The person's next reply can be "trace", a topic, or an answer to the route.

When the person types **trace**, the agent picks a requirement ID that both a test and code refer to, searches for it, and shows the results in its own message. If no requirement in the project has both, it says so in one sentence. Answering the route instead of typing **trace** means no.

### Going further

When the opening ends, the person can go further into topics on LID's other capabilities. Step 5 lists them. The person picks one, and the agent reads that topic's section of `tour-topics.md`. The message that presents a topic ends by listing the topics again, so the person can pick another one or carry on. Whether it also mentions the pending question follows *Letting the person explore*. A person can also ask for a topic at any time (*Asking at any time*).

Each topic is about one or two terminal screens, under the same rules as the opening (*Words*, *How it looks*), and it stands on its own: it explains every term it uses, because a person may read it without having seen the opening. It says what the capability is for and when a person would reach for it, then points to the skill or document that holds its detail, with a link to LID's repository on GitHub. That document is also where the topic's claims trace: to the HLD, or to the design doc of the segment that owns the capability. A topic explains a capability. How-to guides for applying LID to a particular situation, such as product-authored PRDs or a project spread across several repositories, belong to the written guides in issue #54.

The topics are listed under plain-word titles, and each topic introduces LID's term for its subject inside. The starting topics, grouped:

| Group | Topics |
|---|---|
| Why it works | how the levels narrow the possible solutions down to the one you want |
| How the design is organized | the design tree, and when a part gets its own sub-HLD; tenets in more depth; decision docs and Decisions rows; writing documents a newcomer can read without the conversation that produced them; where product documents such as PRDs fit |
| How changes move | cascade, and why it pauses between segments; bug fixes, which follow the same chain |
| How checking works | who checks each level (the person, a blind reader, a delegated inspector, a pull-request review); letting some judgment go; capability flags |
| How much of a project uses LID | Full and Scoped modes |
| Tools for bigger or older projects | `/map-codebase`; the arrow-maintenance overlay and its audits; `/update-lid`; `/lid-coach` |
| Experiments | review depth; the blind differential |
| Tools without a plugin system | the vendored workflow doc |

The topic on narrowing is for a reader who wants the reason behind the method: each level rules out solutions the person would not want, so the documents work like nested rings drawn around a field of possible solutions, closing in on the one the person meant. Changing a document moves a ring, and the agent's solution moves with it. Without written levels, the only record of those rings is the conversation that produced the code, and later changes start from whatever the code happens to do. The topic shows this with a drawing of nested rings over a field of dots. Each ring's label sits in the ring's own line, like a box heading, so the drawing reads as layers rather than as a target. The topic on product documents follows the HLD's *Product documents and the HLD*.

A capability, for this list, is a skill, a command, or an experiment. A change that adds or retires one adds or removes its topic in the same change, and a change to how a capability works reviews its topic.

### Notes during the first change

A person who saw at least the first step of the tour gets a short note the first time each of these happens, for the rest of that session:

- **the first phase stop:** the ways through it: agree, correct, answer a question the agent asked, or skip it, in which case the agent says what skipping risks;
- **the first requirement with an ID:** that the ID is how the agent will find this requirement's test and code when it changes;
- **the first test written before its code:** that it fails on purpose until the code exists;
- **the first edit to an existing higher document that flows down** to lower ones, if one happens;
- **the end of the first change**, when the workflow's final checks pass: a search for one of the change's requirement IDs, with the results shown in the agent's message, as what the agent will find when that requirement changes. When the requirement, its test, or its code is missing because the person skipped that level, the note says so.

Each note appears at most once in the session and runs to about two sentences, plus the search results for the last note. Every note uses the same visual frame, which `tour.md` defines. No note adds a pause, delays the phase's work, or replaces anything the phase presents. A person who declined and later took the tour in the same session gets notes for the moments still ahead. A person who received only the link (*Hosts without a plugin system*) gets no notes, because the notes live in `tour.md`.

### The built-in example

The example is a request most people have met as users of software, small enough to trace briefly at each level, and vague in a way a careful reader notices at once. The tour uses **a 30-day free trial**:

- *The request:* "Give new users a 30-day free trial."
- *Decisions it hands over without saying so:* when the trial starts (at signup, or at first use); what happens when it ends (the account locks, or it is charged); whether someone can start a second trial with a new email address; and when exactly day 30 ends.
- *The boundary question it follows down:* when exactly does day 30 end, and in whose time zone? Someone who signs up at 11 p.m. on the 1st, in Tokyo, is about to find out.
- *The guess, and how a pause catches it (step 2):* the agent's first draft of the low-level design ends the trial at midnight at the end of day 30, in the server's time zone, which quietly takes most of a day from the person in Tokyo. The before-and-after change replaces it with the settled line: the trial ends 720 hours after signup, so everyone gets exactly 30 days.
- *The tenet (step 3):* "The same for everyone: where a rule could work out differently for users in different places, lean toward the version that treats them all alike." Its opposite, following each user's local calendar and customs, is a choice another product could reasonably make (a calendar app might), which is what makes it a tenet. With it in the high-level design, the agent would have given everyone exactly 720 hours without being asked, because ending at the server's midnight gives people in different time zones different amounts of time. For contrast, "write good code" is a statement whose opposite nobody would choose, so it settles nothing.
- *The rest of the chain (step 4):* the requirement line restates the settled boundary with an ID; a test refers to that ID; and so does the code that ends the trial. The test and code are written in TypeScript.

The example's excerpts at each level, its IDs, test, code, and search result are written out in `tour.md`, so the tour never depends on reading or searching the person's project.

### What the tour claims

Each claim in the card, the opening, and the notes traces to one of these sections:

| Claim | HLD section |
|---|---|
| The chain of five levels, and that intent flows down it | Architecture § 1, Methodology |
| The design levels can branch into a tree, with sub-HLDs between the HLD and the LLDs | Architecture § 1, Methodology (*The design layer is a tree*) |
| A request leaves decisions to the agent, which fills them with plausible guesses | Approach: Narrowing the Latent Space |
| The next session does not remember why the code is the way it is | Problem |
| Each level is shown to the person before the next begins, and the person can correct it | Approach: Narrowing the Latent Space (*every phase is inspected*); Tenets |
| A correction is written into the document, so the next session has it | Tenets (*Docs carry current intent, written to be read cold*) |
| Tests are written before the code and run first, so each is shown to fail until the code exists | Approach: Tests-first as Intent Preloading; Phase 5 of the workflow (`LID-CORE`) |
| The person can skip a pause or a level, with a warning | Tenets (*The user is always right — with warning*) |
| When a requirement changes, the agent searches for its ID to find every test and piece of code that depends on it, even across many files | Approach: Linkage-based Intent Tracking (navigation) |
| The person can run the same search to check what was built against what was asked for | Approach: Linkage-based Intent Tracking (attestation) |
| Before tests are written, a fresh agent that sees only the requirements looks for lines that could mean more than one thing, and brings them to the person | Approach: Narrowing the Latent Space (instruments; ambiguity always goes to the human) |
| A tenet is a one-line tie-breaker for decisions nobody has thought of yet, and a real tenet's opposite is a reasonable choice for another project | Approach: Narrowing the Latent Space (tenets); Tenets |
| The later levels are often handed to the agent, with a fresh reviewing agent checking for requirements that could be read more than one way, and the person's work there shifts to reviewing and spot-checking | Approach: Narrowing the Latent Space (instruments, and how deeply the person inspects is their choice) |
| The tools LID offers, and when each is used | Architecture § 2, Plugins; for what each tool does, that tool's own design doc |
| The checks cover what has been written down, and nothing else | Approach: Linkage-based Intent Tracking; Non-Goals (*Not a linter or validator*) |
| A change made at a higher level flows down to the lower ones | Architecture § 1, Methodology (*Cascade*) |
| The documents are what the person changes; the agent builds the code from them | Problem; LID as a Structure for Intent; Tenets (*Intent leads; code is compiled output*) |
| It costs more reading before code exists | Approach: Narrowing the Latent Space (*every phase is inspected*, and how deeply is the person's choice) |

A claim that traces to none of these sections is removed, or a section it traces to is added here, before the tour ships.

### Words

The tour's text means the card, the opening, the notes, and the topics. It is spoken by the agent, in the first person, as itself ("I'll show you each level"):

- Full, connected sentences that explain each idea instead of compressing it, joined with words like "because" and "so" rather than set down as clipped fragments, at about a grade 8–11 reading level measured on the prose (code and requirement excerpts aside). The test is whether a person reading quickly, in the middle of other work, understands it the first time.
- *LID's own terms* are the words for the five levels (as acronyms or in plain words), "sub-HLD", "pause", "ID", "LID" itself, and the words for LID's other mechanisms (segment, cascade, overlay, mode, and the like). Ordinary words such as requirement, test, design, and code are not LID terms. In the card, the opening, and the notes, LID's own terms are limited to the level words, "sub-HLD", "pause", "ID", and "LID", each explained in plain words where it first appears (HLD tenet *Speak the project's language*). A topic may use the terms for the capability it explains, each explained in plain words where it first appears in that topic.
- Say the thing instead of pointing back at it. A sentence does not leave out words the reader has to rebuild from an earlier sentence ("sometimes the answer is 'not quite'" leaves the reader to work out *not quite what*). Restating the key words usually costs only a few more of them.
- Only things that act are given human verbs: the agent, a person, a team. A session, a file, or a project does not remember, know, or decide. "When you come back in a later session, the agent there won't remember why" rather than "the next session won't remember why".
- A new kind of document is introduced with a short example of what it looks like. EARS is introduced with a pattern most people have seen, such as "When a user signs in, the system shall…".
- A structure is shown before it is described or given a term. The tour shows the levels before it says intent flows down them, and shows the tree before it uses "sub-HLD".
- Step 1 opens with a question, not a claim.
- It hedges the way a practitioner does ("usually", "most of the time"), never "you must".
- No colloquial idiom, slang, memes, or jokes (HLD tenet *Name for any English reader*). Plain figurative verbs that any reader follows, such as "flows down" and "points back", are fine. The tour's interest comes from the example, the reveal of the decisions a short request hides, and seeing the search return all three pieces.
- Each sentence starts with its idea. No lead-in announces an idea before stating it ("Here's the short version", "The important part is", "One thing to know"), and no trailing clause rates it ("which is the point").
- Plain verbs for referring to things: a test *points to* or *refers to* its requirement, and a page *says which* version it shows. *Name* is not used as a verb for referring, stating, or labelling. It is a writerly habit that many engineers, and many readers whose first language is not English, do not read easily.
- None of these constructions: "isn't X — it's Y" pivots; runs of short maxims; announced counts that package what follows ("three things to know"); "load-bearing"; "lands" in its figurative sense. Counts that describe structure ("the chain of five levels") are fine.
- No maintainer's first-person stories. The agent describes LID, not its author.

Code and requirement excerpts inside fences are exempt from these rules.

## How it looks

Hosts draw the agent's messages differently. Claude Code's terminal renders Markdown with its own colors. Cursor, the VS Code extension, and the desktop app render it as rich text. Hosts without a plugin system vary. The model cannot set a color directly, and the HLD adds no host detection, so the tour uses only devices that read correctly everywhere and look better where the host does more:

- **The card is a quoted block** (a Markdown blockquote) with a bold heading that starts with one emoji. A quote bar wraps cleanly on a narrow terminal, where a drawn box breaks as soon as a line wraps. A blockquote counts as flowing text, not as a box.
- **Bold** marks emphasis, each step's title line (with its place in the tour, such as "Tour 2 of 5"), the choices at the end of each step, and the current level in the chain line. Italics and strikethrough carry no meaning, because some terminals do not draw them.
- **The chain line is plain text**, short enough never to wrap (`HLD → LLD → **EARS** → Tests → Code`), so its bold renders.
- **Fenced code supplies color.** A `diff` fence shows the requirement before and after (red and green where the host colors it). Language-tagged fences show the example's test and code with the host's syntax colors.
- **Drawings stay inside `text` fences**, at most 60 characters wide, so they keep their alignment and do not wrap on a tablet held upright. The tree in step 1 is a drawing. Outside a fence, a proportional font breaks a drawing.
- **Emoji are limited** to those Unicode draws two cells wide by default (East Asian Width *W*), from Unicode 13.0 or earlier, and chosen so their shape and color read clearly at terminal size. One that looks like a plain circle or square at a glance marks nothing. Variation-selector forms (such as ⚙️ and ⏸️), joined sequences, and emoji added after Unicode 13.0 are not used: terminals and harnesses disagree about their width, which shifts the text after them. An emoji appears only at the start of a line of flowing text, never inside a table, a drawn box, or a fenced drawing, and always beside a word that carries the meaning.
- **No raw terminal escape codes**, and nothing that relies on the host showing command output, which many harnesses hide or collapse. When the tour runs a search, the agent shows the results in its own message.
- **One marker per level**, the same in every step, note, and topic. A marker always appears with its level's word, so a person who meets it in a topic first still knows what it means. The word can appear without the marker, as it does in the chain line and the tree. Where a marker is an emoji, it follows the emoji rules above. `tour.md` defines the markers and the notes' frame.

The tour's visual devices are the card's form, the chain line, the markers, the notes' frame, the fences, and the drawings. When a change alters any of them, a person checks the result by eye before the change ships, on Claude Code's terminal (including a terminal that does not draw italics, at the width of a tablet held upright), on one rich-text host, and on the site's tour page, and records the check in the pull request.

## The tour page

The marketing site presents the tour's five steps and its topics as a page, and the page is one of the site's top-level pages. It serves a person who would rather read the introduction outside the agent, and it is the simplest route for hosts without a plugin system. The card links to it.

- The site builds the page from the steps in `tour.md` and the topics in `tour-topics.md`, at the same commit, so the page and the in-agent tour have one source. The page does not edit or paraphrase them.
- The page leaves out the parts that only make sense inside the agent: the **next** and **done** choices, the **trace** offer, the notes, and the instructions to the agent. `tour.md` and `tour-topics.md` mark those parts so the build can leave them out.
- The topics follow the steps as sections, with a short list of their titles at the top of that part of the page. Each topic's section has a stable anchor, so a link can point to one topic.
- The page says which LID version its content comes from (the version in the plugin manifest at the commit the site was built from). Users install LID from `main`, which the site is built from, so the page and an up-to-date install match. An older install may differ, and the tour leans on the parts of LID that hold across releases, so the difference rarely matters.
- The tour's text follows this segment's *Words* rules, not the site's own copy rules, so the site's rules for its other pages do not apply to it.
- The `marketing-site` segment owns the page's route, navigation, layout, and theme, including how fenced code is colored on the web.

## Recording the answer

The agent records one fact in the harness's per-person memory: that this person has met the LID tour, and whether they took it or declined it. The record uses the wording `tour-offer.md` fixes, so the check on a later route can recognize it. Nothing is recorded in the project's files (HLD § *Harness capabilities*).

- **The record is written at the next natural stopping point**: for a person who took the tour, when the tour ends; for a person who declined, when the route's current step finishes. A harness that asks before memory writes then asks at a moment when the person is already pausing, never between their answer and what they asked for. If the session ends first, nothing is recorded, and the person may see the offer again.
- **A person whose record says they declined** and who later takes the tour has the record changed to say they took it.
- The agent records only where the harness's memory is one it may write in this session, meaning that the harness's own memory instructions in the agent's context allow saving facts about the user. If the harness asks before memory writes, its rule is followed.
- After a write succeeds, the agent mentions it in one short clause in that message. If there is no such memory, or the write fails or is refused, the agent says nothing about remembering.
- The record's reach is the memory's reach. Where memory is kept per project, as in Claude Code, a person may see the offer once in each project, and carrying on declines it.

## Hosts without a plugin system

On these hosts the workflow reaches the agent through the vendored workflow doc (HLD § Distribution). The workflow skill's route passages sit in the skill's own instructions, and `tour-offer.md` is in its reference list, so the release step's assembly carries both into the workflow doc: the agent there has the check, the card, and the answer handling without fetching anything. `tour.md` and `tour-topics.md` are not in the list, so the tour's content stays out of what those hosts load on every change.

`tour-offer.md` carries the links to the other two files: the repository's raw-file address for each, at the release given in the workflow doc's header. When the person asks for the tour, the agent fetches `tour.md` from its link. When they ask for a topic, it fetches `tour-topics.md`. Where the agent cannot get `tour.md` (it has no way to fetch, the fetch fails, or the fetch is refused), it points the person to the marketing site's tour page, records that they took the tour, and carries on without waiting. That person gets no notes. Where it cannot get `tour-topics.md`, it points the person to the topics on the tour page, and the record is unchanged.

On these hosts a person sets LID up by hand from `docs/setup.md`, with no setup skill to make the offer. So `docs/setup.md` links to the tour page for the person doing the setup, and the in-agent offer on these hosts is the one at the start of a person's change, under the same memory condition as on plugin hosts.

## Cascade

Upstream:

- **HLD.** Goal 5, the tenets *Friendly over exacting when introducing LID* and *Introduce LID fast*, and the Key Design Decisions *Introducing LID inside the agent* and *Harness capabilities* are this segment's direct sources. A change to any of them reviews this LLD.
- **The workflow (`LID-CORE`).** The tour describes how the workflow behaves. A change to when or how the workflow pauses, what a level holds, or how a change flows down reviews `tour.md` and the notes in the same change.
- **The segments whose capabilities the topics describe.** A change that adds, retires, or changes a capability reviews its topic in the same change. In `docs/arrows/index.yaml`, `tour` is blocked by `linked-intent-dev`, `arrow-maintenance`, and `lid-experimental`.

Downstream:

- **`marketing-site`** builds its tour page from `tour.md` and `tour-topics.md`, and may mention the tour on its paths for new users once the tour ships. In the index, `tour` blocks `marketing-site`.

Cascade notes into segments that point at this one without depending on its specs. Each owns its own requirements for *when*, derived from the HLD, and a passage that points to `tour-offer.md`, so a change to the tour's wording or answer handling does not reach them:

- **`core` (`LID-CORE`)**: the offer in Phase 1 bootstrap and at the start of a joining person's change; the notes during the first change; noticing requests for the tour or a topic at any time, through a clause in the workflow skill's description.
- **`update-lid` (`LID-UPDATE`)**: the offer on projects without LID directives, and none when the caller already decided the mode or the workflow applies the bootstrap inline.
- **`map-codebase` (`SCALE-MAP`)**: the offer at its first message, once its check confirms a mapping will run. It reaches `tour-offer.md` by loading the `linked-intent-dev` skill, whose references hold it.
- **`packaging-checks`**: `tour.md` and `tour-topics.md` stay out of the workflow skill's reference list.
- **`project-structure`**: `docs/setup.md` links to the tour page for a person setting LID up by hand on a host without a plugin system.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| How the offer is made | A card at the top of the route's first message, with the route's own message below it as the way to keep moving; carrying on declines | A separate turn that waits for yes or no; a one-line offer above the route's question | A separate turn stalls any session nobody is answering (headless runs, evals, dispatched subagents), turns an ignored offer into a recorded decline nobody gave, and adds a turn (*Introduce LID fast*). A single line is easy to miss. The card is prominent, gives a newcomer the context the route's first question needs, and never holds up the work. |
| Which message carries the card | The route's first message to the person, whatever it asks | The message that asks one particular question (the mode question, the scope question) | A route can ask something LID-specific before the question this segment might expect, such as `/map-codebase`'s warning about cost or its question about existing docs. The first message is the one the HLD's timing rule (before the first LID-specific choice) reliably satisfies. |
| How answers are read | Like a colleague reads them: yes in any form starts the tour, a question gets an answer and leaves the offer open, a no or carrying on declines | Only the literal word "tour" starts it, and every other reply declines | *Friendly over exacting when introducing LID.* A newcomer who replies "yes" to "New to LID?" means yes. A literal rule would record a decline from someone who asked how long the tour takes. |
| Where the parts live | `tour-offer.md` (who sees it, the card, answers, the record, the links) assembled into the workflow doc; `tour.md` (steps, notes, example, markers) and `tour-topics.md` kept out of it; a check and a pointer in each route's skill | Everything in one file; the card's wording copied into each route's skill | Hosts without a plugin system need the card without a fetch, and should not load the tour's content on every change, which takes separate files. Copying the card into three skills would give it three homes that drift. |
| Who owns *when* | Each route's own segment, as one requirement derived from the HLD | This segment | The routes would otherwise depend on this segment while it depends on the workflow it describes, a loop the arrow index cannot order. A route that only points at a file is untouched by changes to what the file says. |
| Asking for the tour at any time | The workflow skill's description covers requests for the tour or a topic, and its body points to the tour files | A small skill of its own for the tour; tour only when offered, with the site page for everything else | People forget how a system like LID works when they are not driving it every day, so the tour is worth reaching any time. Absorbing the request into the workflow skill adds no command or skill (Goal 2): only a clause in its description is always loaded, and in most LID sessions the skill is already loaded. A skill of its own would add surface the existing skill can carry. |
| Where the content ships | The workflow skill's references, with hosts without a plugin system fetching the tour files by release links when the person asks, or reading the site's page | A copy vendored into each project beside the workflow doc; plugin hosts only | One copy, at one version. A vendored copy stays in every repository for good to serve each person once, and pins to the release that wrote it. Plugin hosts only would leave cross-tool users, and anyone joining a project on those hosts, with no tour. |
| A web page for the tour | A top-level page on the marketing site, built from `tour.md` and `tour-topics.md`, linked from the card | Agent-only; a separately written page; a page reachable only from the Start page and the card | Some people would rather read outside the agent, and the page is the simplest route for hosts without a plugin system. Building it from the tour files keeps one source. Making it a top-level page puts the introduction where any visitor finds it. |
| Going further | Short topics on LID's other capabilities in `tour-topics.md`, listed when the opening ends and read one at a time | The topics inside `tour.md`; no topics, with the tour linking to the written guides of issue #54 | A person who has met LID wants to know what else it can do, and the moment after the opening is when they are most curious. A separate file means the agent reads only the topic asked for, and a host without a plugin system fetches topics only when one is asked for. Putting the topics in `tour.md` would load every topic into the context of everyone who takes only the opening. The written guides teach how to apply LID to particular situations, which is a different reader at a different moment. |
| Topic titles | Plain words, with LID's term introduced inside the topic | LID's own terms as titles | The titles appear in step 5, where the opening's limit on LID terms applies, and a plain title tells a newcomer what the topic is about. |
| Example source | A built-in example | Researching the person's own project for an example; the person's own request at setup | A built-in example costs no research turns or tokens (*Introduce LID fast*), always contains a real open question, and works the same for a joining person who does not yet know the project. An example people already half-know makes LID clearer than one drawn from the person's own domain. The person's own request may contain no open question to show, and joining has no request to use at all. |
| Which example | A 30-day free trial | The marketing site's account-scoped sign-in; a tax holding period; a split bill | Most people have met a free trial as users. The question of when day 30 ends, and in whose time zone, is concrete and has a real cost when guessed wrong. The site's sign-in example traces cleanly but has no natural boundary question to show a pause catching. |
| The example's before-and-after | The agent's plausible guess in the low-level design, replaced at the pause by the settled line | A vague line made precise; the correction made at the requirement line | The card promises that a wrong guess is caught while it is still a sentence. Showing a guess being replaced keeps that promise in the example itself, and the low-level design is where a boundary like this is decided. |
| What the IDs are for, in the tour | The agent uses them to find everything a change touches, across many files | The person uses them to check a behavior against its requirement | People rarely search the IDs themselves, while the agent does so on nearly every change. Finding every connected piece when a requirement changes is what keeps a large project easy to change over time. |
| Tenets in the opening | A step of their own, with the defensible-opposite test and an example tenet that settles the example's question | A topic only | Most people know what a principle is, but a tenet is a narrower idea, and it is where a newcomer first states their own leanings in the high-level design. |
| Tools before topics | Step 5 lists LID's skills and commands, with when each is used, before the topics | Topics only; skills left for the person to discover | A newcomer needs to know what tools exist before an open list of topics makes sense. |
| Shape | A five-step opening (the levels; writing the design; tenets; the rest of the loop; what you get and where to go next), plus short notes the first time each workflow moment happens in the same session | A four-step opening that follows the example from design to code in one step; a complete tour before any work; notes only | The person's attention in LID goes mostly to the designs, and the later levels are often handed off, so the design gets its own step and the later levels follow as a second part of the loop. Tenets are an idea most people meet for the first time here, and they need room to be told apart from principles. A complete tour up front loses people who want to get to work. Notes alone leave the first question (the mode question, at setup) unexplained. |
| Pacing | One step per message, each about one terminal screen, with **next** and **done** in plain text, and room for the person's questions | The whole opening in one message; a host's structured-question tool for the choices; strict choices only | People learn more from short steps they move through at their own speed, and a single long message reads like a manual. A structured-question tool is not on every host, and its buttons make the easy answer the likely one. Questions keep the tour a conversation (*Friendly over exacting when introducing LID*). |
| Reminders while the person explores | A one-line reminder of the pending question on the first answer in a stretch of questions or topics, and the full question again when the person says done, asks for work, or answers it | The pending question repeated after every answer and topic | A colleague mentions the waiting work once and then lets you explore. Repeating it after every answer reads as impatience to get back to the work (*Friendly over exacting when introducing LID*). |
| How step 5 ends | One message that lists the topics and returns the person to the route, with **trace** offered to a joining person | A message that waits for an answer about tracing before listing topics | One message keeps the end short and leaves every next move open: the person can trace, pick a topic, or answer the route. |
| Step 4's search result | Written out in `tour.md`, labelled as what the search returns in a project built from the example | A real search during the step | A real search would run against the plugin's own files or the person's project, which costs a tool call and shows paths that mean nothing to the person. Real searches happen where the results are the person's own: the joining person's trace and the note at the end of the first change. |
| How a pause is described | Where the person sees what the agent thinks they meant, before anything is built on it | Where the person catches the agent guessing | Most of what a pause finds is something nobody wrote down, not an agent error. Describing the pause as a comparison, where agreement is a pass, is accurate and suits a person who did not choose LID. |
| How "the documents are what you change" is stated | In plain words, after the example has shown the levels | A short slogan at the opening ("Code is output. Intent is the artifact.") | A slogan points at nothing the person can check. After the example, the same idea points at documents the person has just seen. |
| Tracing one of the joining person's own requirements | Offered in step 5 as the word **trace** | Done by default; not offered | Done by default, it would cost a search and an explanation of an unfamiliar project for everyone (*Introduce LID fast*). Offered, it gives a person who wants the real thing a way to see it. |
| Visual devices | Markdown structure, a quoted card, a plain-text chain line, fenced code for color and drawings, and a limited set of emoji | Raw terminal color codes; a plugin output style; a hook that prints a banner; a box-drawn card; a fenced chain line | Model text reaches the user as Markdown, and raw escape codes show as literal text on several hosts. An output style is specific to Claude Code and changes every response in the session. A hook is a script LID would ship, against *LID runs on the agent, not a runtime*. A drawn box breaks when its lines wrap on a narrow terminal, and bold does not render inside a fence. |
| Where the answer is recorded | The harness's per-person memory only, mentioned in a clause after the write succeeds | A bullet in the instruction file's `## LID` block; asking permission before writing; not recording | The instruction file is shared by everyone on the project, and whether one person has seen the tour is knowledge about that person (HLD § *Harness capabilities*). A separate permission question costs a turn, while mentioning a successful write keeps the record visible without claiming one that failed. Not recording would show the offer again and again. |
| When the record is written | At the next natural stopping point: when the tour ends, or when the route's current step finishes after a decline | Always before replying to the answer | A harness that asks before memory writes would otherwise put its question between the person's answer and what they asked for. |
| What the record holds | Took it, or declined; a later yes changes declined to took it | A third value for "knows LID"; a date | Two values are all a later check needs to decide whether to show the offer, and keeping the record accurate costs nothing when the person changes their mind. |
| How far the record reaches | Whatever the harness's memory reaches, which may mean one offer per project | Writing to user-level settings so one record covers every project | User-level settings are configuration the person manages, and writing there is more intrusive than a memory the harness keeps for the purpose. A repeat offer in a new project costs nothing, because carrying on declines it. |
| Who gets the notes | A person who saw at least the first step, for the rest of that session | Everyone whose record says they took the tour; only a person who finished all five steps | The notes build on the opening. A person who got only the link never saw it, and a person who stopped after the first step has still met the chain. |

## Open Questions & Future Decisions

### Deferred

1. **Asking for the tour on a host without a plugin system, outside a change.** On these hosts the agent reads the workflow doc before a change, so a request for the tour at another moment finds no instructions in context. The site's page serves that person until the instruction-file template carries a pointer, which would be a template change with its own version step.
2. **Hosts beyond those checked.** The visual devices are checked on Claude Code's terminal, one rich-text host, and the site's page. Codex CLI, opencode, Aider, and others draw Markdown in their own ways. Results for them are recorded as they are checked.
3. **Offering again after a large change to LID.** A person who took the tour may meet a release that changes the workflow substantially. Whether that warrants offering a refresher is open.
4. **Consolidated pauses.** When a person has authorized fewer pauses (a warned override, or the `review-depth` experiment), the notes attach to whichever pauses remain. A newcomer is unlikely to start that way, so this is left until it comes up.

## References

- `docs/high-level-design.md`: Goal 5; Tenets (*Friendly over exacting when introducing LID*, *Introduce LID fast*, *Speak the project's language*, *Name for any English reader*, *LID runs on the agent, not a runtime*); Key Design Decisions *Introducing LID inside the agent* and *Harness capabilities: used when present, never required*; Architecture § Distribution.
- `docs/intent/linked-intent-dev/core/core-design.md`: the workflow the tour describes, Phase 1 bootstrap, and the workflow skill's newcomer tour passage.
- `docs/intent/linked-intent-dev/update-lid/update-lid-design.md`: the setup routes and the mode question.
- `docs/intent/arrow-maintenance/map-codebase/map-codebase-design.md`: the brownfield route and its first message.
- `docs/intent/marketing-site/marketing-site-design.md`: the tour page, the register and claim-tracing the tour follows, and the opening question it shares with the site.
- `docs/decisions/workflow-distribution.md`: how hosts without a plugin system receive the workflow.
- `docs/intent/packaging-checks/packaging-checks-design.md`: the workflow-doc assembly.
