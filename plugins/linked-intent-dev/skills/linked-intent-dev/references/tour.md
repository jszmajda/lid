# The LID tour

This file holds the newcomer tour: five short steps, then the notes you add during the person's first change. `tour-offer.md` covers when the tour is offered and how the person's answer is recorded. `tour-topics.md` holds the topics a person can go further into.

## How to give the tour

- **Give one step per message.** Start each message with the step's heading as a bold line, such as **Tour 1 of 5: the question, and the levels**. Then give the step as written, speaking as yourself.
- **Steps 1 to 4 end with two choices,** written as plain text, never through a question or button tool. **next** goes to the following step, and **done** ends the tour. Fill in the words after **done** with where it returns the person, such as "back to setting up" or "back to the export".
- **Read replies the way a colleague would.** A question about the step, or about LID, gets a short answer, followed by the step's choices again. "Done", "stop", or a request for work ends the tour. Read anything else, such as "ok" or "go on", for its meaning.
- **When the tour ends, bring the person back to where you paused.** If you weren't paused on anything, go back to what they were doing. If you paused on a short question, such as the mode question, ask it again in full. If you paused on a long draft, give a one-line pointer to the draft and repeat only its question. A request the person made during the tour is their reply to what you paused on. Record their answer as `tour-offer.md` describes, and mention the record in the message where you write it.
- **Let the person explore without pulling them back.** While they keep asking questions or reading topics, end only the first answer in that stretch with a one-line reminder of what's waiting (for example, "The photo app questions are still open whenever you're ready"). Leave it out of later answers, and bring the full question back when they say done, ask for work, or answer it.
- **Keep the visual devices as written.**
  - Each level has one marker, always shown with its level's word: 🎯 HLD · 📐 LLD · 📋 EARS · ✅ Tests · 💻 Code.
  - The chain line in step 4 is plain text, not a code block, so its bold shows.
  - Don't let italics carry meaning, because some terminals don't draw them.
- **Never search the person's project during steps 1 to 5.** The search results in step 4 are written out here. Real searches happen only for **trace** in step 5 and for the note at the end of the first change.

<!-- tour:steps -->

## Tour 1 of 5: the question, and the levels

How do you know your agent built what you meant?

Usually you find out by using what it built. When your request leaves a detail unsaid, the agent fills that gap with its best guess, so what it builds can be close to what you meant without being exactly what you meant. And when you come back in a later session, the agent there won't remember why the code was built the way it was.

With LID, I write your intent down in levels, from the broad idea to the code. Each level is more specific than the one above it:

- 🎯 **HLD**, the high-level design: why the project exists and what it must get right.
- 📐 **LLD**, a low-level design: how one part of the project works.
- 📋 **EARS** requirements: one line each, in a pattern you've probably seen before, such as "When a user signs in, the system shall show their reading list."
- ✅ **Tests**, written before the code and run first, so you see each one fail for the reason you expect. A test that fails first is one you know really checks something.
- 💻 **Code**, which points back to the requirement it implements.

Intent flows through these levels in one direction, downward. When you change your mind, you change the highest level the change affects, and the change is carried down to the levels below it.

In a small project, one high-level design sits over a few low-level designs. In a larger one, a part with enough depth gets its own design in the middle, with smaller designs beneath it:

```text
HLD       a subscription app
├── LLD       free trial
├── LLD       billing
└── sub-HLD   accounts
    ├── LLD       sign-in
    └── LLD       profiles
```

LID calls that middle design a **sub-HLD**, and the tree can go as deep as the project needs.

<!-- agent-only -->
**next**: how a design gets written down · **done**: back to what we were doing
<!-- /agent-only -->

## Tour 2 of 5: writing the design down

Suppose you ask for this: "Give new users a 30-day free trial." It sounds complete, but it leaves these decisions to the agent:

- when the trial starts: at signup, or the first time they use the app
- what happens when it ends: the account locks, or the card on file is charged
- whether someone can start a second trial with a new email address
- when exactly day 30 ends

The last decision is easy to miss, and someone who signs up at 11 p.m. on the 1st, in Tokyo, will notice how it was made.

