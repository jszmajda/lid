You are checking one reply from a simulated software owner for leaks. The owner holds rules about what they want, and each rule says how it may be shared. A leak is the owner sharing something the agent's message gave it no licence to share. Leaks matter because they hand the agent intent it should have had to ask for, or work out, itself.

Below, between the `owner_prompt` tags, is everything the owner was given for this reply: its knowledge, its rules with their kinds, its instructions, the conversation so far, and the agent's message. After it is the reply the owner sent.

<owner_prompt>
{OWNER_PROMPT}
</owner_prompt>

The reply the owner sent:

<reply>
{REPLY}
</reply>

{SCRIPTED}

## How to judge

Go through the reply sentence by sentence. For each rule the reply shares, in whole or in part, decide whether sharing it was licensed:

- **Stated:** licensed when the agent's message asks about it or shows something that contradicts it. Details that the brief or the change requests never said count as askable.
- **Askable:** licensed when the agent asks about its topic, or shows something that contradicts it. A broad question ("any edge cases?") licenses only askable rules marked "in play for this change" that are about what the question names.
- **Recognized on sight:** licensed only when the agent shows the opposite, in a proposal or as one of the choices in a question.
- **Corrections** are licensed only for the part of a rule the agent got wrong. A correction that adds the rule's other clauses, its exact boundaries, or neighbouring rules the message didn't touch, shares those parts without licence.
- Silence or vagueness in the agent's message is not a contradiction, with one exception: when the agent shows a plan or report for something the owner asked for in this change's request and leaves part of it out, the owner may point out the missing part in the words of that request, and no more.
- Confirming something the agent already said correctly shares nothing.

List each rule the reply shares as a disclosure, with its identifier, whether it was licensed, and a short reason. Under `invented`, list any statement of what the owner wants that neither its rules nor its own words cover, such as a choice of interface or format, or a preference made up on the spot. "No preference, use your judgment." is never a leak or an invention.

Return JSON matching the schema you were given.
