# Working hypotheses

**Status: working draft. Nothing here is pre-registered yet.** These hypotheses freeze, together with the primary comparison, the analysis plan, and the equivalence margin, before the first counted run (milestone M3 in [plan.md](plan.md)). Until then they change freely, with the reason recorded in [log.md](log.md).

Each hypothesis states a prediction, why we expect it, and what result would show it wrong. "Arms" are the ways of working being compared, for example a bare agent, a cheap discipline baseline, or LID. [design.md](design.md) describes them and defines the terms used here: cost per change, fidelity, requirements in force, and the disclosure schedule.

## H1: LID's cost per change grows more slowly as a project ages

**Prediction.** Building the system costs more under LID than under the bare and cheap-discipline arms. After that, LID's cost per change on identical probe requests grows more slowly with the number of earlier changes, so the cumulative cost curves cross at some change count. The crossing point depends on project size and on the mix of change types.

**Why we expect it.** A change made later has to find the intent it depends on. Under LID that intent is written down and linked to the code, so an agent in a fresh session can find it cheaply. Without it, the agent has to work the intent out again from the code, or it guesses. SlopCodeBench found that cost per change grew about 2.2 times from first to last change in agent-maintained code, and that prompting for quality didn't change the rate of decline ([sources.md](sources.md)). We expect LID to change the rate, not just the starting point.

**What would show it wrong.** LID's slope of cost per change is the same as the other arms' (inside the equivalence margin) or steeper. Or the curves don't cross within the range of change counts we can afford to test.

## H2: LID's advantage, if any, is in changes that depend on earlier intent

**Prediction.** LID costs less, or breaks less, on changes that depend on intent stated earlier and not visible in the code. Examples are a rule that applies across the whole system, a reversal of an earlier decision, a change that needs to know why an earlier tradeoff was made, and a bug report that describes only a symptom. LID costs more on copy or config changes, dependency bumps, and pure refactors. Ordinary local features, such as adding a field, show no clear difference.

**Why we expect it.** LID's up-front work pays off only when a later change needs what that work recorded. A copy edit needs nothing from it, so the overhead is all cost.

**What would show it wrong.** LID's relative cost doesn't differ between the change types predicted to favour it and those predicted to disfavour it.

## H3: LID asks for more human attention, and more of it is deep

**Prediction.** LID makes more requests of the person than the bare and cheap-discipline arms, counting every kind including bug reports and end-of-change reviews. A larger share of LID's requests are judgment or origination rather than acknowledgement or lookup. Requirements that LID asked about are met more often later than the same requirements in trajectories that never asked about them.

**Why we expect it.** LID stops for inspection after every phase, and its tenets lean toward asking the person. The question is whether that attention buys anything.

**What would show it wrong.** LID's attention profile looks like the other arms', or asking about a requirement doesn't raise the rate at which it is met later.

## H4: Late intent costs less to absorb under LID

**Prediction.** Two kinds of late intent cost LID less at the margin than they cost the other arms at the same timing, and leave fewer statements of abandoned intent in its artifacts afterwards:

- redirects, where the owner changes their mind or clarifies partway through a change;
- emerging intent, where the owner realises something at change k that contradicts a choice the arm made earlier.

The marginal cost of a redirect is the cost of the change with the redirect, minus the cost of the same change with the final intent stated from the start.

**Why we expect it.** LID's phase stops are natural places to redirect. Its cascade rule pushes a change in intent down through every level below it. A choice that LID recorded in a spec should be easier to find and change when the owner's realisation arrives.

**What would show it wrong.** LID's marginal redirect cost, or its cost to absorb emerging intent, is no lower than the other arms' (inside the equivalence margin). Or LID's artifacts keep stale intent as often as the other arms' do, relative to how much each arm keeps.

## H5: Process overhead pays off more on a mid-tier model than on a top-tier one

**Prediction.** The gap between LID and the bare agent, in both cost and fidelity, favours LID more on Sonnet 5.5 than on Opus 5.5. If Sonnet 5.5 shows no difference, a Haiku 5.5 tier may test the prediction at a lower tier.

**Why we expect it.** Two published studies point this way. In one, a harness of contract specs and checks gave a cheap model the same acceptance as a flagship model at lower cost, but gave the flagship model nothing for ten times the tokens. In the other, test-driven development tripled or more the token use of a strong model with no gain in quality ([sources.md](sources.md)).

**What would show it wrong.** The gap is the same on both tiers, or larger on the top tier.

## H6: LID's artifacts make intent checkable in CI

**Prediction.** Of the requirements each arm currently meets, a larger share of injected violations are caught by LID's own tests than by the other arms' own tests and validators.

**Why we expect it.** LID links each requirement to its tests, so every stated requirement should have a test that would notice it being broken.

**What would show it wrong.** LID's detection rate is no higher. That would also be a finding about LID's test discipline. This score is reported on its own and never folded into a combined score.

## H7: The ranking of the arms holds across model families

**Prediction.** Within each executor, the arms rank in the same order on the primary measures: the slope of cost per change against age, and fidelity on preserved requirements.

**Why we expect it.** If a way of working really helps, it shouldn't depend on one provider's models. If the ranking changes between families, some arm may be tuned to one provider.

**What would show it wrong.** Two arms swap places between families, and in at least one family the difference between them has an interval that excludes no difference.

## H8: LID's cost falls in proportion to how much of it a project uses

**Prediction.** LID Scoped costs less per change than LID Full on the same seed, and its fidelity is lower only on the parts of the project outside its scope. LID's cost relative to the cheap-discipline arm falls as the seed grows from well under the executor's context window to near it.

**Why we expect it.** HLD Goal 3 claims that the adoption modes let teams use LID "at proportional cost". Issue #75 asks for evidence for that claim, and these comparisons provide it.

**What would show it wrong.** Scoped costs as much as Full. Or LID's relative cost doesn't fall as the seed grows.

## H9: Intent survives longer under LID

**Prediction.** LID's fidelity on preserved requirements stays higher than the other arms' as the project ages, and the gap widens with age. The gap is largest for latent requirements, the ones the owner disclosed only when asked or on seeing a wrong proposal.

**Why we expect it.** This is the fidelity half of H1. Intent that is written down and linked to the code should survive fresh sessions better than intent that lives only in the code.

**What would show it wrong.** Preserved-requirement fidelity is the same across arms (inside the equivalence margin) at every age.

## H10: LID's artifacts tell a cold reader the truth more cheaply

**Prediction.** A cold reader with the whole repository and a fixed token budget answers questions about the system's behaviour more accurately, and finds where each behaviour is implemented and tested at lower cost, under LID than under the other arms.

**Why we expect it.** LID's docs and `@spec` links are meant to make the system navigable for an agent that knows nothing about it.

**What would show it wrong.** The reader's accuracy and cost are the same across arms. Or the other arms' artifacts don't support the measure at all, which would be a finding about them rather than a result about LID.

## The result we commit to publishing either way

At the project sizes we can afford, a bare agent on a frontier model may meet nearly every graded requirement. If so, the likely result is that "LID costs k times more with no fidelity gain we could measure at these sizes." That answers #75's requirement that LID say honestly where it isn't worth the spend, and we publish it if it's what we find.
