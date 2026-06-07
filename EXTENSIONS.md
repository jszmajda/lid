# Extensions

Third-party projects that build on Linked-Intent Development — editor integrations, language servers, CLIs, CI coherence checkers, and other tooling the minimal LID core deliberately leaves to the ecosystem.

> **Listing is an editorial showcase, not an endorsement.** The projects below are independent — not maintained, vetted, or run by LID — and a listing is not a security or quality guarantee. Evaluate any extension yourself before use. (LID does adversarial *coherence* review, not security review; see [`SECURITY.md`](SECURITY.md) and the *Not adversarial security review* non-goal in the [HLD](docs/high-level-design.md).)

## Projects

| Project | What it does |
|---|---|
| [**EtaCassiopeia/lid-tooling**](https://github.com/EtaCassiopeia/lid-tooling) | VS Code & IntelliJ extensions, a `lidc` CLI, and an MCP server for LID — LSP diagnostics, a visual Intent Navigator, and `lidc check` for CI. |

## How to get listed / make your extension discoverable

Discovery is by **open convention** — no submission or approval step. To make your project findable:

1. **Tag your repository with the GitHub topic [`linked-intent-development`](https://github.com/topics/linked-intent-development).** That topic page is where people browse the ecosystem; the core LID repository carries it too, so the page is anchored by the source project.
2. **Link back to the core repository** ([`jszmajda/lid`](https://github.com/jszmajda/lid)) from your README, so visitors can trace your project to LID.

That is the whole convention — anyone who follows it is discoverable, listed here or not. To be **featured in the curated list above**, open a pull request adding a row (or an issue) once your project follows the convention.
