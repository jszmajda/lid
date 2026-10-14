# Research: What coding harnesses tell the model about its identity

**Snapshot date: 2026-10-14.** These harnesses ship weekly, and several assemble their prompts server-side where no client build shows them. Specifics drift: Copilot CLI added its identity line in February 2026, opencode's next-generation line already drops it, and Cursor's and Amp's current prompts cannot be read from the client at all. Re-verify any load-bearing fact before reusing it for a new decision.

**Question.** For Claude Code, Cursor, Windsurf (Cascade), GitHub Copilot (Chat in VS Code, and Copilot CLI), OpenAI Codex CLI, Aider, Continue.dev, JetBrains Junie, JetBrains AI Assistant, Zed's agent, Amp, goose, opencode, Gemini CLI, Cline, Roo Code, and Kiro, the question has three parts. First, does the system prompt or injected context tell the executing model which model it is by default: exact model ID, display name, family only, or nothing? Second, does that hold on bring-your-own-model routes (BYO key, OpenRouter, custom or OpenAI-compatible providers)? Third, is the reasoning effort stated? A secondary question: how reliable is a model's self-identification when the harness says nothing? The purpose is LID's capability-flag lookup, where a model matches itself against a table of tested model IDs at a reasoning effort. We need to know whether "use the identity the harness states" is available broadly enough to be the primary signal, and how far a model's own belief can serve as a fallback.

**Method.** This was a multi-agent research run across five angles: vendor CLI agents, closed-source IDE agents, open-source CLI harnesses, open-source IDE extensions, and the self-identification literature. Evidence types, strongest first:

1. **Source code read at tagged releases** for ten open-source harnesses: Codex, opencode, Gemini CLI, Aider, goose, Cline, Roo Code, Continue, Zed, and Copilot Chat (now inside `microsoft/vscode`).
2. **Strings extracted from shipped binaries** for Claude Code 2.1.299, Copilot CLI 1.0.97, and the Amp CLI.
3. **One first-hand wire capture.** Claude Code 2.1.299 was run as `claude -p` against a local mock endpoint over gateway, Bedrock, and Vertex routes.
4. **Vendor docs, changelogs, and staff statements, plus user issue reports.**
5. **Third-party leaked-prompt collections** for the five closed IDE agents (Cursor, Windsurf, Kiro, Junie, JetBrains AI Assistant). None of these leaks is newer than 2025-11-07.
6. **For self-identification:** five measured studies (2024–2026), vendor documents, and harness bug reports.

Only Claude Code was observed on the wire. Every other classification rests on reading code or text that the harness *would* send.

**Answer.** No, the stated identity is not broadly available. Twelve harnesses could be checked against source code or a shipped binary:

- **Four state a machine-style model ID by default:** Claude Code, Copilot CLI (outside Auto mode), opencode 1.x, and Roo Code.
- **Two state only a display name:** Zed and Copilot Chat.
- **One states only the family:** Codex CLI ("an agent based on GPT-6").
- **Five state nothing:** Aider, Continue, goose, Gemini CLI, and Cline.

