#!/usr/bin/env python3
"""B10: run a full audit arm (3A+3B+classifier per unit) on an OpenAI model.

Mirrors the frozen prompts in audit-prompts.md exactly, except file access:
API models cannot read the filesystem, so B-direction and classifier calls get
slice file CONTENTS embedded (protocol asymmetry recorded in RESULTS methods).

Usage:
  openai_arm_driver.py --units grid-units.json --arm T3 --model gpt-5.6-terra \
      --unit-ids id1,id2,... --out-dir runs-t3/ [--concurrency 4]
"""
import argparse, json, pathlib, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).parent
FIXTURE = (HERE / "FIXTURE-DESCRIPTION.txt").read_text().strip()
CALL = HERE / "openai_call.py"

A_TMPL = """{fixture}

You are given ONLY the EARS requirement below. Respond directly from the requirement text alone. (Attempt {i} — independent.)

EARS {spec}: "{text}"

Produce: a concise Rust implementation sketch (a function or small module) that implements exactly this requirement. Make reasonable assumptions; explicitly list EVERY assumption you had to invent (type shapes, edge cases around invalid/boundary input, defaults, fallback behavior). If the EARS is ambiguous, state which interpretation you chose and why. Keep it under 400 words. Your final message is consumed as raw data by a harness, not read by a human."""

B_TMPL = """{fixture}

(Attempt {i} — independent.) You are given ONLY the following files (full contents below) — consider nothing else:
{files}

Among other concerns, these files implement: {topic}. Reconstruct the EARS-style requirement(s) (patterns: ubiquitous / event-driven / state-driven / unwanted-behavior) that this code ENFORCES for that specific concern, written the way a spec author would state them in a requirements doc. Include every behavior the code pins — including behavior pinned only by tests — that a requirements doc should state: exact constants, tie-break rules, normalization, error semantics, boundary handling. Do not speculate beyond what the code and tests show. Keep it under 400 words. Your final message is consumed as raw data by a harness, not read by a human."""

C_TMPL = """You are the classification step of a bidirectional differential audit (B9/B10 protocol). {fixture}

The REAL EARS requirement {spec}: "{text}"

The real implementing code and tests (full contents below):
{files}

Below are 3 independent A-direction outputs (implementation sketches written from the EARS text ALONE) and 3 independent B-direction outputs (EARS reconstructions written from the code ALONE).

Direction semantics:
- Direction A = SPEC-SIDE SURPLUS: the spec states or forces something the code does not honor — behavior the A-outputs implement because the spec text states it but the real code lacks it, or a sub-decision the spec leaves open, forcing the A-outputs to invent. IMPORTANT: distinguish spec-traced behavior from inventions — A-side behavior that traces to explicit spec text and is missing from the real code IS a finding; unanimous A-side behavior with NO basis in the spec text is an assumption artifact, NOT a finding.
- Direction B = CODE-SIDE SURPLUS: the code+tests enforce behavior (constants, tie-breaks, normalization, error semantics, boundaries) that the spec text never states — visible by comparing the B-outputs against the REAL EARS text above.
- BD = both directions surface the same or related gap.

Classification is the RELATIONSHIP between the two signals, not either alone:
- BD-COHERENT: neither direction surfaces anything material.
- A-ONLY-DRIFT: A-side surplus only.
- B-ONLY-DRIFT: B-side surplus only.
- BD-DRIFT: both directions surface the same or related gap.
- INCONSISTENT-BLIND: runs within a direction disagree too much to classify.

{blocks}

Classify, then list each concrete drift finding ORDERED STRONGEST-FIRST. Respond ONLY with a JSON object:
{{"classification":"BD-COHERENT|A-ONLY-DRIFT|B-ONLY-DRIFT|BD-DRIFT|INCONSISTENT-BLIND","findings":[{{"direction":"A|B|BD","description":"what the spec text says vs what the code+tests actually pin, naming exact constants/rules"}}],"stability":{{"aAgreement":"low|medium|high","bAgreement":"low|medium|high"}},"notes":"..."}}"""


def call(model, prompt, out_path, max_tokens):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        pf = f.name
    r = subprocess.run([sys.executable, str(CALL), "--model", model, "--prompt-file", pf,
                        "--out", str(out_path), "--max-tokens", str(max_tokens)],
                       capture_output=True, text=True)
    pathlib.Path(pf).unlink(missing_ok=True)
    if r.returncode != 0:
        return None
    return json.load(open(out_path))


def embed(files):
    parts = []
    for p in files:
        parts.append(f"===== FILE: {p.split('/crates/')[-1]} =====\n{open(p).read()}")
    return "\n\n".join(parts)


def run_unit(u, arm, model, out_dir):
    ud = out_dir / u["unitId"]
    ud.mkdir(parents=True, exist_ok=True)
    files = embed(u["sliceFiles"])
    gen = []
    for i in (1, 2, 3):
        r = call(model, A_TMPL.format(fixture=FIXTURE, i=i, spec=u["specId"], text=u["specText"]),
                 ud / f"a-run-{i}.json", 4000)
        gen.append(r["text"] if r else "(run failed)")
    for i in (1, 2, 3):
        r = call(model, B_TMPL.format(fixture=FIXTURE, i=i, files=files, topic=u["topic"]),
                 ud / f"b-run-{i}.json", 4000)
        gen.append(r["text"] if r else "(run failed)")
    blocks = "\n\n".join(f"[{'A'+str(i+1) if i < 3 else 'B'+str(i-2)}]\n{g}" for i, g in enumerate(gen))
    c = call(model, C_TMPL.format(fixture=FIXTURE, spec=u["specId"], text=u["specText"],
                                  files=files, blocks=blocks), ud / "classification.json", 6000)
    ok = c is not None
    print(f"[{arm}] {u['unitId']}: {'done' if ok else 'CLASSIFIER FAILED'}", flush=True)
    return {"unitId": u["unitId"], "specId": u["specId"], "kind": u["kind"], "arm": arm,
            "model": model, "ok": ok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--unit-ids", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    units = json.load(open(a.units))
    want = set(a.unit_ids.split(","))
    sel = [u for u in units if u["unitId"] in want]
    missing = want - {u["unitId"] for u in sel}
    if missing:
        sys.exit(f"unknown unit ids: {missing}")
    out_dir = pathlib.Path(a.out_dir)
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        results = list(ex.map(lambda u: run_unit(u, a.arm, a.model, out_dir), sel))
    (out_dir / "arm-summary.json").write_text(json.dumps(results, indent=2))
    bad = [r["unitId"] for r in results if not r["ok"]]
    print(f"{a.arm} complete: {len(results) - len(bad)}/{len(results)} units ok" + (f"; FAILED: {bad}" if bad else ""))


if __name__ == "__main__":
    main()
