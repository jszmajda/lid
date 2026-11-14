Please write a product brief for a service called ReleaseDesk, in the voice of the person who runs a small archive. They are handing it to a developer who will build the service. Use only the material below.

## What you have to work with

**Who and why.** We are a small local-history archive publishing letters, notes, and other text records for public use. Archive staff use ReleaseDesk to prepare records, review their contents, and manage their release. Visitors use the public side to find material and download text attachments.

**What the archive's records contain.** This is only a list of what the archive keeps; it implies no rules:

- Catalog records and their identifiers
- Descriptive information, including titles and display labels
- Plain-text attachments
- Content versions and their identifiers
- Folders and folder membership
- Release-date information for records and folders
- The archive’s time-zone setting
- Staff identities
- Approvals and approval history
- Takedown information
- Staff-only notes and internal provenance
- Bundle requests and bundle identifiers
- Activity history

**The owner's up-front rules.** These are the only rules the owner has decided to put in the brief:

- Staff can ingest plain-text attachments together with structured descriptive information.
- Staff can organize records into folders and move records between folders.
- Staff can edit a record’s descriptive information.
- Staff can add a distinguishable content version to an existing record without creating a separate catalog record.
- Staff can record approval of a specific content version.
- Approval of a version does not by itself authorize replacement text with different contents.
- Public access to a text attachment requires both approval of that content version and satisfaction of its embargo.
- When no release date applies, a record remains embargoed, because records often arrive before staff have decided when they can open.
- A release date begins at local midnight in the archive’s time zone.
- A staff takedown blocks publication even when release dates and approvals would otherwise permit it.
- Public visitors can search the catalog.
- Public-facing information must not expose staff-only notes, internal provenance, or private reasons for access decisions.
- Public visitors can request ZIP bundles containing text attachments from multiple records.
- When a public visitor creates a bundle, only attachments available to that visitor at that time may be included.
- Staff can review a record’s content versions and approval history.

**Fixed operating requirements.** Our IT team needs these, exactly:

- Use Python 3.12, FastAPI, and SQLite.
- One command, documented in the README, starts the service.
- All of the service’s data lives in one location that the start command uses.
- The service reads the current time from the system clock.
- Staff and public callers are told apart by a simple simulated identity, not real authentication.

## How to write it

- Write in the first person, as the archive's owner. Sound like a capable person explaining what they need to a developer they trust, not like a specification.
- Open with what ReleaseDesk is for and who uses it.
- Explain the up-front rules in the owner's own words, grouped the way an archivist would think about them. Every rule must be there, with its meaning unchanged. Some rules are worded loosely on purpose, so don't tighten them, resolve them, or add examples or edge cases that go beyond them.
- Don't add any rule, behaviour, or example of behaviour that isn't in the material. In particular, don't say anything about how approvals relate to who uploaded something, what happens after a takedown ends, what the public sees while a new version waits, which edits need approval, how bundle files are named, release manifests, what happens to bundles after they're made, how dates are counted beyond local midnight, collections or folders being shown or hidden publicly, or how search words combine.
- Don't describe an interface: no endpoints, field names, status codes, or data formats. The developer designs the interface. Say what the archive needs to be able to do, not how the software exposes it.
- Mention that the archive's existing records and staff need to get into the system, without saying how.
- End with the fixed operating requirements in a short section of their own, stated exactly as given.
- Aim for about 500 to 800 words.
- Don't use "shall" or formal requirement phrasing, and don't number the rules.
- Don't mention testing, grading, a study, or AI, and don't name any development method or tool beyond the stack above.

Reply with the brief in Markdown and nothing else.
