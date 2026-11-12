# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

## 2026-11-11: Kickoff

**Done.**

- Found issue #75 as the home for this work. #75 compares walking LID's arrow with not walking it. Comparing LID with other SDD systems widens that scope, so the eval instrument will probably get its own issue, linked to #75.
- Collected three independent takes on the design: a brainstorm in the main session; a brainstorm by a second model (Claude Fable), which didn't see the first; and a survey of the SDD landscape and the published research. All three, working separately, arrived at the same core design:
  - a fresh session for each change, with the agent continuing in its own workspace;
  - hidden behaviour tests at a fixed interface, split into new and preserved behaviour;
  - the slope of cost per change as the measure, rather than the total;
  - a user simulator as the main fairness question;
  - pinned versions and dated claims.

  The survey added two axes: model tier, and a plan-mode baseline.
- Checked whether existing Claude Code transcripts from one of the maintainer's LID projects could give a cheap first answer. There were about 25 recent sessions on Opus 5 and 5.5, with token usage recorded. They can't answer the question, for four reasons:
  - transcripts are kept for only about 30 days;
  - each session mixes many tasks;
  - phases aren't marked;
  - there is no comparison arm.

  They do show one thing. Cache reads were by far the largest token class, usually 20 to 110 times the cache writes and over 200 times in one session, while uncached input was a few thousand tokens per session. Token counts that don't split by class therefore say little about cost. Subagent usage may not be included in these counts.

**Decided by the maintainer.**

- **Keep the comparison with other SDD systems.** People ask about it more than anything else.
- **Also compare LID with a bare agent and with cheap discipline.** Cheap discipline is the unbranded way of working that probably covers the most real use.
- **Staging is the main session's call.** The maintainer has no strong view on the order of the work.
- **Invite the maintainers of the compared systems** to run the eval on their own systems, in case we configured them wrong, and document how to do it.
- **This is a research spike, not a gate.** It should be able to become a measuring eval or a gate later.
- **LID's bidirectional-differential skill is the idea behind measuring intent fidelity.** It doesn't grade fidelity from HLD to LLD to EARS. Measuring that level may lead to extending the skill or adding a new one.
  - LID's own tools aren't used as metrics, but their methods may carry over to other systems, for example a naive reader working intent out again.
  - Some systems may not produce artifacts where intent fidelity can be measured at all, and that would be a finding in itself.
- **The eval includes redirects:** the user changing their mind, or clarifying an unclear intent, partway through a change.
- **Human attention is a headline measure,** and so is the kind of attention: saying "ok" differs from having to think hard. The human cost is the most interesting part.
- **SlopCodeBench is worth trying,** alongside a bespoke eval. SLUMP and EvoClaw are more divergent, and optional.
- **Measure top-tier and mid-tier models.** Candidates beyond Claude are the GPT-6.1 family (Sol at the top tier, Terra at the mid tier), Gemini 4 Carbon or Argon, and recent DeepSeek models. Models from other families can write material that shouldn't be written by Claude, such as the oracle.
- **Plan mode is a reasonable cheap-discipline baseline.** Other definitions of discipline may be tested too.
- **For Spec Kit, use the configuration closest to LID,** and document it carefully. That is the living-spec model.
- **Leave Kiro out.** A plan-plus-EARS arm could stand in for it, and cc-sdd is that arm.
- **Mining old transcripts (stage 0) is dropped.** The maintainer doubted it would help, and the transcript check above confirmed that.
- **Work in public,** with a draft pull request that gets regular pushes, and keep this notebook so that someone starting a new session cold can pick up the work.

**Answered: why oracle-gap tests fail.** The question was whether hidden tests fail on unstated names because the grader isn't capable enough to see that two names mean the same thing.

In the oracle-gap paper the grader isn't a model. It is an executable test suite, and a test can't see meaning at all: a test that imports `valueSSE` fails to compile against a correct implementation that calls the constant `valueEventStream`. A more capable grader would have passed those runs.

Our design does two things about this:

- Hidden tests touch only the fixed external interface, whose names are part of the stated intent.
- Wherever a model judges instead, the judge is first checked on pairs of the same behaviour under different names, and different behaviour under the same names.

**Next.** M1 in [plan.md](plan.md): the pilot seed, its oracle, the change script, the simulator, and the three arm configurations.