🎯 The high-level design states the intent: "New users can try the app free for 30 days before they pay."

After each level, I stop and show you what I think you meant, before anything gets built on top of it. LID calls that a pause. If it matches, you say go. If it doesn't, you correct it, and your correction goes into the document, so when either of us comes back to this later, we start from your words instead of from my guess.

📐 The low-level design for the free trial says how it works. In my first draft, I guessed at the boundary, and at the pause after the draft you'd correct it:

```diff
- The trial ends at midnight at the end of day 30, in the server's time zone.
+ The trial ends 720 hours after signup, so everyone gets exactly 30 days.
```

My guess would have cut the Tokyo signup's trial about 14 hours short, because the server counts day 1 from its own midnight, and 14 hours of that day had already passed when they signed up.

I also look for gaps myself as I draft, asking "what happens when…" questions about the design, so a pause is where we catch what either of us missed.

Usually, most of your attention in LID goes here, to reading the designs and correcting them while they're still a few sentences long.

<!-- agent-only -->
**next**: tenets, which settle questions before anyone asks them · **done**: back to what we were doing
<!-- /agent-only -->

## Tour 3 of 5: tenets

A tenet is a one-line tie-breaker that lives in the high-level design. It tells me which way to lean when a choice could reasonably go either way and nobody has decided it yet. Many of the choices I'll meet later in a project are like that.

Not every principle makes a good tenet. A real tenet's opposite is a choice another project could reasonably make. "Write good code" isn't a tenet, because nobody would choose its opposite, so it settles nothing. "Customer delight over perfect cost management: when a choice could go either way, we lean toward the customer" is a tenet, because another business could reasonably lean the other way and keep its costs as low as it can.

With that tenet in the trial app's high-level design, I'd have leaned toward giving everyone the full 720 hours without being asked, because ending the trial at the server's midnight takes hours away from some customers, depending on where and when they sign up. The tenet settles the day-30 question, and many other questions like it, before anyone thinks to ask them.

When we write a high-level design together, I'll ask you about the few leanings that matter most to you, and we'll write them down as tenets.

<!-- agent-only -->
**next**: how the requirements, tests, and code follow from the design · **done**: back to what we were doing
<!-- /agent-only -->

## Tour 4 of 5: from requirements to code

From the settled design, I write the requirements, then the tests, then the code. This part is often handed to me, and your work here is mostly reviewing and spot-checking.

HLD → LLD → **EARS** → Tests → Code

📋 The requirement states the settled design as one line. Each requirement has an ID, a short label that tests and code can refer to, and this one is `TRIAL-003`:

```text
TRIAL-003: When 720 hours pass after signup, the system shall end the trial.
```

Usually, before any test is written, a fresh agent that sees only the requirements, never our conversation, reads them looking for lines that could mean more than one thing. Any it finds come back to you, because only you know which one you meant. That's how assumptions nobody stated come to light before they turn into surprises in the code.

HLD → LLD → EARS → **Tests** → Code

✅ The test is written before the code and run first, so you can see it fail for the reason you expect. It refers to the requirement's ID:

```ts
// @spec TRIAL-003
it("ends the trial 720 hours after signup", () => {
  const signup = new Date("2026-03-01T14:00:00Z"); // 11 p.m. in Tokyo
  expect(trialEnded(signup, hoursAfter(signup, 719))).toBe(false);
  expect(trialEnded(signup, hoursAfter(signup, 720))).toBe(true);
});
```

HLD → LLD → EARS → Tests → **Code**

💻 The code that ends the trial refers to the same ID:

```ts
// @spec TRIAL-003
export function trialEnded(signup: Date, now: Date): boolean {
  return now.getTime() - signup.getTime() >= 720 * HOUR_MS;
}
```

When the code is done, I check that the tests pass and that every ID in the tests and code points to a real requirement.

The IDs are mostly for me. When a requirement changes, I search for its ID to find every test and every piece of code that depends on it, even when they're spread across many files in a large codebase. In a project built from this example, the search for `TRIAL-003` finds:

