# Security Policy

## Scope

LID ships **no executable application code**. It is a methodology plus a set of Claude Code plugins — Markdown skills, prompts, and documentation — together with the static marketing-site build under `site/`. Nothing in LID runs as a service or installed binary on your machine as part of using the methodology.

Because of that, the usual software-vulnerability surface (memory safety, injection into a running service, CVEs in a shipped binary) does not apply to the core project. The realistic concerns are:

- **Prompt content in skills.** Once installed, the plugins are instructions an agent executes with your privileges, so prompt content that could steer an agent toward unsafe actions is the most relevant surface.
- **Build and tooling dependencies** of the marketing site under `site/`.

## Reporting a vulnerability

Please report privately rather than opening a public issue:

- Use GitHub's [**Report a vulnerability**](https://github.com/jszmajda/lid/security/advisories/new) flow (the repository's **Security → Advisories** tab), or
- Email the maintainer: **jess.szmajda@gmail.com**

Include enough detail to understand and, where applicable, reproduce the issue. We will acknowledge your report and follow up with a fix or mitigation.

## Out of scope

A vulnerability in a **downstream project that used LID to design itself** is that project's own security concern, not LID's. LID performs adversarial *coherence* review — checking that intent and implementation stay aligned — not adversarial *security* review (threat modeling, penetration testing, vulnerability analysis). That boundary is intentional; see the **Not adversarial security review** non-goal in [`docs/high-level-design.md`](docs/high-level-design.md).
