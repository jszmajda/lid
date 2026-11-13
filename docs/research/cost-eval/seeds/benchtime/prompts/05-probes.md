We're running a research study comparing ways of working with AI coding agents as software is changed over time. You wrote the hidden oracle and change script for BenchTime, our pilot project, and both are included below as they now stand after editing. Now I need the probes that graders use to check each oracle item.

## How grading works

Each arm of the study builds BenchTime from an owner-voice brief, then makes ten changes in fresh sessions. Every arm designs its own interface, so no two builds look alike. After each change, the study grades a checkpoint:

1. **Interface extraction.** A separate session reads the build and writes a neutral reference that says how to call each operation (setup, booking, and so on), never what it is meant to do.
2. **Execution.** A grader that sees only that reference and the probe scenarios performs each scenario against the running service and records everything in an execution log. It never sees the expected observations, the oracle, or the source. It reaches the service only through a harness tool that can:
   - set the service's clock to any instant, frozen there;
   - reset the service to empty data;
   - make requests;
   - run the service's own setup commands, if its setup data loads that way.
3. **Judgment.** A separate session compares each probe's expected observation with the log, and returns met, not met, or couldn't exercise. An item is met only if all its probes are met.

The executor and the judge are both models, so wording is judged by meaning: a refusal is any response that clearly declines, whatever its status code or message, and a field can have any name.

## What a probe is

A probe is a scenario plus an expected observation, written in terms of operations, never endpoints, fields, or status codes. Write probes that:

- **Cover the item's check sketch.** Turn the sketch into concrete steps with concrete times. Split it into several probes when it tests separate things, so a failure points at one thing. Most items need one to three probes. Keep each probe to about ten steps or fewer.
- **Separate the scenario from the expectation.** The executor sees only the scenario, so the scenario must name every inspection the judge needs ("then look at Maya's booking", "then list the bookings on scope-1") without hinting at the answer. Never write "check that it is refused" in a scenario; write "try to ...".
- **Check for unintended changes.** For a refused or invalid operation, the scenario inspects the relevant state afterwards, and the expected observation says what must be unchanged.
- **Start from a named setup.** Each probe starts from one of a few named setups, defined once at the top of your output, so the harness can prepare each setup once and restore it. The default is the example lab from the oracle's grading fixtures, with the clock at 2026-01-05T08:00:00Z. Define a variant only when a probe needs different setup data, such as an instrument with no cleaning allowance, another time zone, or a time-zone offset transition.
- **Use UTC times.** Give every time as a full UTC instant (2026-01-05T09:00:00Z), and say in the expected observation what local time it is when that matters.
- **Apply from the right change.** A probe applies from the change at which its item comes into force, or from the change that introduces an operation it uses, whichever is later, until the item is retired. Example: a BT-29 probe that moves a booking applies from change 3. A probe for an item in force from the start applies from change 0, the first build.
- **Name what the harness must provide** beyond the four abilities above, so we can build exactly that:
  - `concurrent`: two or more requests sent at the same moment (for race checks);
  - `restart`: restart the service on its existing data;
  - `prior-data`: data created at an earlier checkpoint, carried into this one (for checks about older records);
  - anything else, described plainly.

  Where a check would need an ability that isn't worth building, say so and leave that part out.

## Output format

Reply in Markdown with exactly this structure.

```
# Probes: BenchTime

## Setups

### S0: Example lab
<the oracle's example lab, restated in full, and the starting clock>

### S1: <name>
<what differs from S0, in full>

## Probes

### BT-01

#### P-BT01-a
- **Applies:** from change N[, until change M]
- **Setup:** S0
- **Needs:** none | concurrent | restart | prior-data | <other>
- **Scenario:**
  1. <step>
  2. <step>
- **Expected observation:** <what the log must show for this probe to be met, referring to the steps by number>
```

- Include every item in the item table that isn't marked Dropped, in ID order, BT-01 to BT-55.
- Give items whose sketch can't be turned into probes a one-line note under their heading, instead of probes, and explain why.
- Don't write probes for the separate, disposable probe request at the end of the change script. That is handled differently.

## Examples

These four probes were written by hand for a test of the grading machinery. Use them as examples of the format and level of detail, and revise them if they fall short of the rules above.

{PLUMBING_PROBES}

## The oracle

{ORACLE}

## The change script

{CHANGE_SCRIPT}
