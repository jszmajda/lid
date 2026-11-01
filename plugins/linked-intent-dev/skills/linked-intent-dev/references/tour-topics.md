# The LID tour: topics

These are the topics a person can go further into, during the tour or at any other time. Each one stands on its own, so it explains every term it uses.

## How to give a topic

- Give only the topic the person asked for, in one message, with its heading as a bold line. Each topic is written in your voice, so give it as written.
- End the message by listing the other topics by title.
- Let the person explore without pulling them back. While they keep asking questions or reading topics, end only the first answer in that stretch with a one-line reminder of what's waiting (for example, "The photo app questions are still open whenever you're ready"). Leave it out of later answers, and bring the full question back when they say done, ask for work, or answer it. When you do bring it back, repeat a short question in full; for a long draft, give a one-line pointer to it and repeat its question. If nothing was paused, go back to what they were doing.
- A question about the topic gets a short answer. A request for work ends the topic.
- When the person asks how one part of LID works, outside the tour, answer in two to four plain sentences drawn from the matching topic, then offer the full topic by its title.

<!-- tour:topics -->

## How the levels close in on what you meant
<!-- anchor: narrowing -->

Picture every program that could satisfy your request as a dot in a large field. A short request leaves most of the field open, and I pick one dot from it, often close to what you meant but not exactly it. Each level of LID draws a ring around the dots you'd accept. The high-level design (HLD) draws a wide ring, a low-level design (LLD) draws a smaller ring inside it, and the one-line requirements (EARS) draw the tightest ring, with the tests holding it in place, until what's left inside is the solution you meant:

```text
  ·    ·     ·    ·     ·    ·     ·    ·
     ╭─ HLD ──────────────────────╮   ·
  ·  │ ·    ╭─ LLD ────────╮    · │
     │   ·  │  ╭─ EARS ─╮  │ ·    │  ·
  ·  │      │  │   ●    │  │      │
     │ ·    │  ╰────────╯  │   ·  │  ·
  ·  │   ·  ╰──────────────╯ ·    │
     ╰────────────────────────────╯   ·
  ·    ·     ·    ·     ·    ·     ·    ·

  ●  the solution you meant
```

LID calls this narrowing. The documents are those rings, saved, and their real job is to rule out the solutions you didn't mean. When you change your mind, you move a ring by editing a document, and the solution I build moves with it. Without written levels, the only record of the rings is the conversation that produced the code, and later changes start from whatever the code happens to do instead of from what you meant.

Tenets, the one-line leanings in a high-level design, draw a ring ahead of time, for choices nobody has thought of yet.

More detail: the "Narrowing the Latent Space" section of LID's high-level design, https://github.com/jszmajda/lid/blob/main/docs/high-level-design.md

## One big design, or a tree of smaller ones
<!-- anchor: design-tree -->

LID's designs form a tree. The high-level design (HLD) is the root and says why the project exists. Low-level designs (LLDs) are the leaves, and each one owns the requirements for one part of the project. Most projects need only one HLD over a few LLDs. When one part grows deep enough that its own parts share decisions a parent document should hold, that part gets a design in the middle of the tree, with smaller designs beneath it:

```text
HLD       a subscription app
├── LLD       free trial
├── LLD       billing
└── sub-HLD   accounts
    ├── LLD       sign-in
    └── LLD       profiles
```

LID calls that middle design a sub-HLD. "HLD" and "LLD" are roles by position in the tree, not two different kinds of document. A sub-HLD has to carry real shared intent. If all it would hold is a list of its children, the parts stay as separate LLDs instead.

A long LLD isn't automatically a problem. Choose the tree's shape by what a part holds, not by how long its document is:

- A concern that spans many parts and has its own decisions, such as security or monitoring, gets its own design.
- Categories within one part, such as its error rules or its performance rules, stay in that part's LLD as groups of requirements.

The tree also shapes requirement IDs: an ID starts with the path through the tree to its LLD, so the ID alone shows where a requirement lives.

More detail: the section of the workflow skill on low-level designs, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md

