# Asciinema Cascade Demo — Recording Script

**Purpose**: capture a ~2-minute terminal recording of an LID cascade in a real project, for embedding on the marketing site (`MKT-SITE-003`).

**Target**: `/Users/jess/src/lid-example/` (Rust implementation of the `examples/urlshort/` specs — single crate, axum + rusqlite, tests inline via `#[cfg(test)]`).

*Worth noting out loud*: this project was originally Go. The implementation swapped to Rust without the LLDs or EARS specs changing — intent was the source, code was the output, and the output was recompiled into a different language. That's the English-compiler claim made tangible. You might mention it in the recording's outro if you want a nice meta-beat.

---

## 1. Pre-flight checklist

Run once, before you're ready to record. These are annoying to redo mid-recording.

```bash
# Install asciinema (macOS)
brew install asciinema

# Optional: link a free asciinema.org account so casts are persistent.
# Uploads without auth expire after 7 days.
asciinema auth
# (paste the URL into a browser, log in with GitHub)
```

Terminal prep — keeps the recording legible when embedded:

- **Font size**: bump to 14–16pt so the embed at ~720px wide is still readable.
- **Terminal dimensions**: resize to ~100 cols × 30 rows. The recording captures exact geometry; smaller terminals embed poorly.
- **Color scheme**: dark background with high-contrast text. Avoid patterned backgrounds.
- **Shell prompt**: a short prompt renders best. Consider a temporary `PS1='$ '` for the recording.
- **Clear scrollback** and **`clear`** the screen before recording.

Project prep in `lid-example/`:

- `git status` should be clean (or only show changes you intend to demo).
- Claude Code installed; `claude` runs.
- LID plugins installed: `/plugin list` should show `linked-intent-dev` and `arrow-maintenance`.
- `cargo test` should currently pass.
- Keep this script open in another window as a reference — don't try to memorize.

---

## 2. The scenario: add a max URL length

**What to demo**: add a 2048-character cap on incoming URLs at the API layer — reject longer ones with HTTP 400 and a clean error body. Additive, not breaking. One LLD, one new EARS spec, one new test, a handful of lines in the handler.

**Why this scenario fits**: the change stays inside one arrow segment (`api.md` / `api-specs.md` / `internal/api/`). No cross-boundary pause needed, so the cascade runs clean in a single ~2-minute pass. The motivation is also legible to a cold viewer — "don't let abusive clients send MB-scale URLs" — so there's no setup needed.

**Real files the demo will touch** (verified against `/Users/jess/src/lid-example/`):

- `docs/llds/api.md` — LLD for the HTTP surface
- `docs/specs/api-specs.md` — EARS specs, prefix `USH-API-NNN`
- `src/api.rs` — axum handlers + inline `#[cfg(test)]` tests in the same file

The project's other arrow segments (`shortener-core`, `storage`) stay untouched in this demo — on purpose, so the viewer sees a *bounded* cascade, not a sprawling one.

---

## 3. The 2-minute script

**0:00 — Start recording**

```bash
cd ~/src/lid-example
asciinema rec ~/Desktop/cascade-demo.cast \
  --idle-time-limit=2 \
  --cols=100 \
  --rows=30 \
  --title="LID cascade: add a max URL length"
```

`--idle-time-limit=2` compresses any pause longer than 2 seconds in the replay (keeps the embed tight).

**0:00–0:12 — Orient the viewer**

```bash
clear
ls docs/llds/
head -30 docs/llds/api.md
```

Viewer sees: a real project, an LLD that describes the HTTP API in prose.

**0:12–0:22 — Show the current arrow is green**

```bash
grep -c "@spec" src/api.rs                     # some number > 0 (≈21 today)
cargo test --lib api::                         # module tests pass
```

The "before" state: specs and code are linked, tests pass.

**0:22–0:32 — Start Claude Code**

```bash
claude
```

