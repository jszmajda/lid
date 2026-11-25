A software system keeps its requirements as a spec file of numbered lines. Over time some lines were reworded or replaced. Below is the spec file as it stands now, then old versions of lines that no current line repeats word for word.

For each old version, decide whether its intent is still held by the current spec file or has been retired.

- **still said:** everything the old line requires is still required by one or more current lines, perhaps in other words, in more detail, or with more cases added. List those current lines' IDs in `current`.
- **retired:** the old line requires something the current lines no longer require: the current lines contradict it, narrow it, or dropped that part. Write `retired_claim`: one sentence, in plain words, saying only what no longer holds (not the parts the current lines kept). Give `quote`: words copied exactly from the old line that carry that claim. List in `current` the current lines that replaced it, if any.

When an old version retires the same claim as an earlier retired one (say, two successive wordings of a rule since replaced), set `duplicate_of` to that earlier candidate's number; otherwise set it to 0. For every candidate give a `reason` of one or two sentences.

The current spec file:

````markdown
{CURRENT}
````

Old versions (each with the ID it had):

{CANDIDATES}
