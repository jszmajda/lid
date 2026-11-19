You have some files from a software system and nothing else: no other code, no other documents, and no one to ask. {SOURCE_NOTE}

Write down the system's current rules: what it does, and what it must and must not do, as these files show it.

- **One rule per entry, in plain product language.** Say what a person using the system would notice, not how the code is organised. Name a function, field, endpoint, or message only when the rule is about it.
- **Cite what each rule rests on.** Give each rule one or more citations: `path::test_name` for a test, `path § heading` for a section of a document, or the `path` alone. Use the paths exactly as the files below are headed.
- **Only what the files support.** Don't add rules you would expect such a system to have, defaults the files don't show, or guesses about intent the files leave open.
- **Where the files show two rules that can't both hold, write both,** each with its own citations.
- **One behaviour per rule.** Split independent behaviours into separate rules, and merge rules that say the same thing.
- **Cover everything the files show,** the edge cases and limits as well as the main features.
- **Write only the rules:** nothing about these instructions, about the files themselves, or about how you read them.

The files:

{FILES}