## Writing down which way to lean
<!-- anchor: tenets -->

A tenet is a one-line tie-breaker in the high-level design. It says which way to lean when a choice could reasonably go either way and no requirement settles it. Many of the choices I meet later in a project are like that.

LID checks a candidate tenet in this order:

1. **Its opposite has to be reasonable.** A real tenet's opposite is a choice another project could make. "Write good code" fails, because nobody would choose the opposite, so it settles nothing.
2. **It has to be a lean, not a rule.** Something phrased as "when X happens, do Y" is really a requirement, so it goes in the requirements instead.
3. **It stays one line.** Any instructions for applying it belong in the project's workflow guidance, not in the tenet.

Tenets are listed in order of priority, so when two pull against each other, the higher one wins. A project usually has a few, not a long list. A tenet says which way to lean, a requirement says what to do, and an entry in a design's Decisions table records what was already chosen.

When we write a high-level design together, I ask you about the few leanings that matter most, and you decide which ones become tenets.

More detail: the Tenets section of LID's HLD template, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/references/hld-template.md

## Recording why a choice went one way
<!-- anchor: decisions -->

When you settle a design choice, you can record it in one of these ways. The test looks at the design as it will stand once it's built, not at how hard the choice was.

- **Nothing**, when the choice will look obvious to anyone reading the finished design.
- **A row in the design's Decisions table**, when a reader would wonder "why this?" and a line answers it. The row also records the alternatives you turned down and why.
- **A decision doc**, a short standalone document laid out under headings like these:

  ```text
  Context · What the choice turns on · Options · Selection
  ```

  These are rare. I offer one only when a reader would keep questioning the choice without the full trade-offs, and other parts of the design are about to be built around it. I write one only if you accept.

A long debate doesn't earn a decision doc on its own. If the choice reads as obvious once it's built, a row or nothing is enough. Some models tend to offer decision docs more often than needed, and if I'm one of them, I tell you when I offer one.

More detail: LID's decision-doc template, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/references/decision-doc-template.md

## Writing documents a newcomer can read on their own
<!-- anchor: read-cold -->

Every LID document is written as if its author knew only what the project means today, and nothing of the conversation that produced it. LID calls this writing to be read cold. The next agent to read the document starts with no memory of your sessions, so anything the document doesn't say is lost.

When I draft or revise a document, I read each line asking whether that author would have written it. These kinds of line fail:

- lines that tell the story of how the design changed ("we originally planned…");
- lines whose meaning depends on the conversation ("as discussed");
- answers to questions only an earlier conversation raised.

The reasons behind a choice stay, along with the alternatives that were considered. Those belong in the design's Decisions table rather than scattered through the text. Git keeps the history of how things changed, so the documents don't need to keep it.

The same test applies to where knowledge goes. Something a fresh agent would need to build the project correctly belongs in the documents. Something about you, such as how you like to work, belongs in my memory.

More detail: the rules for every phase in the workflow skill, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md

## Where product documents such as PRDs fit
<!-- anchor: product-documents -->

Many projects have no product document at all, especially when one person leads both the product and the engineering. When a project does have one, such as a product requirements document (PRD) or a PRFAQ, it often comes first, and it feeds the high-level design. Its problem, its users, and its measures of success go into the high-level design's own sections, written for the project at hand. Most of what the product document sets out to say ends up there, in a form I can build from directly.

The high-level design is the root of truth for what the project is. Once it exists, the project's intent flows down from it.

Sometimes it's worth keeping the product document as its own layer, for example when a product team owns it and the high-level design has to follow it. Then it can live in the project above the high-level design, with the design tracing back to it. Either way, the high-level design stays the root of the design tree. LID doesn't say where product documents live. The project's instruction file says where they are, so I read them.

More detail: "Product documents and the HLD" in LID's high-level design, https://github.com/jszmajda/lid/blob/main/docs/high-level-design.md. For a conversation about your own setup, ask `/lid-coach`.

## How a change in a design reaches the code
<!-- anchor: cascade -->

