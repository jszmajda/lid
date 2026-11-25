You are editing a product owner's reply to a coding agent so that it says no more than it needs to. The owner tends to say more than the agent asked for, and every extra clause hands the agent something it should have asked about itself.

Below is the agent's message, then the owner's draft reply in numbered parts. Each part either answers one of the agent's questions or corrects something the agent said.

<agent_message>
{MESSAGE}
</agent_message>

{PARTS}

For each part:

- An **answer** keeps only what answers its question.
- A **correction** keeps only what replaces the agent's words that it quotes, or supplies the missing thing it names. Delete the rest of the rule: its other clauses, its exact boundaries, its exceptions, and anything about neighbouring situations.
- A clause that starts with "including", "also", "even", "still", "unless", "whatever", "or if", or "not only", and a consequence that starts with "so" ("so one already under way still counts"), usually add a case the agent didn't raise. Delete them unless the question or the quoted words mention that case.
- A list of the things a rule covers, such as "(opening hours, delivery area, payment, …)", keeps only the entries the question names or the quoted words got wrong.
- When an answer confirms what the agent proposed ("Yes", "That's right", "That matches"), keep only the confirmation and delete any restatement of the proposal, above all one that mentions a case the proposal didn't.
- If a correction's quoted words are correct as far as they go, and the correction only adds something they left out, return `DROP` as that part's text: it isn't a correction.
- Keep the owner's own wording for what remains. Don't add, explain, soften, or reword anything else.
- Never delete an answer entirely. If every clause is needed, return the part unchanged.

Return JSON matching the schema you were given, with every part's number and its text after editing.
