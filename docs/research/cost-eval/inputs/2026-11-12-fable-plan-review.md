# Review of the plan by Claude Fable (2026-11-12)

A fresh Claude Fable session was asked for a critical review of the notebook as it stood on 2026-11-12, before the seed proposals came back. It was read-only. The text below is its report, unedited apart from formatting. [log.md](../log.md) records which points were adopted.

The five points that matter most are marked **[TOP]**. Cost figures are rough guesses, and the reviewer did not test any `claude -p` behaviour.

## 1. Biggest risks to a trustworthy answer (ranked)

- **[TOP] The repair loop gives every arm a free, instant, all-knowing QA team.** Graders re-check every requirement after every change and the simulator files a bug straight away.
  - Dwell time is therefore always zero, although design.md says it is recorded.
  - The human cost of noticing and reporting a failure is never counted, which favours arms that regress.
  - Grader false-fails become real repair sessions charged to the arm. At 40 requirements and a 2% false-fail rate, that is about one spurious repair per checkpoint.
  - Fix: run the pilot measure-only, with no repair loop, and report cost and the fidelity curve side by side. Add repair later with a detection lag, each bug report counted as a human touchpoint, and a failure filed only after a replayed reproduction.
- **[TOP] The diligent simulator is an oracle-backed proofreader, not a person.** It checks every document against the hidden oracle with perfect recall, so the arm that shows the most text (LID) gets the most free correction. Rubber-stamp is the opposite extreme, and the result will probably flip between the two.
  - Fix: add a bounded-attention policy, where each contradiction is caught with a probability that falls with document length, calibrated from the maintainer-played trajectories.
  - Define what the simulator does with a broad question ("any other edge cases?"). Tag each oracle item as disclosed on a specific question or only on seeing a wrong proposal.
  - Define what it does when the oracle is silent.
  - Give it a per-trajectory ledger of answers already given. Otherwise a fresh simulator at change 6 can contradict change 2.
  - Audit it for volunteering oracle facts nobody asked for. plan.md calibrates the grader but not the simulator.
- **[TOP] Graders cannot be blind if they read the repository.** LID's `docs/`, `@spec` comments and NOTES.md identify the arm, and a requirement written in a spec can persuade a grader that the behaviour exists.
  - Fix: grade level 1 black-box only, through the external interface, against a built artifact with no source.
  - The brief must then fix a run command, a state reset and an injectable clock. "When does day 30 end" cannot be graded otherwise.
  - Add a test-retest check: grade the same snapshot twice and report the flip rate.
- **[TOP] The pilot cannot see the effect the hypothesis is about.** A 1,000 to 3,000 line seed fits whole in the context window, so navigation is never tested. Eight to ten changes cannot show a slope or a crossing. The size question #75 asks is deferred to M6, behind competitors and model families.
  - Fix: move LID Scoped, the overlay ablation and a medium seed ahead of the competitor arms. They answer #75 directly and carry no conflict of interest.
  - Measure slope by forking the identical probe request from snapshots 0, 3, 6 and 9 and discarding the result. "Same type, different instance" confounds age with how hard the instance is.
- **The change mix decides the headline, and LID's maintainer picks it.** Four types are predicted to favour LID, two to disfavour it. Fix: report per type always, weight any aggregate by a mix taken from real commit histories and fixed in advance, and publish the break-even mix ("LID wins if at least x% of changes depend on earlier intent").
- **Config contamination.** LID plugins, a global CLAUDE.md and memory are installed at user level on the maintainer's machine. Unless each arm gets an isolated config directory, the bare arm may load them. Fix: isolate per arm and assert the loaded skills and plugins from each session's init record. Pin the Claude Code version and model snapshot.
- **Touchpoints depend on headless plumbing that is unverified.** Check in M1 that plan-mode approval, LID's phase stops and question-asking all work through stop-and-resume under `claude -p`. You also need an explicit classifier for "turn ended, done" against "turn ended, waiting", and one sentence given to every arm saying an owner is available.
- **Token accounting.** The log says subagent usage "may not be included". Resolve this before any run. Never pace inside a change, because cache expiry between resumes would penalise arms with many stops.

## 2. Inconsistencies and gaps

- "Accepted change" is the unit of the headline claim and is never defined. Does a latent failure block acceptance?
- No primary comparison is named, even provisionally, yet the pilot is meant to measure its variance.
- No hypothesis covers size, Scoped mode or "proportional cost", which is #75's actual claim. None covers fidelity on its own (preserved-requirement pass rate) or the level 2 cold reader.
- hypotheses.md H2 lists "adding one field" as costing LID more. design.md's table marks an ordinary local feature as "neither".
- Probes are at new, about 5 and about 15 changes, but the pilot script has 8 to 10.
- The bare arm is "harness defaults", but auto-memory, a default, is off in every arm.
- Graders must come from a different family from the executor, yet plan.md trials Haiku for a Claude pilot. A cross-family grader also means the pilot spends real OpenRouter dollars.
- H6 says "the project's own test suite"; design.md adds "any validator the arm ships". Neither sets the denominator (only requirements the arm currently passes) or says who writes and validates the mutants.
- The rubric links each requirement to the change that introduced it, but not to the one that retires it. Reversals and redirects need validity intervals, or "check everything after every change" will grade retired intent.
- Stated and latent tags change per trajectory once an owner answers or a bug report reveals the rule. This is not specified.
- H4 says "costs less under LID" without saying against what: other arms at their early point, or LID late.
- H7 does not say which metric the arms are ranked on, or what "more than the noise" means.
- The evidence grades cannot rate a null. Grades A and B need an interval that excludes no difference, but the result you commit to publishing is "no measurable gain". Add an equivalence margin.
- The level 2 reader gets docs for LID and code plus README for bare. Give every reader the whole repository and a fixed token budget, and merge this with "cost to trace".
- The repair cap sensitivity check, the time limits and the stack are unspecified. Fix the language in the brief to cut variance.

