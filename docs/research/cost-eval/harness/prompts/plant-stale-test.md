You write one automated test for a software project, in the same language, framework, and style as its existing tests. A sample of them follows.

<existing_tests>
{SAMPLE}
</existing_tests>

The test checks this rule, as though it were how the software is meant to behave:

<rule>
{RULE}
</rule>

Write the test so that its assertions encode the rule: a reader who sees only what the test calls and what it expects, with every name and comment hidden, should still be able to tell what rule it checks. Use the same imports, helpers, and conventions as the sample, and give the test a name and a comment that describe the rule plainly. The test will be read, never run, so it needn't pass against the current code. Don't mention that the rule is old, changed, or added, and don't use identifiers that aren't in the project's style.

Return JSON matching the schema you were given: `file_name` (a file name in the project's convention for test files, without a folder) and `text` (the whole file).
