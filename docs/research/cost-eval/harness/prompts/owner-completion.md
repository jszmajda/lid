You read one message that a coding agent wrote to the person it is working for, at the end of a turn on a change the person asked for.

<agent_message>
{MESSAGE}
</agent_message>

Does the message report the change as done, or does it announce work still to do on it?

- **done**: it reports the work as finished. It may summarise what it did, say the tests pass, list caveats, or offer extras the person didn't ask for ("if you'd like, I can also…").
- **work to do**: it says what the agent will do next on this change (a next phase or step, code or tests it is about to write, something it will run), or it asks for the go-ahead before carrying on.

Return JSON matching the schema you were given: the `verdict`, and a `quote`: the words in the message that show it, copied exactly.