When you change something at one level, I update the levels below it in the same session, so they still agree with it. Change a low-level design, and the requirements, tests, and code under it follow. LID calls this a cascade, and I do it as part of the change.

A project divides into segments. A segment is one low-level design plus the requirements, tests, and code that refer to its requirement IDs. Inside one segment, I carry a change down freely. When a change would reach a different segment, I stop and ask you first. Designs differ in how complete they are, and pushing a change unchecked into a part that's described less fully can spread mistakes into it.

A change to the high-level design reaches every segment, so I work through them one at a time, pausing at each. I also warn you before I touch files you're in the middle of editing. If I notice two documents disagreeing, I tell you rather than quietly picking one.

More detail: "Cascade discipline" in the workflow skill, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md

## Fixing a bug the same way
<!-- anchor: bug-fixes -->

A bug fix follows the same chain as any other change. I first find where the behavior parted from what was meant, which is usually one of these:

- what was meant needs to change, so the design or requirement changes first;
- the requirement already says the right thing, and the code doesn't follow it;
- nobody ever wrote the intent down, so it gets written now.

From there the fix is carried down to the tests and code like any change, so the requirement, the test that holds it, and the fix stay linked.

Patching the code directly skips that, and the reason the code should behave this way stays unwritten, so it can be lost again. I warn you if you ask for a direct patch, and then I do what you asked.

More detail: "Bug fixes" in the workflow skill, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md

## Who checks each level
<!-- anchor: who-checks -->

Every level gets checked before the next begins, and you choose who checks it:

- **You**, reading the level at its pause. This is the default, because only you know what you meant.
- **A blind reader**, a fresh agent that sees only the documents and never our conversation, so it can't inherit my blind spots. It's good at finding requirements that could be read more than one way.
- **A delegated inspector**, an agent that reviews a level in your place and brings you a short list of what it found. You decide what to do with each item. A clean report means it found no problem, which isn't proof there's none.
- **Your team's usual review**, such as a pull-request review, for the parts that review actually reads.

You choose in conversation, and nothing needs configuring. Handing off the checking changes who reads at a pause, never how many pauses there are. Handing it off never hands off the questions only you can answer: when a requirement could mean two different things, it still comes to you, because only you know which one you meant. You can choose to let even that go, but only by saying so specifically ("Deciding how much to check yourself" covers how).

More detail: "Specification and inspection instruments" in the workflow skill, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md

## Deciding how much to check yourself
<!-- anchor: how-much-to-check -->

Some moments need your judgment: a requirement that could mean two things, a choice no document settles, a design that works against one of your project's tenets (the one-line leanings in its high-level design), a change that can't easily be undone, and others. By default I bring all of them to you.

You can choose to check less, based on the risk as you see it. A tool that handles money might need everything checked, while a game made for fun might need very little. Say it in your own words, in conversation or as a line in your instruction file. You can also limit it to one piece of work, such as a research prototype, without it carrying over to the product that prototype later joins.

Requirements that could mean two things, and changes that can't easily be undone, need you to say so specifically. A general wish for fewer interruptions doesn't cover them. If I notice a pattern, such as you approving every question about carrying a change into another part of the project without reading it, I can point that out and ask whether you want it treated as your preference. I won't start doing that on my own.

More detail: "Judgment still reaches the user" in the workflow skill, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md

## When your model is known to miss something
<!-- anchor: capability-flags -->

LID's guidance runs on whatever model you pair it with, and most of it works on any model. A few kinds of judgment depend on the model, though, and on how much reasoning it's allowed. LID tests models on those kinds of judgment. When tests show a model reliably missing one, LID records a capability flag for that model at that reasoning setting.

When a flag applies to the model I'm running on, I still do my best work, then bring that one kind of judgment to you and ask you to check it yourself. For example: "Please check this design against your project's tenets yourself; models configured like me are known to miss conflicts like that." I say so once and plainly, and I don't hedge the rest of my work. A tendency is milder: a lean in something you already decide, which I mention once so you can weigh it.

