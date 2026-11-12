# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

## 2026-11-12 (evening): BenchTime's materials drafted and edited

**Decided by the maintainer.**
- The maintainer will review the brief, oracle, and change script together.
- The main session should use its own judgment on Sol's drafts rather than pass them through unchanged.

**Done.**
- **Drafting.** GPT-6.1 Sol drafted the interface, the oracle, and the change script, from [prompts/01-oracle-and-changes.md](seeds/benchtime/prompts/01-oracle-and-changes.md). Gemini 4 Argon drafted the brief from only the interface and the items stated at the start ([prompts/02-brief.md](seeds/benchtime/prompts/02-brief.md)). Together they cost about $0.40.
- **Editing.** The main session edited both. The edits are logged privately, because they reveal the hidden materials.
  - Three are marked for the maintainer's review: moving one emerging item later, replacing an emerging item that wasn't really emerging, and replacing the probe.
  - The others fix a brief that would have contradicted an askable rule, and stop the simulator receiving later intent early.
- **Editing rules.** These went into [design.md](design.md) because the main session knows the arms. Edits may fix consistency, gradability, realism, and scope. They may not change the mix of change types or move items to favour a predicted direction. Every edit is logged with its reason, and the drafts are kept unedited.
- **Hidden materials stay private.** The oracle and change script stay out of the public repository until the runs that use them finish, because an agent under test could find them with a web search. They live in a git-ignored `hidden/` folder, and their hashes will be published before any counted run. The brief and the prompts are public.

## 2026-11-12 (later): Seeds chosen, plan review adopted, costs constrained

**Decided by the maintainer.**

- **Seeds.** BenchTime is the pilot seed and ReleaseDesk the second, as recommended in the main session.
- **Every point in the plan review is adopted.** [design.md](design.md), [hypotheses.md](hypotheses.md), and [plan.md](plan.md) were rewritten to match. The main changes:
  - the pilot measures without repairing;
  - a bounded-attention policy joins the diligent and rubber-stamp ones;
  - the simulator keeps a record of its answers and is audited for leaks;
  - level 1 grading is black-box only, through the interface;
  - probes are one identical request forked from several ages;
  - redirect costs are marginal, measured against a twin run;
  - an interrupt timing doesn't depend on the arm's stopping points;
  - each arm runs with its own configuration;
  - the pilot runs in four stages with stopping criteria, about 200 sessions instead of about 700;
  - the A/A check and positive control;
  - an equivalence margin;
  - LID's ablations and a medium seed come before the competitors;
  - the competitors' maintainers are invited before pre-registration.
- **The owner's latent intent can arrive late.** The maintainer's idea: intent shouldn't only be bounded by the owner's attention. Some of it should be released later in the work, the way an owner realises something weeks on, or a requirement passed through a business group loses detail, or a product manager forgets to pass it on. Every oracle item now has a disclosure point: stated, askable, recognised on sight, emerging at change k, or realised on a symptom. Emerging intent became part of H4, and relayed briefs became a later variant.
- **Cost is a real constraint.** Costs should stay small without weakening the research. Graders should run on the maintainer's Claude subscription where possible. Graders, the simulator, and the classifier therefore run through `claude -p`, with Haiku 5.5 tried first for grading. The risk of Claude grading Claude is handled by black-box grading, blind grading, calibration, and a small cross-family sample. OpenRouter money is limited to authorship, that sample, and the later stage with other executor families.

**Also changed.** H2 and the change-type table now agree, so adding a field is an ordinary local feature. H4 compares marginal costs at the same timing. H7 states its metrics and threshold. H8 (proportional cost and size), H9 (intent surviving over time), and H10 (the cold reader) are new.

## 2026-11-12: Graders are models; collecting project proposals

**Decided by the maintainer.**

- **Graders are models.** The oracle-gap result shows only that deterministic tests can't grade output the agent words and names for itself. What we grade is meaning, which models handle well, and even a small model such as Haiku may catch a lot. Graders are calibrated before they're trusted, and the maintainer spot-checks their verdicts, most heavily at fidelity level 2 (artifacts against code). [design.md](design.md) now treats model graders as primary, keeps executable checks only where the brief fixes the output exactly, and tags each graded requirement as stated or latent.
- **Collect project proposals from other model families before choosing the pilot seed.** GPT-6.1 Sol and Gemini 4 Argon each answer the same prompt ([seed-proposals/prompt.md](seed-proposals/prompt.md)), and the maintainer picks. Briefs, even for a domain Claude proposed, can also be written by models from several families, for variety.
- **Get one more read of the plan from Claude Fable** before starting M1.

**Done.**

- The same prompt also went to a fresh Claude Opus 5.5 session through `claude -p`, with no tools and no project context. Claude's proposals then come from the same inputs as the other two, rather than from the main session, which already knew the design.
- **Fifteen candidate projects came back.** They are in [seed-proposals/](seed-proposals/README.md), with a comparison table. The OpenRouter calls cost about $0.09 (Sol) and $0.16 (Argon). Claude Code estimated $1.05 for the Opus session.
  - Sol's top pick and Argon's are nearly the same domain: shared lab equipment booking.
  - All three proposers asked, unprompted, for a clock the grader can set.
- **Claude Fable reviewed the plan** with no context beyond the notebook. Its report is saved as [inputs/2026-11-12-fable-plan-review.md](inputs/2026-11-12-fable-plan-review.md). Its top concerns:
  - the repair loop acts as a free QA team for every arm;
  - the diligent simulator acts as a perfect proofreader, which rewards whichever arm shows the most text;
  - graders that read the repository can't be blind to the arm;
  - a small pilot can't show the slope it is meant to measure;
  - redirect costs aren't comparable across arms with different stopping points.

  Its proposed changes wait on the maintainer's decision.
- **Kept the kickoff brainstorm** by the second model as [inputs/2026-11-11-fable-brainstorm.md](inputs/2026-11-11-fable-brainstorm.md), so a later reader can see where the design came from.

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
