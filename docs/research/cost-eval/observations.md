# Observations

Things the study noticed along the way that aren't results in their own right, but that may matter to LID, to measuring it, or to running a study like this with agents. Each one says what was seen, where the evidence is, and what it might mean. Most rest on a handful of runs, so treat them as leads.

## About LID

**Links between segments run one way, so an agent changing a rule can't see who relies on it.** LID records a dependency on the dependent side: a design doc references the concern it relies on. An agent changing the concern reads its own segment, finds nothing pointing outward, decides the change stays inside, and stops. On Clowder's cross-crate changes this cost the LID agent dependencies a grep-happy bare agent kept (log, 2026-11-23). Filed as #135.

**A boundary question sent to the owner often comes back unanswerable.** When one LID agent noticed that its change touched the interface's segment, it asked the owner whether to go in. The simulated owner, like many real ones, knew nothing about the code and said it had no preference, so the agent stayed out and broke the interface. The pause across segments routes a technical question to a person who may not hold the knowledge to answer it. One possible direction is for the agent to investigate the dependent side itself and bring the owner a decision about behaviour, not about segments.

**The design phase catches misreadings of the request.** On openGym, two LID runs first read "a join code for the gym" as an admin invitation, exactly as two bare runs did, and then corrected it while writing the design, before any code. The bare runs built the wrong thing, and repairs didn't fix it. This is one of the clearest places LID's structure paid off.

**Long documents make the owner's review weaker, not only slower.** The simulated owner objected to 2.7 of 4.3 contradictions in the bare agent's short messages, and to 0.3 of 4.0 in LID's long documents (log archive, 2026-11-17). The owner's attention model comes from published research on reading, so a real person may do no better. That bears directly on document length: shorter design documents might buy back review quality as well as time.

**LID's artifacts help agents that don't follow LID.** A bare agent working in Clowder's full repository, docs and all, wrote tests at Clowder's density and updated LID's docs in 10 of 12 changes (log archive, 2026-11-20). LID's documents seem to carry value of their own, separate from the workflow that produced them. That makes "LID against a bare agent" on a LID-built codebase a comparison of workflows over shared artifacts, which is why the study moved to projects each approach grows itself.

**The bare agent didn't divide its code into parts; LID did.** At change 20 on ReleaseDesk, the bare agent kept about 85% of its code in one file, while the LID agent's code was in 16 modules (runs/analysis/structure.md). On a small project that costs nothing measurable. It might matter a great deal on a long-lived one, because one large file is where intent from different decisions ends up tangled. This is a candidate mechanism for the long-horizon benefit people report, and a reason to measure structure in a long-horizon test.

**A cheap spec file can carry intent as well as LID's whole tree, for a cold reader.** When a fresh reader rebuilt the system's rules from each approach's artifacts alone, the checklist approach's single spec file did best (+42 points over guessing from the brief), LID's tree next (+36), and the bare agent's tests least (+10) (runs/growth/m2e.md). LID's advantage may lie less in having written intent than in keeping it linked and current as the system changes, which a one-run test can't show.

**LID didn't reduce the agent's later costs on small projects.** On BenchTime, the same request made after changes 0, 3, 6 and 9 cost LID the same extra amount each time. Whatever LID's written intent saves, it didn't show up as cheaper later changes on a project this small.

**The LID agent was behind on stated requirements on ReleaseDesk** (93% against 98%) while far ahead on unstated ones. We haven't looked at why. One guess is that effort spent writing and maintaining documents comes partly out of attention to the request itself. It's worth checking in transcripts before anyone builds on it.

**Grepping for literal values is a strong way to find dependencies.** Several of openGym's mirrored limits were reachable by searching for the number itself, from either side. LID's documents don't replace that kind of search, and an agent following LID may do less of it because it trusts the tree. Guidance that LID agents also search the code for the values and names a change touches could close part of the gap #135 describes.

**Inside a segment, the LID agent sometimes read too little.** On openGym the maps grouped each feature's API and app code into one segment, so LID's misses there weren't about boundaries: the agent read the server half of a segment and not the app half. Phase 4's edge audit looks across specs, but nothing prompts it to check that every file the segment owns was considered.

**`/map-codebase` under a mid-tier model drifts where the skill is loose or contradicts itself.** Across four draws, the agent making the map chose its segmentation before reading its own survey, accepted workers that skimmed, invented a cap on specs per file, and followed the skill's main file in some places and its reference in others (#133, #134). Each map recorded the rules inside a component well, and the ties between components rarely. A map is also a single draw: the three used here differed by a factor of two in size and cost.

