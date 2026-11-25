You read one file from a software project, a test or a document, and judge whether anything in it contradicts how the project is meant to behave now. A rule in its area has changed.

What is intended now:

<current>
{CURRENT}
</current>

{RETIRED_BLOCK}The file, `{PATH}`, with its lines numbered. In its comments, docstrings, and prose, the word "requirement" may stand in for the project's own word for a stated rule.

<file>
{FILE}
</file>

Judge three parts of the file against what is intended now:

- **name**: the names of its tests, functions, sections, or headings;
- **comments**: its comments, docstrings, and prose;
- **assertions**: what its checks actually expect (for a document, what it states the behaviour to be).

For each part, say `current` if it agrees with what is intended now, `contradicts` if it states or expects something that conflicts with it (describing or expecting the earlier intent counts), `mixed` if it does both, or `silent` if it says nothing about this rule.

Then give one `verdict` for the file: `current` if every part that speaks of the rule agrees with what is intended now, `stale` if any part contradicts it and nothing in the file corrects that, `mixed` if parts disagree with each other, or `unrelated` if the file doesn't deal with this rule at all.

Return JSON matching the schema you were given: the three parts, the `verdict`, the line numbers your verdict rests on as `evidence` (at least one unless the verdict is `unrelated`), and a `reason` in one or two sentences.
