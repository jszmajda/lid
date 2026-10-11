# Coach sampling strategy

Read when the project has more than 15 LLDs or more than 200 files carrying `@spec` annotations, or when the arrow-maintenance overlay (`docs/arrows/index.yaml`) is present.

Two rules:

1. **Arrow-path sampling for large projects.** When the project has **more than 15 LLDs OR more than 200 files carrying `@spec` annotations**, sample at least one complete arrow path per arrow segment — HLD section → LLD → at least one EARS spec → at least one test citing that spec → at least one code file citing that spec. End-to-end sampling is the only way to catch drift where one level of an arrow disagrees with another (specs that read well but have no implementation; code that exists for behaviors that have no spec; LLD claims contradicted by the code that's supposed to satisfy them). Below those thresholds, sampling depth is judgment — skim broadly, dig where the principle body suggests drift might live.

2. **`docs/arrows/index.yaml` is your guide when present.** When the arrow-maintenance overlay is installed, the index enumerates segments and carries `status`, `audited`, `audited_sha`, `next`, and `drift` fields per segment — direct evidence of what the project itself thinks is in flight. **Read the index first.** Use it to pick which segments to arrow-path-sample, and which segments to dig into for cascade-health findings. The index's drift fields feed directly into findings — a segment whose `drift` field has been non-null across multiple samplings is itself a signal worth surfacing.