The five closed IDE agents cannot be verified for 2026. Their newest evidence points to product personas, or to identity withheld on purpose under Auto routing. Where an ID is stated, it is the literal string the harness sends to the provider, such as `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `claude-sonnet-4-5@20250929`, `openrouter/openai/gpt-6.1-sol`, or a raw Bedrock ARN. Matching it against a table therefore needs normalization, and some BYO routes reduce it to a user label or to nothing.

**No harness states reasoning effort in prose. Effort travels only as an API parameter**, so the effort column of LID's lookup cannot be resolved from context in any surveyed harness.

A model's own belief is reliable only at the family level, and only for frontier closed models. Exact version is essentially never known, and errors lean toward older siblings. Open-weight models served over BYO routes often claim to be Claude or ChatGPT, and those routes are exactly where harness disclosure is weakest. The harness line works as the primary signal in Claude Code and opencode, the two harnesses LID's own evidence was gathered in. The fallback should be deterministic ("unknown → untested") rather than self-belief.

## Per-tool disclosure: four of twelve verified harnesses state a machine ID

The table is grouped by what the model is told. "Exact ID" means exact to the request, not a canonical vendor ID.

| Harness | Version checked | What the model is told (default) | BYO-route behavior | Effort stated? | Evidence | Confidence |
|---|---|---|---|---|---|---|
| **Claude Code** | 2.1.299 (2026-10-14) | **Exact ID + display name + knowledge cutoff**, for example `You are powered by the model named Opus 5.5. The exact model ID is claude-opus-5-5. Assistant knowledge cutoff is June 2026.` It is an environment attachment inside a system-role message. It is re-injected when `/model` switches models, and subagents receive it. It is omitted under `CLAUDE_CODE_SIMPLE`, in bare forks, and in isolated contexts. | The ID is the provider's literal string: Bedrock `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, Vertex `claude-sonnet-4-5@20250929`. **Unrecognized IDs degrade to `You are powered by the model <raw ID>.`** with no name and no cutoff. That covers non-Anthropic models behind `ANTHROPIC_BASE_URL`, Bedrock application-profile ARNs, and every Foundry deployment, and in those cases the persona still calls the model "a Claude agent". `modelOverrides` can map an ID to a known model. | No prose; sent as `output_config.effort` | Shipped binary, wire capture, and self-observation; recognition rules in [model-config docs](https://code.claude.com/docs/en/model-config) | High |
| **Copilot CLI** | 1.0.97 (2026-10-13) | **Display name + Copilot catalog ID** when a model is picked: `Powered by <model name="…" id="…" />.` It also tells the model to reply "I'm powered by … (model ID: …)", and it sends a notice when the model is switched. **In Auto mode identity is withheld by design** ("do not name a specific underlying model"), and Free and Student token-billing plans are restricted to Auto. Present since v0.0.415 (2026-02-23). | Untraced for BYO providers (`COPILOT_PROVIDER_TYPE` / `COPILOT_MODEL`). The template sits in vendor-neutral runtime code. | No prose found; sent as a request parameter | Shipped runtime strings, [v0.0.415 notes](https://github.com/github/copilot-cli/releases/tag/v0.0.415), staff comments | High for the template; medium across vendors; BYO unknown |
| **opencode** | v1.19.0 (2026-10-11); opencode2 v2.0.29 | **Exact ID** on every main-loop turn: `You are powered by the model named ${api.id}. The exact model ID is ${providerID}/${api.id}`. The "named" slot carries the API ID, not a display name. This covers plan and build modes, custom agents, and subagents. Present since v1.1.35 (2026-01-25). It is **absent** from compaction and title calls, from the `SessionV2` runtime, and from **the opencode2 v2.0.x line, which drops it** except for Meta "muse" models. | The same on every route, with raw IDs: on OpenRouter the line reads `openrouter/<vendor>/<model>`, and on a custom provider it is the user's `model.id` or config key. Aliases and display names are never used ([#36164](https://github.com/anomalyco/opencode/issues/36164) was closed as not planned). | No; reasoning variants go into request options | Source at tag ([system.ts](https://github.com/anomalyco/opencode/blob/v1.19.0/packages/opencode/src/session/system.ts#L74-L85)) | High for v1; the v2 direction is uncertain |
| **Roo Code** | v3.54.0 (2026-05-15; **repo archived**) | **Exact request ID** in every user turn's `<environment_details>`, as `<model>${modelId}</model>` under `# Current Mode`. It is unconditional in every mode and does not appear in the system prompt. Present since 3.11.16 (2025-04-14). | Holds on every route, literal to the request: an OpenRouter slug, an Anthropic API ID, an Ollama tag, an LM Studio ID, a user-typed OpenAI-compatible string, or a Bedrock ID or ARN. | No | Source at tag ([getEnvironmentDetails.ts](https://github.com/RooCodeInc/Roo-Code/blob/v3.54.0/src/core/environment/getEnvironmentDetails.ts#L204-L227)) | High |
| **Zed agent** | v1.23.3 (2026-10-12) | **Display name** in the system prompt: `## Model Information` followed by `You are powered by the model named {{model_name}}.` It is rebuilt on every request and users cannot override it. Present since [PR #41490](https://github.com/zed-industries/zed/pull/41490) (2025-10-31). This applies to the native agent only; external ACP agents bring their own prompts (inferred). | Holds on every route. Anthropic models use the catalog `display_name`. OpenRouter models use OpenRouter's name with the "Provider:" prefix stripped. Ollama, LM Studio, and OpenAI-compatible models use the configured `display_name`, or else the raw model name or tag. | No | Source at tag ([system_prompt.hbs](https://github.com/zed-industries/zed/blob/v1.23.3/crates/agent/src/templates/system_prompt.hbs#L214-L219)) | High |
| **Copilot Chat (VS Code)** | VS Code 1.141.1, `extensions/copilot` 0.69.0 | **Display name, phrased as a conditional**: "When asked about the model you are using, you must state that you are using {name}." It is sent on every request in Ask, Edit, and Agent modes. **GPT-5.5, GPT-5.6, GPT-6, and one hidden family are told to say only "I am GitHub Copilot."** The hidden "familyH" and MiniMax families receive both lines, which conflict. The `chat.omitBaseAgentInstructions` setting drops the line. Present since [PR #1267](https://github.com/microsoft/vscode-copilot-chat/pull/1267) (2025-10-16). | Holds on BYO routes, using the provider's name field (Anthropic `display_name`, OpenRouter `name`, Ollama model info) or the user's configured `name` for custom endpoints. Auto mode was not traced. | No | Source at tag ([copilotIdentity.tsx](https://github.com/microsoft/vscode/blob/1.141.1/extensions/copilot/src/extension/prompts/node/base/copilotIdentity.tsx#L9-L26)) | High (read from source, not run) |
| **Codex CLI** | rust-v0.162.1 (2026-10-09) | **Family only** for OpenAI catalog models: "You are Codex, an agent based on GPT-6." or "…based on GPT-5." The catalog has a `display_name`, but no template uses it. A model switch injects the new model's instructions, not its slug. | The family line appears only when the slug prefix-matches an OpenAI catalog entry; one namespace segment may be stripped first. Third-party slugs (Claude, Llama, Ollama) get **no identity**. The remote catalog used under ChatGPT auth was not inspected. | Not for itself; it lists the efforts of models it can *spawn* | Source at tag ([models.json](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/models-manager/models.json#L76)) plus issues | High for the bundled catalog |
| **Aider** | main 5dc9490 (2026-05-22), identical to v0.86.0 | **None**. The prompt opens "Act as an expert software developer." Model name, think tokens, and effort are printed to the *user* only. | The same on every litellm route. The per-model `system_prompt_prefix` is user-settable. | No (shown to the user only) | Source ([base_coder.py](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L207-L230)) | High |
| **Continue.dev** | v2.1.0-vscode (2026-06-19) | **None**; the prompt states the mode only ("You are in agent mode."). The `cn` CLI's `<env>` block has no model either. | Nothing on any route. Users can add an identity line through per-model `baseAgentSystemMessage` overrides. | No | Source ([defaultSystemMessages.ts](https://github.com/continuedev/continue/blob/v2.1.0-vscode/core/llm/defaultSystemMessages.ts#L51-L91)) | High |
| **goose** | v1.54.0 (2026-10-08) | **None**; harness persona only ("…an AI agent called goose…"). The model name is read only to compute a context-remaining hint. | The same across providers; a full prompt override is supported. | No | Source ([prompt_manager.rs](https://github.com/aaif-goose/goose/blob/v1.54.0/crates/goose/src/agents/prompt_manager.rs#L126-L135)) | High |
| **Gemini CLI** | v0.64.0 (2026-10-13) | **None**: "You are Gemini CLI…" plus the approval mode. The active model only chooses between the modern and legacy prompt snippets. | No identity on any route. `GEMINI_SYSTEM_MD` replaces the whole prompt. | No (approval mode only) | Source ([snippets.ts](https://github.com/google-gemini/gemini-cli/blob/v0.64.0/packages/core/src/prompts/snippets.ts#L185-L195)) | High |
| **Cline** | v4.1.24 (2026-10-13), both the "Next" and "Legacy" bundles | **None**. The `<env>` block has platform, date, IDE, and working directory. The Legacy bundle computes a `MODEL_FAMILY` token that no template renders. | Nothing on any route. In an open issue, DeepSeek running under Cline answers "I'm Claude, built by Anthropic" ([#11914](https://github.com/cline/cline/issues/11914)). | No (`reasoningConfig` is a request parameter) | Source ([act.ts](https://github.com/cline/cline/blob/v4.1.24/sdk/packages/shared/src/prompt/system/act.ts#L1-L13)) | High |
| **Cursor (agent)** | Closed source; leaks 2024-12 to 2025-11; staff statement April 2026 | **2025 leaks: display name** for a picked model ("You are an AI coding assistant, powered by GPT-5. You operate in Cursor."). **Auto and Composer get a product label** ("Auto" or "Composer"), not the routed model, and Composer is told it is "not gpt-4/5, grok, gemini, claude". What a picked model is told in 2026 is unknown. | BYOK requests pass through Cursor's servers "for final prompt building", so presumably they are treated the same as hosted models. | No evidence | Leaks, [staff statement](https://forum.cursor.com/t/cursor-using-or-reporting-wrong-model/156654), [docs](https://cursor.com/docs/settings/api-keys) | Low to medium |
| **Windsurf (Cascade)** | Closed source; leaks 2024-12 to 2025-07 | **Persona only** ("You are Cascade…"). One July 2025 leak adds an on-request answer: "respond with `GPT 4.1`". 2026 behavior unknown. | No evidence | No evidence (the model catalog sells thinking variants) | [Leaks](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Windsurf/Prompt%20Wave%2011.txt); docs say nothing | Low |
| **Kiro** | Closed source; leak 2025-07; issues through 2026-10 | The 2025 leak gives a **persona only** ("You are Kiro…"). The prompt carries a hard-coded knowledge cutoff that is identical for Claude, Qwen, and MiniMax. An unfilled `{{model:name}}` variable leaked in November 2025. One May 2026 report has a correct self-report of "Claude Sonnet 4.5". **Overall: unknown**, leaning toward none or family only. | No BYOK route found. Auto mode hides the model even from users. | No evidence; `effortLevel` is a session option | [Leak](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Kiro/Vibe_Prompt.txt), [user issues](https://github.com/kirodotdev/Kiro/issues/3667) | Low |
| **JetBrains Junie** | Closed source; one ask-mode leak (2025-05-17) | **None** in that leak ("Your name is Junie."). The current agent and CLI are unknown. | BYOK (Anthropic, OpenAI, Google, xAI, OpenRouter, Copilot). Prompt behavior is undocumented. | No evidence | [Single leak](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Junie/Prompt.txt), [README](https://github.com/JetBrains/junie) | Low |
| **JetBrains AI Assistant** | 2026.2 docs (2026-07-28) | **Unknown**; no leak exists. | Supports OpenAI-compatible endpoints, Ollama, and LM Studio. User Prompt Library system prompts are the only documented way to inject anything. | No evidence | [Docs only](https://www.jetbrains.com/help/ai-assistant/use-custom-models.html) | Very low |
| **Amp** | CLI build 0.0.1791964847 (npm 2026-10-14) | **Unknown** for 2026: the client binary contains no main system prompt, because the prompt is assembled server-side. The September 2025 dumps show **none**: the environment section lists date, working directory, OS, and repo, and model questions are sent to the online manual. Only the oracle tool's model is named. The mode "dial" picks the model, the effort, and a per-mode prompt. | Amp picks the model per mode. Its "Claude Code" mode runs the Claude Agent SDK, which presumably carries Claude Code's identity line (unverified). | No evidence | Binary (negative result), [2025 dumps](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Amp), [The Dial](https://ampcode.com/news/the-dial) | Low |

## Cross-cutting findings: identity is route-literal, requested rather than served, and silent on effort

### "Exact ID" means the request string, and the same model looks different in every harness

The four harnesses that state an ID each print the string they hand to the provider, not a canonical name. A table keyed on bare IDs such as `claude-sonnet-4-5` or `openai/gpt-6.1-sol` must normalize before it can match. The strings below come from the wire capture, from source, or from issue reports. The OpenRouter row uses the source-level pattern with an illustrative ID.

| Harness and route | What the model sees | Normalization needed to hit a bare table ID |
|---|---|---|
| Claude Code, first-party or gateway | `You are powered by the model named Sonnet 4.5. The exact model ID is claude-sonnet-4-5-20250929.` | Strip the date suffix |
| Claude Code, Bedrock | `…The exact model ID is us.anthropic.claude-sonnet-4-5-20250929-v1:0.` | Strip the region and vendor prefix, the date, and `-v1:0` |
| Claude Code, Vertex | `…The exact model ID is claude-sonnet-4-5@20250929.` | Strip `@date` |
| Claude Code, Bedrock application profile or Foundry | `You are powered by the model arn:aws:bedrock:us-east-1:…:application-inference-profile/….` | **Cannot be resolved** |
| Claude Code, non-Anthropic gateway | `You are powered by the model deepseek-v4-pro.` The persona text still says "Claude agent". | Match as-is and ignore the persona |
| opencode, native Anthropic provider | `…named claude-sonnet-4-20250514. The exact model ID is anthropic/claude-sonnet-4-20250514` | Strip the date from the "named" slot |
| opencode, OpenRouter | `…named openai/gpt-6.1-sol. The exact model ID is openrouter/openai/gpt-6.1-sol` | The "named" slot already matches OpenRouter-form rows |
| Roo Code | `<model>claude-3-7-sonnet-20250219</model>`, an OpenRouter slug, or an Ollama tag | Depends on the route |
| Copilot CLI | `Powered by <model name="…" id="claude-sonnet-4.5" />.` (Copilot catalog form, inferred from issue reports; no capture) | Change dots to dashes |
| Zed, Copilot Chat | A display name, an OpenRouter name, or a user label | Needs a per-row display-name alias list |
| Codex CLI | `You are Codex, an agent based on GPT-6.` | None possible; family only |

Claude Code also gives the model a second channel that can disagree with the first: the commit trailer `Co-Authored-By: Claude Sonnet 4.5`. For unrecognized models the trailer becomes `Claude Code`. Read the ID sentence, not the trailer.

### The stated identity is the requested model, and routers and wrappers break it

Every identity line reflects the model the harness *asked for*. Products that route requests either withhold the identity on purpose or state the wrong one:

- **Copilot CLI's Auto mode** tells the model not to name itself.
- **Cursor** gives Auto and Composer sessions a product label. Its staff say "The name the model reports has no correlation with which model is actually handling your request" ([Cursor forum](https://forum.cursor.com/t/cursor-using-or-reporting-wrong-model/156654)).
- **Kiro's Auto mode** does not even show *users* the model ([kirodotdev/Kiro#8903](https://github.com/kirodotdev/Kiro/issues/8903)).
- **Remapping produces confidently wrong lines.** Roo once printed `<model>claude-3-7-sonnet-20250219</model>` while the user ran DeepSeek-R1 through a relay provider ([Roo-Code#2706](https://github.com/RooCodeInc/Roo-Code/issues/2706)).
- **Subagents can drift silently.** Copilot CLI subagents can run a different model "with no surfacing" ([copilot-cli#3824](https://github.com/github/copilot-cli/issues/3824)). Codex subagents running `gpt-5.6-sol` inherited a parent's "based on GPT-6" instructions and identified as GPT-6 ([codex#44598](https://github.com/openai/codex/issues/44598)).

Claude Code and opencode do put the line in subagent contexts, which matters for LID's inspectors and other subagents.

### A wrong line is believed and defended

In Claude Code issue #64848, the harness injected a stale "Opus 4.7" line while Opus 4.8 was selected. The model "in good faith disputes the user's own UI evidence ... since the system prompt is the only identity signal the model has" ([anthropics/claude-code#64848](https://github.com/anthropics/claude-code/issues/64848)). The 2.1.299 template is now computed from the live model ID and re-sent on every switch, so this class of bug is likely addressed, but that is not confirmed.

Persona text competes with the ID line. With `ANTHROPIC_BASE_URL` pointed at DeepSeek, the model answered "I am Claude Opus 4.8 by Anthropic" ([anthropics/claude-code#69067](https://github.com/anthropics/claude-code/issues/69067)). Today's capture shows the raw `deepseek-v4-pro` ID sitting next to the "Claude agent" persona, so the ID is present and the conflict remains. Copilot Chat sends its hidden "familyH" and MiniMax families two contradictory instructions, and no capture shows which one wins.

### Identity lines are recent, reactive, and not monotonic

Each identity line was added after users reported misidentification:

- Roo Code: April 2025
- Copilot Chat: October 16, 2025
- Zed: October 31, 2025
- opencode: January 25, 2026
- Copilot CLI: February 23, 2026

Before Copilot CLI's line existed, GitHub staff said: "I wouldn't trust how the model self-reports, we haven't done anything in our prompts to ensure that it says the right thing here!" ([copilot-cli#131](https://github.com/github/copilot-cli/issues/131)).

The trend also runs the other way. opencode2 drops the line, Copilot Chat withholds the name from its newest OpenAI families, and Auto routing is spreading. More harnesses now name the model when the *user* picks it. When the *product* picks it, more of them hide it.

### No harness states reasoning effort to the model

This holds across all twelve source-verified harnesses. Effort is sent only as a request parameter:

- **Claude Code.** The wire capture shows `"output_config": {"effort": "xhigh"}` for Opus 5.5 and `"thinking": {"budget_tokens": 31999}` for Sonnet 4.5, with no prose about either. Claude Code's docs say `ultrathink` "adds an in-context instruction" while "the effort level sent to the API is unchanged" ([model-config docs](https://code.claude.com/docs/en/model-config)).
- **Codex.** Effort levels appear only to describe models and roles that the parent agent could spawn ([role.rs](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/core/src/agent/role.rs#L298-L331)).
- **Aider.** The effort is printed to the user, never to the model.
- **The closed IDE agents.** They sell effort tiers, but no leaked prompt states one.

One low-confidence lead goes against this. A Claude Code researcher saw a numeric reasoning-effort marker in its own context. That would be the API platform's doing, not the harness's, and it was a single observation.

## Self-identification: family yes, version no, and errors lean older or toward Claude

Measured studies agree that self-knowledge gets worse as the question gets more specific.

**Family is reliable for frontier closed models.** In "Know Thyself?" (2025), ten models were queried through OpenRouter. All but one named their family correctly 100% of the time. The exception was GLM-4.5, which said "Claude" in half of its rollouts ([arXiv:2510.03399](https://arxiv.org/html/2510.03399v1)).

**Exact version is essentially never known.** On SAD's FACTS-NAMES task, models were "never knowing their precise version… and mostly not knowing their model class" ([arXiv:2407.04694](https://arxiv.org/abs/2407.04694)). The best score was 29% (Claude 2.1), and the authors note that always answering "Claude" would have scored 33%. No study measures exact-ID self-report for 2026 frontier models. None measures size-tier self-knowledge (Haiku vs. Sonnet vs. Opus) either.

**Cross-vendor claims concentrate in open-weight and distilled models.** In "I'm Spartacus", 7 of 27 models showed identity confusion, mostly about who built them ([arXiv:2411.10683](https://arxiv.org/abs/2411.10683)). STEMMA (August 2026) probed models adversarially and drew direct wrong-identity claims at strict rates from 0% to 82% ([arXiv:2608.08164](https://arxiv.org/html/2608.08164)):

- MiniMax-M2.5: 82%
- Qwen3.5-Plus: 74%
- GPT-5.4-Nano, Grok-4.1-fast, Llama-3.3-70B: near zero

Newer releases resisted better: Kimi fell from 61% to 11%, and Qwen from 74% to 14%. STEMMA used only 12 prompts and an LLM judge. Anthropic also alleges large-scale distillation of Claude by DeepSeek, Moonshot, and MiniMax ([InfoWorld](https://www.infoworld.com/article/4136468/anthropic-alleges-large-scale-distillation-campaigns-targeting-claude.html)). If true, that explains why these lines claim Claude so often, but it remains an allegation.

**Within a vendor line, self-reports lean older.** The harness bug trackers show the same pattern again and again:

- **Claude:** Sonnet 3.7, 4, and 4.5 and Opus 4.1 called themselves "Claude 3.5 Sonnet" in Claude Code, Cline, Kiro, Cursor, and Copilot CLI ([claude-code#1294](https://github.com/anthropics/claude-code/issues/1294), [cline#6646](https://github.com/cline/cline/issues/6646), [Kiro#583](https://github.com/kirodotdev/Kiro/issues/583), [copilot-cli#131](https://github.com/github/copilot-cli/issues/131)).
- **Codex:** `gpt-5.6-sol` answered "based on GPT-5.5" ([codex#36872](https://github.com/openai/codex/issues/36872)), and `gpt-6-astra` reported GPT-5.5 ([codex#45245](https://github.com/openai/codex/issues/45245)).
- **Gemini CLI:** Gemini 2.5 Pro believed it was 1.5 Pro ([gemini-cli#4636](https://github.com/google-gemini/gemini-cli/issues/4636)).

The likely mechanism is that training data names a model's predecessors but rarely the model itself.

**A model may reject its own unfamiliar name.** GPT-5 "sometimes treated 'gpt-5' as a fake name, given its knowledge cutoff" ([Know Thyself?](https://arxiv.org/html/2510.03399v1)). One Claude Code model called its own correctly injected identity "non-existent" because the identity postdated its training ([claude-code#37706](https://github.com/anthropics/claude-code/issues/37706)).

**In-context identity overrides trained belief.** GPT-4o's identity association was M = 0.989 with a true identity cue and M = 0.001 under a false "You are Claude Sonnet" cue. Asked "Which version of Claude are you?", GPT-4o and Gemini 2.0 Flash "readily answered that they were Claude 2.0" ([Lehr et al., arXiv:2509.26464](https://arxiv.org/html/2509.26464v2)). For a lookup, this cuts both ways. A correct harness line wins, and a wrong one is believed just as completely. Text in the repository that names a model, such as a capability table listing `claude-sonnet-4-6`, is plausible anchoring material. That last point is inferred from the suggestibility results, not measured.

**Vendors do not rely on trained-in identity for their own apps.** Anthropic's claude.ai prompt states "This iteration of Claude is Claude Sonnet 5.5". It also lists the current model strings and warns that "earlier messages in this thread that identify as a different model … may still be accurate". Anthropic notes that these app prompts "do not apply to the Claude API" ([Anthropic system prompts](https://platform.claude.com/docs/en/release-notes/system-prompts/claude-sonnet-5-5)). Ecosystem guidance is consistent: check the API response's `model` field, not what the model says ([Microsoft Q&A](https://learn.microsoft.com/en-us/answers/a/1344070); [OpenAI Community](https://community.openai.com/t/does-chatgpt-really-know-which-model-i-use-in-api/290795)).

## What a tested-model lookup can read from context

A lookup that matches the executing model against a table of tested model IDs at a reasoning effort can draw on these inputs, by where each occurs by default:

| What is in context | Where it occurs by default | What it supports |
|---|---|---|
| Exact-ID line | Claude Code, opencode 1.x, Roo Code, Copilot CLI (picked model) | A match after normalizing route prefixes and suffixes. The line holds even when the model does not recognize the name. |
| Raw ID that cannot be resolved (ARN, Foundry deployment, Ollama tag, user label) | Claude Code for unrecognized IDs; Roo, Zed, and Copilot Chat on custom routes | No match |
| Display name only | Zed, Copilot Chat, Cursor (picked models, as of the 2025 leaks) | A match only against a known display-name alias |
| Family only | Codex CLI | No match to a specific row |
| Identity withheld, or a product label | Copilot CLI Auto ("Auto mode is active"), Cursor Auto and Composer, Copilot Chat on GPT-5.5/5.6/6, persona-only prompts | No match |
| Nothing | Aider, Continue, goose, Gemini CLI, Cline; likely Windsurf, Junie, and Amp | No match; self-belief reaches family level at best |
| Reasoning effort | No surveyed harness | Cannot be read from context |

**The exact-ID line covers the harnesses LID's own evidence came from, and few others.** LID's tested rows come from Claude Code and from `opencode-ai@1.18.32`, and both inject an exact-ID line; v1.18.32 carries it, confirmed at the tag ([system.ts @v1.18.32](https://github.com/anomalyco/opencode/blob/v1.18.32/packages/opencode/src/session/system.ts#L76)). Over OpenRouter, opencode's "named" slot carries the `<vendor>/<model>` form, the same form as OpenRouter-style table IDs such as `z-ai/glm-5.3-flash` (inferred from source, not captured). Claude Code's first-party IDs match bare Anthropic IDs once a date suffix is dropped; Bedrock and Vertex forms need prefixes and suffixes stripped. Outside those two harnesses, coverage is thin:

- **Cursor**, a host that reads LID's plugins, is unverifiable for 2026, and it hides identity in Auto.
- **Roo Code** is archived.
- **Copilot CLI** reports a dotted catalog ID, and nothing in Auto.
- **Five widely used harnesses** state nothing at all.

**Self-belief fails in a direction that matters for a lookup.** A model that knows it is untested is easy to handle. A model that wrongly believes it is a tested model is not. Behind a Claude Code gateway, DeepSeek answered "I am Claude Opus 4.8 by Anthropic" ([#69067](https://github.com/anthropics/claude-code/issues/69067)); placed by that belief, it would read Opus 4.8's row. The stated line in the same session read `deepseek-v4-pro`. Cross-vendor impersonation concentrates in open-weight models on bring-your-own routes, which is where harness lines are absent or degraded. Within a vendor line, by contrast, mistaken self-reports name an *older* sibling.

**Comparing a stated ID against sibling IDs meets irregular naming:**

- dated and undated IDs side by side (`claude-haiku-4-5-20251001` vs. `claude-sonnet-4-6`)
- dots vs. dashes (Copilot's `claude-sonnet-4.5`)
- vendor and router prefixes
- named tiers such as Fable or Wonder that do not order numerically

No study measures whether a model told its own ID orders it correctly against sibling IDs (open question 9).

**The effort axis cannot be resolved from context anywhere.** No surveyed harness states effort in prose, so a model asked for "the reasoning effort you run at" cannot read it; it can only assume or guess. The single lead about an Anthropic-platform effort marker would, if confirmed, cover Claude on first-party routes only, and it would arrive as a number, not a named level.

## Refuted or unverified claims (do not rely on)

1. **"Codex gives third-party and routed models an explicit identity instruction ('You are a coding agent powered by <model-id>…')"** ([codex#47961](https://github.com/openai/codex/issues/47961)). A grep of rust-v0.162.1 found no such string. If it exists, it comes from a remote catalog or the reporter's proxy.
2. **Codex's per-model prompt files** ("You are GPT-5.1 running in the Codex CLI…") are dead files at rust-v0.162.1: no code references them. They do not describe current behavior.
3. **"Cursor gives Claude models just the word 'Claude'"** (Cursor-side responder, July 2025). This conflicts with the June 2025 leak "powered by Claude Sonnet 4". It is unresolved, and either may be mode-specific.
4. **Kiro "never call yourself Kiro, say you are Claude"** comes from a secondary report of a 2026 leak ([80aj.com](https://www.80aj.com/2026/06/21/ai-kiro-prompt-leak-claude/)). The primary source was not fetched, and the claim conflicts with the 2025 leak.
5. **A JetBrains AI Assistant line "You are working powered by <provider-model> model"** is an unsourced recollection. Targeted searches found nothing.
6. **The "Knowledge cutoff: 2024-06 / Image input capabilities: Enabled" lines in Cursor leaks** are probably OpenAI platform preamble that the model regurgitated, not text Cursor wrote.
7. **Template slots that look like identity but are never rendered:** Cline's `MODEL_FAMILY` token, Zed's `experimental_system_prompt.hbs` model block, and Amp's "INSTRUCTIONS FOR LLMs" page blocks. The last describes Amp the product, not the model's own identity.
8. **The opper.ai "AI Roundtable" self-identification poll** had a platform system prompt present and some implausible answers. It is illustrative only.
9. **Amp's Claude Code mode inherits Claude Code's identity line.** This is presumed from architecture and not verified inside Amp.

## Open questions

1. Does Copilot CLI emit `Powered by <model …>` for BYO providers (`COPILOT_MODEL`), and what does it print for a catalog miss?
2. What do Cursor, Windsurf, Kiro, Junie, and JetBrains AI Assistant tell a *picked* model in 2026? No leak is newer than 2025-11-07.
3. What does Amp's server-assembled main-agent prompt contain in 2026?
4. Is opencode2's removal of the identity line deliberate, and which clients use the line-less `SessionV2` endpoints?
5. In Claude Code: does a real Bedrock account resolve application-profile ARNs to a name? Do `ANTHROPIC_DEFAULT_*_MODEL_NAME` overrides change the identity line? Do `--system-prompt` replacement or `--bare` suppress it?
6. Does Codex's remote `/models` catalog, used under ChatGPT auth, carry identity text that the bundled catalog lacks?
7. Does any API platform surface reasoning effort inside the model's context, as the single Claude observation suggests, and in what form?
8. In Copilot Chat's Auto mode, does the model see the resolved model's name or an "Auto" label? For familyH and MiniMax, which of the two conflicting lines wins?
9. How accurately do 2026 frontier models report their exact ID with an empty system prompt, and can a model told its own ID order it correctly against sibling IDs? No study measures either.

## Key sources

Primary, read from source or binary: opencode [system.ts](https://github.com/anomalyco/opencode/blob/v1.19.0/packages/opencode/src/session/system.ts#L74-L85) · Codex [models.json](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/models-manager/models.json) and [manager.rs](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/models-manager/src/manager.rs#L865-L926) · Roo Code [getEnvironmentDetails.ts](https://github.com/RooCodeInc/Roo-Code/blob/v3.54.0/src/core/environment/getEnvironmentDetails.ts#L204-L227) · Zed [system_prompt.hbs](https://github.com/zed-industries/zed/blob/v1.23.3/crates/agent/src/templates/system_prompt.hbs#L214-L219) · Copilot Chat [copilotIdentity.tsx](https://github.com/microsoft/vscode/blob/1.141.1/extensions/copilot/src/extension/prompts/node/base/copilotIdentity.tsx) · Cline [cline.ts](https://github.com/cline/cline/blob/v4.1.24/sdk/packages/shared/src/prompt/cline.ts#L140-L212) · Continue [defaultSystemMessages.ts](https://github.com/continuedev/continue/blob/v2.1.0-vscode/core/llm/defaultSystemMessages.ts) · Gemini CLI [snippets.ts](https://github.com/google-gemini/gemini-cli/blob/v0.64.0/packages/core/src/prompts/snippets.ts) · goose [prompt_manager.rs](https://github.com/aaif-goose/goose/blob/v1.54.0/crates/goose/src/agents/prompt_manager.rs) · Aider [base_coder.py](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py) · Claude Code 2.1.299 binary plus wire capture (first-hand) · [@github/copilot 1.0.97](https://www.npmjs.com/package/@github/copilot) · [@ampcode/cli](https://www.npmjs.com/package/@ampcode/cli)

Vendor docs and changelogs: [Claude Code model config](https://code.claude.com/docs/en/model-config) · [Copilot CLI v0.0.415](https://github.com/github/copilot-cli/releases/tag/v0.0.415) · [Cursor available models](https://cursor.com/help/models-and-usage/available-models) and [API keys](https://cursor.com/docs/settings/api-keys) · [Anthropic system prompts](https://platform.claude.com/docs/en/release-notes/system-prompts) · [Amp: The Dial](https://ampcode.com/news/the-dial) · [JetBrains custom models](https://www.jetbrains.com/help/ai-assistant/use-custom-models.html)

Issues and staff statements: anthropics/claude-code [#64848](https://github.com/anthropics/claude-code/issues/64848), [#69067](https://github.com/anthropics/claude-code/issues/69067), [#37706](https://github.com/anthropics/claude-code/issues/37706) · github/copilot-cli [#131](https://github.com/github/copilot-cli/issues/131), [#3824](https://github.com/github/copilot-cli/issues/3824) · openai/codex [#47961](https://github.com/openai/codex/issues/47961), [#44598](https://github.com/openai/codex/issues/44598) · [cline#11914](https://github.com/cline/cline/issues/11914) · [Roo-Code#2706](https://github.com/RooCodeInc/Roo-Code/issues/2706) · [Cursor forum 156654](https://forum.cursor.com/t/cursor-using-or-reporting-wrong-model/156654) · kirodotdev/Kiro [#3667](https://github.com/kirodotdev/Kiro/issues/3667), [#8903](https://github.com/kirodotdev/Kiro/issues/8903)

Studies: [SAD, arXiv:2407.04694](https://arxiv.org/abs/2407.04694) · [Know Thyself?, arXiv:2510.03399](https://arxiv.org/html/2510.03399v1) · [STEMMA, arXiv:2608.08164](https://arxiv.org/html/2608.08164) · [I'm Spartacus, arXiv:2411.10683](https://arxiv.org/abs/2411.10683) · [Lehr et al., arXiv:2509.26464](https://arxiv.org/html/2509.26464v2)

Leaked prompts (lower confidence, all from 2025 or earlier): [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) · [elder-plinius/CL4R1T4S](https://github.com/elder-plinius/CL4R1T4S) · [jujumilk3/leaked-system-prompts](https://github.com/jujumilk3/leaked-system-prompts)