Wait for the TUI to settle. Paste (don't type — paste is cleaner in the recording):

> add a 2048-character cap on incoming urls at the API layer. longer urls should respond with HTTP 400 and an error body. cascade through the arrow.

Press enter.

**0:32–1:10 — Agent cascades**

The `linked-intent-dev` skill takes over. Roughly:

1. Agent reads `docs/llds/api.md` and `docs/specs/api-specs.md` to orient.
2. Proposes an LLD edit (new paragraph on length-cap behavior). Pauses for your approval. **Approve.**
3. Proposes a new EARS spec — the next available `USH-API-NNN` — codifying the 400 response. Pauses. **Approve.**
4. Reports an intent-narrowing edge audit: "one new spec, no cross-segment bleed, no sibling-spec collisions."

The pauses are the point. Let them render.

**1:10–1:45 — Tests-first, then code**

5. Agent writes a new test inside the `#[cfg(test)] mod tests` block in `src/api.rs`, citing the new spec ID via `// @spec USH-API-NNN`. Runs it — it fails as expected (no validation yet).
6. Updates the POST `/shorten` handler in `src/api.rs` with the length check.
7. Re-runs `cargo test --lib api::`. Green.

Resist scrolling. Let the agent finish the loop.

**1:45–1:55 — Show the result**

Exit Claude (`/exit` or Ctrl+C twice):

```bash
git diff --stat
cargo test --lib api::
```

Viewer sees: a small, bounded diff across LLD, spec, test, handler. Tests green.

**1:55–2:00 — Close**

```bash
echo "one intent change. one spec. cascaded in minutes."
```

Ctrl+D to stop the recording.

---

## 4. Post-recording

Preview the cast to catch issues before upload:

```bash
asciinema play ~/Desktop/cascade-demo.cast
```

If pacing is wrong, re-record (it's short). If acceptable, upload:

```bash
asciinema upload ~/Desktop/cascade-demo.cast
```

Asciinema returns a URL like `https://asciinema.org/a/XXXXXX`. Visit it, click **Share**, copy the `<script>` embed snippet. It looks like:

```html
<script src="https://asciinema.org/a/XXXXXX.js" id="asciicast-XXXXXX" async></script>
```

Paste into `site/src/index.njk`, replacing the `.demo-placeholder` block:

```html
<section class="demo section" aria-labelledby="demo-heading">
  <div class="container">
    ...
    <div class="demo-frame">
      <span class="demo-plate"><span class="num">001</span>CASCADE · LLD → SPECS → TESTS → CODE</span>
      <script src="https://asciinema.org/a/XXXXXX.js" id="asciicast-XXXXXX" async></script>
    </div>
  </div>
</section>
```

Then mark `MKT-SITE-003` in `docs/specs/marketing-site-specs.md` as `[x]`, and this planning doc can move to `docs/planning/old/`.

---

## 5. Alternative scenarios

Same flow, different prompt. All grounded in the real `lid-example` code:

- **Unknown-code 404 body** — `USH-API-007` currently specifies a plain-text "Short code not found." body on unknown codes. Switch to a JSON error body (`{ "error": "not_found", "code": "<the code>" }`). One spec revision, one test update, one handler tweak in `src/api.rs`. **Smallest cascade** — good if you want to keep the demo especially tight.
- **Response field rename** — rename the response field `short_url` → `share_url` (response-only; request shape unchanged). Touches `docs/llds/api.md`, `USH-API-001` and `USH-API-011` in `api-specs.md`, the `serde` rename attribute on the response struct in `src/api.rs`, and the inline tests. **Scoped to the API layer**, a bit more to watch than the primary scenario.
- **Case-normalized short codes** — currently case-sensitive (`USH-API-009`). Switch to uppercase-canonical with case-insensitive lookup. Touches `api-specs.md`, `shortener-core-specs.md`, and both `src/api.rs` and `src/core.rs`. **Largest cascade** — crosses arrow boundaries, so the skill will pause at the `api ↔ shortener-core` seam. Demonstrates the pause-at-boundary discipline if you want the extra beat.

Same recording flow, different prompt. The primary scenario (max URL length) is the recommended starting point; these are available if you record once and want a second take at a different scope.

---

## 6. Tips that make the demo land

- **Don't type the prompt live.** Have it in another window and paste it. Typos in the embedded cast are distracting and the paused recording is fine (idle compression handles it).
- **Pick a single cascade.** Don't try to demo two changes or handle a surprise. The point is *one clean sweep*.
- **Accept that Claude's output will vary.** The skill's wording changes across runs. That's actually good — it proves the workflow, not a scripted output.
- **If something goes wrong**, don't keep going hoping the viewer won't notice. Ctrl+C, `clear`, start again. Re-records are free.
- **Keep the terminal geometry stable** once you start recording. Resizing mid-cast breaks the replay.

---

## 7. Tracking

- `MKT-SITE-003` — current status `[ ]`. Flip to `[x]` after the embed ships.
- `MKT-SITE-035` — "when skill behavior changes materially, re-record the asciinema demo before the next deploy." The cast is a cascade-dependent artifact; treat it like any other downstream artifact of the plugin LLDs.