**A project's instruction file can quietly reshape LID.** Clowder's instruction file tells agents to settle reviews below the HLD against the game's principles rather than ask the owner. The LID agent followed it, and even so it stopped 60 times across 36 changes. Anyone comparing LID across projects needs to read each project's instructions, because a standing override changes how many stops LID makes, and so what it costs and catches.

**The case for LID that the data supports best is "you get what you meant".** Across the projects, LID's clearest effects were on building what was asked and on surfacing what the owner left unsaid, mostly by asking. Preventing breakage in another part of the system depended on whether the documents linked the two parts. Onboarding material that leads with the first claim and is careful about the second would match the evidence.

## About measuring LID

**Check the grading both ways before counting anything.** On both large projects, grading the untouched code (which must fail every new requirement) and a correct build of every change (which must pass every one) caught faults first, every time. Some were faults in the probes, and one was a wrong "correct" build. Each check is cheap next to a run that has to be regraded.

**Grading that looks for code addressing a rule penalises an agent that rightly changes nothing.** Rules like "shy colonies nap at the same rate as before" are met by leaving code alone, and so are rules that hold through existing code the change relies on. A grader that treated "met, but no code addresses it" as suspicious voided correct results until we added guard rules and an "inherited" status.

**Probes have to test what the owner would see, not how the reference build did it.** Several faults were probes that encoded one implementation's shape: a particular accessor, a browser prompt instead of a sheet, an exact call count, a request without a flag a real interface always sends. Every right build we wrote passed them, because we wrote both. The fix each time was to test the observable outcome.

**A dependency check must not credit an agent that built nothing.** If a probe only checks that two parts agree, an agent that didn't implement the change keeps them agreeing for free. Scoring each run on two counts, whether the change was built and whether the other part was kept, broken or never exercised, closed that hole. A reviewer from another model family raised it, after reviewers from our own had missed it.

**Rescoring the same spot-check draws after a fix is not a fresh check.** Agreement went from 9 of 12 to 12 of 12 when the faulty probe was fixed, but those were the same verdicts. A fresh sample after the fix is the stronger evidence.

**Test whether the model already knows a codebase before using it.** Asking the executor to recall a project's internals with nothing shown took a few minutes and settled the question: one well-known project came back at over 80%, and two newer ones at about a fifth. Without it, a brownfield test can end up measuring memory.

**Single changes from a fixed snapshot can't show compounding.** Forked changes answer "does existing intent help on this change?" well. They can't show whether keeping intent current makes the hundredth change easier, because nothing carries forward between forks. That needs a sequence of changes on a project that grows past what an agent can read at once.

**A simulated owner with fixed intent can't show whether LID helps people think.** Our owner's intent was written in advance, so it had nothing to work out. A real owner often discovers what they want while writing or reading a design. If that's part of LID's value, this study's design can't see it.

**Agent dollars are the wrong headline cost.** LID's extra agent cost was well under two dollars per change at list prices. The owner's reading was 5 to 11 times larger, and it degraded review quality. Reports on LID's cost should lead with reading time.

**Repair cost leaves out the time a miss goes unnoticed.** Fixing a reported miss was cheap. What the study can't price is how long a real owner takes to notice one, and what the wrong software costs in the meantime. That's the term that decides whether "cheap agent now, repairs later" beats LID.

## About running a study like this with agents

**A subagent that hands back while its job runs may not come back when the job ends.** Once, a null check finished and nothing started the next step for about five hours. Since then, the main session starts its own watcher on any job a subagent leaves running.

**Parallel work on a live harness needs a separate workspace.** Runs import the harness as they start, so editing it mid-run can change a run halfway. Building the next study's harness in its own jj workspace, merged after the runs finished, kept the two apart. Committing while a subagent edits the working copy snapshots its half-done work, so commits wait for agents to stop.

**Freed container volumes don't free disk until the VM's disk is trimmed.** Colima's disk image grew back to 89 GB as runs created and released volumes, and the Mac fell to under 9 GB free. Trimming after every release, and a disk gate that checks the host's free space as well as the VM's, fixed it.

**Small harness faults can look like results.** A planner that listed each miss twice ran two repairs into one workspace. One faulty probe voided a whole batch of judgments. A shared test baseline raced when several graders built it at once, and suites run in parallel ran out of memory. Each one read as an outcome until someone looked at a transcript. Reading a few transcripts per phase, not only the summary tables, found most of them.

**Rebuilding a run from its saved diff works, if the check is exact.** When volumes had been released, regrading from each run's saved diff, with a byte-for-byte or tree-hash check against what was first graded, let us apply fixed probes without rerunning the agents.

**Reviewers from several model families find different things.** Claude Fable's reviews caught most probe and grading faults. A GPT reviewer caught the dependency-credit hole that applied to both large projects. A cold reader with no context was the best check on whether an issue said what it meant.
