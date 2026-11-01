# Newcomer tour: the offer

LID offers a short introduction, the tour, to a person meeting it for the first time. This file covers who sees the offer, what the offer looks like, how to read the person's answer, and how to record it. The tour itself is in `tour.md`, and the topics a person can go further into are in `tour-topics.md`, both beside this file.

## Who sees the offer

A skill that makes the offer (the workflow's Phase 1 bootstrap, `/update-lid` on a project with no LID directives, `/map-codebase`, or the start of a change in a project that has LID directives) checks the memory your harness already placed in your context before its first message. If that memory shows the person has met LID before, there is no offer. The tour's own record is the usual sign, and other memories that show the person working with LID count too. Otherwise, apply these conditions:

- **Setting LID up** (Phase 1 bootstrap, `/update-lid`, `/map-codebase`): show the offer unless your harness's per-person memory shows the person has met LID before. If your harness keeps no such memory, show it anyway. Setup is rare for any one person, and carrying on declines it.
- **Joining a project** (the start of a change in a project that already has LID directives): show the offer only if your harness keeps per-person memory that you may write, as *Recording the answer* below describes, and that memory doesn't show the person has met LID before. Without such memory, make no offer, because nothing could stop it from coming back at every change.

Check only the memory already in your context. Don't search files or run commands to look for a record.

Make the offer at most once in a session, whichever skill reaches it first. Only the agent talking with the person makes it. A subagent you dispatch never does. In Scoped mode, if you need to ask whether a change is in scope, make no offer until the answer puts the change in scope.

## The card

Put the card at the top of your first message to the person, whatever that message asks. Write it exactly as shown in the block below, including the `>` at the start of every line, so it appears as a quoted block set apart from the rest of your message. The ```` ``` ```` fence lines around it are not part of the card. Then write the message you would have sent anyway, unchanged, introduced as the way to keep moving. Never send the card on its own and wait for an answer: the person carries on simply by answering the rest of the message.

When the person is setting LID up:

```markdown
> 👋 **New to LID?**
>
> When you ask a coding agent to build something, your request usually leaves some details unsaid, and the agent fills them in with its best guess. LID has me write your request down in layers before any code exists: first why the project exists, then how each part should work, and then short requirements that a test can check. I show you each layer and wait for your go-ahead, so if I guessed wrong, you can correct it while it's still a sentence instead of after it's code. Every test and every piece of code then points back to the requirement it serves, so when something changes later, I can find every piece connected to it, even across many files.
>
> Say **tour** for a short walk-through right here, or read the same thing at **linked-intent.dev/tour**.
```

When the person is joining a project that already uses LID:

```markdown
> 👋 **This project uses LID.**
>
> Work in this project starts from documents that say what it should do: why the project exists, how each part works, and short requirements that a test can check. When you ask for a change, I write it into those documents first, before any code exists. I show you each document I change and wait for your go-ahead, so if I guessed wrong about what you meant, you can correct it while it's still a sentence instead of after it's code. Every test and every piece of code points back to the requirement it serves, so when something changes later, I can find every piece connected to it.
>
> Say **tour** for a short walk-through right here, or read the same thing at **linked-intent.dev/tour**.
```

Then continue with "Or, to keep moving:" and the rest of your message.

## Reading the answer

Read the person's reply the way a colleague would:

- **First, check whether the reply could answer either the card or your own question.** A bare "yes", "ok", or "sure" is ambiguous whenever the rest of your message also invited a yes, whether by a yes-or-no question or by something like "reply go to proceed". Don't pick one, even if one reading seems more likely. Ask in one short question which they meant, for example: "Did you mean yes to the short tour, or yes to going ahead with Full mode? I'm happy to do either."
- **"Tour", a "yes" that can only mean the card, or any other request for the introduction:** start the tour from `tour.md`. When it ends, bring the person back to where you paused (`tour.md` describes how).
- **A question about the tour or about LID** ("how long is it?", "what does Scoped mean?", "how does cascade work?"): answer it briefly, offer the matching topic from `tour-topics.md` where there is one, and leave the offer open. Record nothing yet. If they keep asking, don't repeat your own question after every answer: it's still there in your first message.
- **"Not now", saying they already know LID, or carrying on with the work** (answering your question, approving a draft, or any other reply that continues): the offer is declined. Carry on exactly as you would have without the card, apart from the short clause about the record described below.
- **A request for the tour or a topic later,** in this session or any other: give it, whether or not they declined.

## Recording the answer

Record one fact in your harness's per-person memory, using exactly one of these two phrases:

- `Has met the LID tour: took it`
- `Has met the LID tour: declined`

A person who said they already know LID is recorded as declined. A person who saw at least the tour's first step took it.

- **Where:** only in memory your harness's own instructions in your context allow you to write facts about the user to. If the harness asks before memory writes, follow its rule. Never write the record into the project's files, including its instruction file.
- **When:** at the next natural stopping point. For a person who declined, that's when your current step finishes. For a person who took the tour, it's when the tour ends. That way a harness that asks before memory writes asks while the person is already pausing, never between their answer and what they asked for.
- **Saying so:** after the write succeeds, mention it in one short clause in that message. For example, after a decline: "I won't show the LID introduction again in this project, and you can ask for the tour any time." After the tour: "I've noted that you've taken the LID tour, so I won't offer it again here." If there is no such memory, or the write fails or is refused, say nothing about remembering.
- **A later yes:** when a person whose record says declined takes the tour, change the record to say they took it.

## Where the tour lives

On a host with the LID plugins, `tour.md` and `tour-topics.md` sit beside this file in the `linked-intent-dev` skill's references.

If you're following the vendored workflow doc instead of the `linked-intent-dev` skill, those files aren't local. Fetch them only when the person asks, from LID's repository at the release given in the workflow doc's header (replace `<version>` with that version):

- `https://raw.githubusercontent.com/jszmajda/lid/v<version>/plugins/linked-intent-dev/skills/linked-intent-dev/references/tour.md`
- `https://raw.githubusercontent.com/jszmajda/lid/v<version>/plugins/linked-intent-dev/skills/linked-intent-dev/references/tour-topics.md`

If you can't get `tour.md` (you have no way to fetch, the fetch fails, or it's refused), point the person to https://linked-intent.dev/tour, record that they took the tour, and carry on without waiting. That person gets no notes during their first change, because the notes are in `tour.md`. If you can't get `tour-topics.md`, point the person to the topics on that page (https://linked-intent.dev/tour#going-further), and leave the record unchanged.