```text
docs/intent/trial/trial-specs.md   TRIAL-003: When 720 hours…
tests/trial.test.ts                // @spec TRIAL-003
src/trial.ts                       // @spec TRIAL-003
```

Finding every connected piece this way is a large part of why a LID project stays easy to change over time: related pieces don't get missed, even when nobody remembers where they all are. You can run the same search yourself whenever you want to check.

You stay in charge the whole time. You can skip a pause and keep going without reviewing it, and the next pause still comes. For a single change, you can also tell me to leave out a level, for example the requirements for a quick experiment. That's an exception for that one change rather than a setting, and either way I'll tell you what it risks before I do what you asked.

<!-- agent-only -->
**next**: what LID gives you, and where to go from here · **done**: back to what we were doing
<!-- /agent-only -->

## Tour 5 of 5: what you get, and where to go from here

When you change your mind, you change it once, in a design, and the change is carried down through the requirements, tests, and code, because I find everything that change touches by its IDs. Over time, the documents become what you work in, and I build the code from them. My checks only cover what has been written down, so anything left unsaid is still ours to catch together.

LID costs you more reading before any code exists, mostly at the pauses.

LID has a few tools, and you'll mostly use the first one without thinking about it:

- `/linked-intent-dev`: every change goes through it. On tools with plugins, it usually starts on its own when you ask for a change.
- `/update-lid`: sets a project up, or brings its LID setup up to date after LID changes. It shows you what it will change before it changes anything.
- `/map-codebase`: starts LID on an existing codebase by reading every file and mapping what's already there. It's thorough, so it costs a lot to run, and it only runs when you ask for it.
- `/arrow-maintenance`: helps you find your way around a project too big to hold in one session, and checks that its documents, tests, and code still agree.
- `/lid-coach`: reviews how you're using LID and suggests improvements, without changing anything. It runs when you ask for it.
- Experiments: optional extras you can install to try newer ideas. They may change, or be removed, between releases.

<!-- agent-only -->
If the person is joining a project, add: "If you'd like to see this project's own requirements traced the same way, type **trace**." When they type it, pick a requirement ID that both a test and code in the project refer to, search for it, and show the results in your own message. If no requirement has both, say so in one sentence. If they answer what you paused on instead, that means no.

Then list a few topics by title, and offer to list the rest:

If you'd like to go further, each of these topics is short, and you can ask for any of them later:

- How the levels close in on what you meant
- One big design, or a tree of smaller ones
- Where product documents such as PRDs fit
- How a change in a design reaches the code
- Who checks each level
- …and more, which I can list

Then bring the person back to where you paused, with its question repeated, introduced with "Or, back to …".
<!-- /agent-only -->

<!-- /tour:steps -->

## Notes during the first change

For the rest of a session in which the person saw at least the first step of the tour, add each note below the first time its moment happens. Each note appears once in the session. A note never adds a pause, delays the phase's work, or replaces anything the phase presents. Give it as one quoted line in this frame:

> 💡 **First pause.** You can say go, correct anything in the draft, answer the questions I asked, or skip this pause and keep going, and I'll tell you what skipping risks.

- **First pause** (the first stop after a level): use the note above.
- **First requirement with an ID:**
  > 💡 **First ID.** `<ID>` is how I'll find this requirement's test and code when the requirement changes later.
- **First test written before its code:**
  > 💡 **First test.** This test fails right now on purpose, because the code it checks doesn't exist yet.
- **First edit to an existing higher document that's carried down to the lower ones** (if one happens):
  > 💡 **Carrying a change down.** I'm updating the requirements, tests, and code under this document now, so they still agree with it. If the change would reach another part of the project, I'll stop and ask you first, because that part may be described less fully and a change pushed into it unchecked can spread mistakes.
- **End of the first change** (when the final checks pass): search for one of the change's requirement IDs, then give this note with the results in a text block below it. If the requirement, its test, or its code is missing because the person skipped that level, say which, in one more sentence.
  > 💡 **All linked.** When `<ID>` changes, searching for it is how I'll find everything that depends on it:

A person who declined the tour and later took it in the same session gets the notes for the moments still ahead. A person who only got the link to the tour page gets none.