## 3. The pilot (M1 and M2)

- As written: 3 arms × 2 models × 2 policies × 3 repetitions = 36 trajectories.
  - Each is about 10 scripted sessions plus repairs and probe forks, so about 20 sessions, or about 700 in total, half on Opus.
  - LID sessions are about 6 to 8 resumes each, so roughly 2,400 `claude -p` invocations, plus about 2,000 simulator calls.
  - Grading is about 470 checkpoints, or about 12,000 verdicts if done one requirement at a time.
  - At list price the guess is $1,000 to $5,000 equivalent, which means weeks of paced quota.
  - Maintainer-played trajectories are hours each for LID, at 60 or more touchpoints.
- It is not the smallest pilot. Stage it with kill criteria:
  - Stage 0, plumbing: 3 arms, Sonnet, a build plus 2 changes, about 9 sessions.
  - Stage 1, ceiling: bare arm only, Opus, the full script, 2 trajectories, about 20 sessions. Stop and harden the seed if it passes more than about 85 to 90%.
  - Stage 2, variance: 3 arms × 1 tier × 3 repetitions, one policy, with identical-probe forks.
  - Stage 3: the second tier and the second policy, on the LID and cheap-discipline arms only.
  - Total: about 15 to 20 trajectories and about 200 sessions.
- Cut:
  - both policies on the bare arm, which never stops, so they are the same run;
  - the repair loop;
  - redirects as a measurement, since 2 of 4 cells at 3 runs each only test plumbing;
  - the second tier until stage 2 passes.
- Missing:
  - numeric go/no-go thresholds for every pilot question;
  - a positive control, a deliberately degraded arm the instrument must detect;
  - an A/A check, bare against bare;
  - grader test-retest;
  - the simulator leak audit;
  - verification of subagent token accounting;
  - a budget for grader dollars.

## 4. The human-attention measure

- It is not yet fair. Bare shows zero touchpoints while its human pays later in bug discovery and in reviewing the final diff, and neither is counted. Count bug reports as a fifth kind, and treat the end-of-change review the same way for every arm.
- "Acknowledgement" is defined by whether the plan matches, which the person learns only by reading it. The cost is the reading. Report words presented separately from decisions requested, and count changed words since the last touchpoint, not whole documents.
- Operationalize as follows:
  - The unit is one request, and a turn may hold several.
  - Classify by the request plus the oracle, never by the simulator's reply, so the kind does not depend on policy. Lookup: the answer is a stated item. Judgment: it is latent and the agent offered the right option. Origination: it is latent and not offered, or absent from the oracle.
  - Have two people label about 100 requests and set a target agreement of kappa 0.7 or better. If four kinds don't reach it, collapse to decision against no decision.
- Yield as defined measures relevance, not prevention. H3's falsifier ("extra questions don't change outcomes") needs a counterfactual: the pass rate on the same requirement in trajectories where it was not asked.
- Drop wall-clock time under paced quota, or record active time only.

## 5. The redirect design

- **[TOP] "Cost from the redirect to an accepted change" is not comparable across arms.** At an early stop LID still has four phases of ordinary work left that the redirect did not cause. Bare has no early stop at all in headless mode, so its early redirect is the same as its late one.
  - Fix: measure marginal cost. From the same snapshot, run the change with the redirect and a twin with the final intent stated at the start, and subtract.
  - Add an arm-independent timing, an interrupt at a fixed fraction of the arm's median spend for that change, alongside the arm-native stops. A real bare-agent user can interrupt.
- A clarification redirect fires only if the agent guessed. If the arm asked first, record "pre-empted" as an outcome, not as missing data.
- Stale intent: define the artifact set to include code, tests and comments for every arm. Report a count and a behavioural check, since more artifacts means more places to go stale.

## 6. What a competing maintainer would object to

- "You chose the seed, the changes and the oracle review." Answer: have them written blind to the arms, hash them before any run, and include a second seed written by an outsider.
- "Your simulator rewards documents." Answer: the bounded-attention policy, with results shown as a function of detection probability.
- "Fresh sessions with memory off is LID's home ground." Answer: run the single-session and memory-on ablations and report them, not just list them.
- "You picked our configuration." Answer: invite their review before the freeze at M3, not at M4 after the design has hardened.
- "Small greenfield is not what we are built for." This is the same objection LID has, so state the scope on every claim.
- "LID-specific measures are folded in." Answer: keep level 3 and H6 out of any cross-arm score.
- Sonnet 5.5 may be too strong to stand in for the "cheap model" in the H5 sources. Consider a Haiku tier.

## 7. Cold pickup

- Mostly yes. The gaps:
  - README.md says "Last updated 2026-11-11" and its Next actions omit the 2026-11-12 work: seed proposals in progress, this review, grader calibration and the rubric.
  - `seed-proposals/` is not in the Files table and holds only `prompt.md`. The model responses are not saved.
  - The three original design takes are not kept.
  - There is no glossary for trajectory, checkpoint, probe, touchpoint or yield.
  - The Open questions list in design.md omits the third model family.
  - No run commands, config-isolation recipe or quota budget are recorded.
  - "A subagent given this page and one milestone has what it needs" is not true without design.md.
  - Six files are uncommitted in the worktree, so the public draft PR is behind the notebook.