I find my own entry by the model name your tool reports, not by what I believe I am. If I have no entry of my own, I take the entry of a tested earlier or smaller model in my family. If nothing fits, I treat every flag as applying, because bringing you a check you didn't need costs less than skipping a check you did need.

More detail: LID's capability-flag list, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/references/capability-flags.md

## Using LID for the whole project or one part
<!-- anchor: modes -->

A project runs LID in one of two modes, written in the `## LID` block of its instruction file:

- **Full**: the whole project follows LID. This is the default, and the usual choice for a new project.
- **Scoped**: only a part of a larger project follows LID, such as one service or package, while the rest is left alone. You list the paths in scope, and a change outside them doesn't involve LID. Changes stop at the scope's edge rather than carrying across it.

Both modes go through the same levels and the same pauses. They differ only in how much of the project they cover. In Scoped mode, the high-level design can mark sections as "not yet specified" instead of filling them in.

You can change modes later with `/update-lid`. Moving from Scoped to Full gathers the scoped documents into the usual places, and I ask you to settle any overlaps between them.

LID's files live in the project itself. If you want them private, add them to `.gitignore`.

More detail: "Adoption modes" in LID's high-level design, https://github.com/jszmajda/lid/blob/main/docs/high-level-design.md

## Starting LID on code that already exists
<!-- anchor: existing-code -->

`/map-codebase` starts LID on a codebase that was built without it. It's thorough, so it costs a lot to run, and it only runs when you ask for it.

Its first question asks what to map, and your answer also sets the mode: the whole project means Full mode, and a list of specific parts means Scoped mode. I then read every file in scope and propose a few different ways to divide the code into parts. You choose one, and decide how fine the parts should be. You correct the result before anything is written. Then I draft a skeleton high-level design, low-level designs, and requirements that describe what the code does today, not what it should do. My guesses about why the code was written a certain way are marked as guesses for you to confirm later. I stop after each stage, and stopping leaves nothing written.

When it finishes, the project is set up for LID, and you fill in the skeletons through ordinary changes.

For a small codebase you know well, you don't need it: start with an ordinary change and write the designs as you go.

More detail: the map-codebase skill, https://github.com/jszmajda/lid/blob/main/plugins/arrow-maintenance/skills/map-codebase/SKILL.md

## Finding your way around a large project
<!-- anchor: large-projects -->

`/arrow-maintenance` is for projects too big to hold in one session. It keeps an index, `docs/arrows/index.yaml`, with a short entry for each part of the project:

```yaml
free-trial:
  status: AUDITED
  detail: free-trial.md
  next: "Add the trial-reminder email."
```

Each entry points to that part's design, its requirements, and its state, so I can find the right part without reading everything.

It also checks that the project's documents, tests, and code still match:

- documents that point to things that no longer exist;
- requirements with no test;
- code that refers to a requirement that isn't there;
- documents that no longer match the code.

It fixes what has one clear answer and brings the rest to you. Renaming or moving a part rewrites its requirement IDs everywhere they appear, in one change.

The plugin is installed by default but optional to use, and a small project doesn't need the index. When the index is present, I use it quietly as I work, and running `/arrow-maintenance` asks for a full check. It never blocks your work the way a build check would.

More detail: the arrow-maintenance skill, https://github.com/jszmajda/lid/blob/main/plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md

## Keeping a project's LID setup up to date
<!-- anchor: setup-current -->

`/update-lid` looks at the project and does what it needs:

- set LID up on a new project;
- add LID's instructions to an existing instruction file;
- bring a project forward after LID releases changes to its conventions;
- tidy up details that have drifted;
- switch modes;
- or tell you nothing needs doing.

It always shows you what it plans to change, and waits for your go-ahead before changing anything. Afterward it tells you what it changed.

The project's instruction file records which version of LID's conventions the project follows. When LID's conventions move to a new version, `/update-lid` walks the project forward through each release's migration steps in order. A small release that asks nothing of a project doesn't start a walk. If the project records a newer version than the LID you have installed, `/update-lid` asks you to update LID first and changes nothing.

