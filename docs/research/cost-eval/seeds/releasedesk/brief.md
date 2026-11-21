# ReleaseDesk

We run a small local-history archive publishing letters, notes, and other text records for public use. I’m commissioning ReleaseDesk so our staff have a dedicated place to prepare records, review their contents, and manage their release, and so visitors on the public side have a straightforward way to find material and download text attachments.

To give you a picture of what we keep, our holdings and day-to-day records cover catalog records and their identifiers, descriptive information including titles and display labels, plain-text attachments, and content versions and their identifiers. We also keep folders and folder membership, release-date information for records and folders, and the archive’s time-zone setting. Alongside the material itself, we keep staff identities, approvals and approval history, takedown information, staff-only notes and internal provenance, bundle requests and bundle identifiers, and activity history. We already have existing records and staff, and they will need to get into the system.

### Preparing and Organizing Records

Our work starts with bringing material in and keeping it well described and arranged. In ReleaseDesk, staff need to be able to ingest plain-text attachments together with structured descriptive information. Staff can edit a record’s descriptive information, and they can organize records into folders and move records between folders. A record can carry a release date of its own, and a folder can carry one for the records in it.

Staff can also add a new content version to an existing record without creating a separate catalog record.

### Review, Approvals, and Release Timing

Staff need to be able to review a record’s content versions and approval history, and they can record approval of a specific content version. Approval of a version does not by itself authorize replacement text.

Public access to a text attachment requires both approval of that content version and satisfaction of its embargo. Because records often arrive before staff have decided when they can open, when no release date applies, a record remains embargoed. A release date begins at local midnight in the archive’s time zone. Staff can also take a record down: a staff takedown blocks publication even when release dates and approvals would otherwise permit it.

### Public Search and Downloads

On the public side, visitors can search the catalog to find material. Public-facing information must not expose staff-only notes, internal provenance, or private reasons for access decisions.

Visitors often want to gather attachments across several records at once, so public visitors can request ZIP bundles containing text attachments from multiple records. When a public visitor creates a bundle, only attachments available to that visitor at that time may be included.

### Fixed Operating Requirements

Finally, our IT team has a set of fixed operating requirements that we need as-is:

- Use Python 3.12, FastAPI, and SQLite.
- One command, documented in the README, starts the service.
- All of the service’s data lives in one location that the start command uses.
- The service reads the current time from the system clock.
- Staff and public callers are told apart by a simple simulated identity, not real authentication.
