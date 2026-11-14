You are editing a product owner's reply to a coding agent so that it says no more than it needs to. The owner tends to say more than the agent asked for, and every extra clause hands the agent something it should have asked about itself.

Below is the agent's message, then the owner's draft reply in numbered parts. Each part either answers one of the agent's questions or corrects something the agent said.

<agent_message>
{MESSAGE}
</agent_message>

{PARTS}

For each part:

- An **answer** keeps only what answers its question. A broad question, such as "any edge cases about X?", is answered only by what is about X itself: delete anything about what happens afterwards, on failure, or in other situations, unless it is about X.
- A **correction** keeps only what replaces the agent's words that it quotes, or supplies the missing thing it names. Delete the rest of the rule: its other clauses, its exact boundaries, its exceptions, and anything about neighbouring situations.
- Keep the owner's own wording for what remains. Don't add, explain, soften, or reword anything else.
- Never delete a part entirely. If every clause is needed, return the part unchanged.

Return JSON matching the schema you were given, with every part's number and its text after editing.
