# Working hypotheses

**Status: working draft. Nothing here is pre-registered yet.** These hypotheses freeze, together with the primary comparison and the analysis plan, before the first counted run (milestone M3 in [plan.md](plan.md)). Until then they change freely, with the reason recorded in [log.md](log.md).

Each hypothesis states a prediction, why we expect it, and what result would show it wrong. "Arms" are the ways of working being compared, for example a bare agent, a cheap discipline baseline, or LID. [design.md](design.md) describes them.

## H1: LID's cost per change grows more slowly as a project ages

**Prediction.** Building the system costs more under LID than under the bare and cheap-discipline arms. After that, LID's cost per accepted change grows more slowly as the number of earlier changes rises, so the cumulative cost curves cross at some change count. The crossing point depends on project size and on the mix of change types.

**Why we expect it.** A change made later has to find the intent it depends on. Under LID that intent is written down and linked to the code, so an agent in a fresh session can find it cheaply. Without it, the agent has to work the intent out again from the code, or it guesses. SlopCodeBench found that cost per change grew about 2.2 times from first to last change in agent-maintained code, and that prompting for quality didn't change the rate of decline ([sources.md](sources.md)). We expect LID to change the rate, not just the starting point.

**What would show it wrong.** LID's cost per change grows at the same rate as the other arms', or faster. Or the curves don't cross within the range of change counts we can afford to test.

## H2: LID's advantage, if any, is in changes that depend on earlier intent

**Prediction.** LID costs less, or breaks less, on changes that depend on intent stated earlier and not visible in the code. Examples are a rule that applies across the whole system, a reversal of an earlier decision, a change that needs to know why an earlier tradeoff was made, and a bug report that describes only a symptom. LID costs more on local changes such as a copy edit, adding one field, a dependency bump, or a pure refactor.

**Why we expect it.** LID's up-front work pays off only when a later change needs what that work recorded. A local change needs nothing from it, so the overhead is all cost.

**What would show it wrong.** LID's relative cost doesn't differ between the two groups of change types.

## H3: LID asks for more human attention, and more of it is deep

**Prediction.** LID asks the person for attention more often than the bare and cheap-discipline arms do. A larger share of it is judgment or working out new intent, rather than acknowledgement. A larger share of LID's questions also turns out to matter: the answer brings out intent the person hadn't stated, and a later graded requirement checks that intent.

**Why we expect it.** LID stops for inspection after every phase, and its tenets lean toward asking the person. The question is whether that attention buys anything.

**What would show it wrong.** LID's attention profile looks like the other arms', or its extra questions don't change outcomes.

## H4: Redirects cost less under LID when made early, and leave less stale intent behind

**Prediction.** When the person changes their mind or clarifies partway through a change, the redirect costs less under LID if it comes at a phase stop. After the change, LID's artifacts are less likely to still state the abandoned intent.

**Why we expect it.** LID's phase stops are natural places to redirect, and its cascade rule pushes a change in intent down through every level below it.

**What would show it wrong.** Redirects cost the same or more under LID, or LID's artifacts keep stale intent as often as other arms' do.

## H5: Process overhead pays off more on a mid-tier model than on a top-tier one

**Prediction.** The gap between LID and the bare agent, in both cost and fidelity, favours LID more on a Sonnet-tier executor than on an Opus-tier one.

**Why we expect it.** Two published studies point this way. In one, a harness of contract specs and checks gave a cheap model the same acceptance as a flagship model at lower cost, but gave the flagship model nothing for ten times the tokens. In the other, test-driven development tripled or more the token use of a strong model with no gain in quality ([sources.md](sources.md)).

**What would show it wrong.** The gap is the same on both tiers, or larger on the top tier.

## H6: LID's artifacts make intent checkable in CI

**Prediction.** When a violation of an earlier requirement is injected into the code, the project's own test suite catches it more often under LID than under the other arms.

**Why we expect it.** LID links each requirement to its tests, so every stated requirement should have a test that would notice it being broken.

**What would show it wrong.** The detection rate is no higher under LID. That would also be a finding about LID's test discipline.

## H7: The ranking of the arms holds across model families

**Prediction.** Within each executor (harness, model, and effort), the arms rank in the same order.

**Why we expect it.** If a way of working really helps, it shouldn't depend on one provider's models. If the ranking changes between families, some arm may be tuned to one provider.

**What would show it wrong.** The order changes between families by more than the noise between repeated runs.

## The result we commit to publishing either way

At the project sizes we can afford, a bare agent on a frontier model may meet nearly every graded requirement. If so, the likely result is that "LID costs k times more with no fidelity gain we could measure at these sizes." That answers #75's requirement that LID say honestly where it isn't worth the spend, and we publish it if it's what we find.
