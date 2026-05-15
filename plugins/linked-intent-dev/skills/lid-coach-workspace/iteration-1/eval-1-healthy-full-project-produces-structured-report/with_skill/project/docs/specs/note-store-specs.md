# Note Store specs

**LLD**: docs/llds/note-store.md

## Creation

- `[x]` **NOTE-STORE-001**: When the user creates a note, the system SHALL write the note file to the notes directory and append a create event to the event log.
- `[x]` **NOTE-STORE-002**: When the user deletes a note, the system SHALL remove the note file and append a delete event to the event log.