Running it twice in a row changes nothing the second time, so it's safe to run whenever you want to check.

More detail: the update-lid skill, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/update-lid/SKILL.md

## Getting advice on how you're using LID
<!-- anchor: coach -->

`/lid-coach` reads your project's LID documents (the high-level design, the low-level designs, the requirements, and a sample of the code) and writes a short report on how you're using LID. The report starts with what's working, then lists ways to use LID more effectively, in priority order, without grades. It also reads your designs the way a newcomer would, looking for what's unclear.

It doesn't change anything. When a finding needs a fix, it points you to the tool for it, such as `/update-lid` for setup or `/arrow-maintenance` for a structural check.

You can also ask it how to use LID in a particular situation, such as working with product documents, a project spread across several repositories, or deciding between Full and Scoped. It runs only when you ask for it.

More detail: the lid-coach skill, https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/lid-coach/SKILL.md

## Fewer pauses, in your own words (an experiment)
<!-- anchor: fewer-pauses -->

The review-depth experiment lets you say which design levels you want to review one at a time, and have the rest come to you as one combined review. You write it in your own words, in your instruction file or in conversation, for example: "Review depth: I review through LLD; below that, consolidate to one review." There, "through LLD" means you review the high-level design and the low-level designs (LLDs) one at a time. LID writes no configuration for it.

Every level is still written and checked. Only the number of times you're stopped changes. Some things still come to you right away:

- a requirement that could mean two things, in an area you've said you care about;
- anything LID's capability flags record my model as known to miss;
- and work that turns out to touch the high-level design or cross into another part of the project, which goes back to a pause at every level.

It's opt-in, part of the `lid-experimental` plugin, and may change or be removed between releases.

More detail: the review-depth skill, https://github.com/jszmajda/lid/blob/main/plugins/lid-experimental/skills/review-depth/SKILL.md

## Checking requirements and code against each other, blind (an experiment)
<!-- anchor: blind-check -->

The blind-differential experiment checks whether a requirement and its code still say the same thing. It starts two fresh agents, each beginning with none of our conversation. One writes code from the requirement alone. The other reads the code, with its references to the requirement removed, and writes the requirement it thinks the code meets. Comparing the two shows where the requirement and the code have drifted apart: behavior the code has that the requirement never states, or a requirement the code doesn't fully meet.

Its findings are advice for you to judge. When it finds drift, the suggested fix is to settle with you what was meant first, then change the design, the requirement, the tests, and the code, in that order.

It needs the index that `/arrow-maintenance` keeps, runs only under Claude Code, and costs real API spend, so it starts by asking which requirements you want checked. It's opt-in, part of the `lid-experimental` plugin, and may change or be removed between releases.

More detail: the bidirectional-differential skill, https://github.com/jszmajda/lid/blob/main/plugins/lid-experimental/skills/bidirectional-differential/SKILL.md

## Using LID on tools without plugins
<!-- anchor: no-plugins -->

LID's plugins run on Claude Code and Cursor. Other coding tools read the project's instruction file, `AGENTS.md`, which carries a short core of LID's instructions. The full workflow comes in a separate file, `docs/lid/workflow.md`, which LID generates from its workflow skill at each release.

That file is added only when a tool without plugins needs it. The instruction file tells such a tool to offer it once, and on a yes, the tool fetches it from the LID release your project records. A no is recorded so the offer isn't repeated. Projects on plugin hosts don't need the file, and skipping it keeps them on the plugins' upgrade path: a copied file stays at the release it was copied from until someone updates it, with `/update-lid` or by copying the newer version.

Edit LID's instructions upstream or in `AGENTS.md`, never in the copied file. Some tools can be told to load `AGENTS.md` every time, which makes them more reliable at following it. The setup guide explains how, for each tool.

More detail: LID's setup guide, https://github.com/jszmajda/lid/blob/main/docs/setup.md

<!-- /tour:topics -->
