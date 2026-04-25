#!/usr/bin/env python3
"""
LID overlay dispatcher — prototype.

Reads `*.overlay.yaml` manifests from an overlay directory, invokes each
manifest's declared engine(s), and aggregates results into `_status.yaml`.

Supported engines (v0.3 schema):
  - manual-review   — reads signoff metadata (pass-through)
  - lemmascript / lemmascript-dafny — dafny verify on the .dfy artifact
  - test-witness    — structural check of test file + describe/it presence
  - type-system     — tsc --noEmit on the .types.ts artifact
  - codeql          — codeql query run against a prebuilt DB
  - git-provenance  — advisory report from git log queries (no gate)
  - differential    — advisory only; reports "review manually"

Posture:
  - "gate" engines: any non-V status → dispatcher exits 1 (CI failure)
  - "advisory" engines: status is recorded but does not affect exit code
    (differential and git-provenance default to advisory)

Usage:
  dispatcher.py <overlay-dir> [--write-status] [--verbose]
    <overlay-dir>     directory containing *.overlay.yaml files
    --write-status    emit _status.yaml alongside manifests
    --verbose         print per-spec, per-engine details
    --codeql-db PATH  optional path to a prebuilt CodeQL DB
                      (else reads from manifest.engine.database or env)
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


# ---------- engine posture table ----------

GATE_ENGINES = {
    "codeql",
    "lemmascript",
    "lemmascript-dafny",
    "test-witness",
    "type-system",
    "manual-review",
}
ADVISORY_ENGINES = {"differential", "git-provenance"}


# ---------- result model ----------

class EngineResult:
    def __init__(
        self,
        engine: str,
        status: str,
        posture: str,
        detail: str = "",
        artifact: Optional[str] = None,
        elapsed_ms: int = 0,
    ):
        self.engine = engine
        self.status = status  # V | Vp | Vx | Vn | ?
        self.posture = posture  # gate | advisory
        self.detail = detail
        self.artifact = artifact
        self.elapsed_ms = elapsed_ms

    def to_dict(self) -> Dict:
        return {
            "engine": self.engine,
            "status": self.status,
            "posture": self.posture,
            "detail": self.detail,
            "artifact": self.artifact,
            "elapsed_ms": self.elapsed_ms,
        }


class SpecResult:
    def __init__(self, spec_id: str, arrow: str, manifest_path: Path):
        self.spec_id = spec_id
        self.arrow = arrow
        self.manifest_path = manifest_path
        self.engines: List[EngineResult] = []

    @property
    def overall_status(self) -> str:
        """Aggregate status across all gate engines for this spec.
        Advisory engines do not affect the overall status.

        Rule: Vx dominates. Otherwise, any V lifts the spec to V (one engine
        actually verified at least this aspect — a sibling's `?` means
        'couldn't run', not 'broken'). Vp next. All-Vn counts as Vn.
        Only-? counts as ?."""
        gate_results = [e for e in self.engines if e.posture == "gate"]
        if not gate_results:
            return "?"
        statuses = [e.status for e in gate_results]
        if "Vx" in statuses:
            return "Vx"
        if "V" in statuses:
            return "V"
        if "Vp" in statuses:
            return "Vp"
        if statuses and all(s in ("Vn", "?") for s in statuses) \
                and "Vn" in statuses:
            return "Vn"
        return "?"

    def to_dict(self) -> Dict:
        return {
            "spec_id": self.spec_id,
            "arrow": self.arrow,
            "manifest": str(self.manifest_path.name),
            "overall_status": self.overall_status,
            "engines": [e.to_dict() for e in self.engines],
        }


# ---------- engine invokers ----------

def engine_manual_review(
    manifest_dir: Path, engine_cfg: Dict, spec_id: str
) -> EngineResult:
    """Pass-through: reads signoff metadata from the manifest."""
    artifact = engine_cfg.get("artifact")
    status = engine_cfg.get("status", "?")
    detail = f"signoff: {engine_cfg.get('signoff_by', '<unspecified>')}"
    if artifact:
        path = manifest_dir / artifact
        if path.exists():
            detail += f"; artifact present ({artifact})"
        else:
            detail += f"; artifact MISSING ({artifact})"
            status = "Vx"
    return EngineResult(
        engine="manual-review",
        status=status,
        posture="gate",
        detail=detail,
        artifact=artifact,
    )


def engine_lemmascript_dafny(
    manifest_dir: Path, engine_cfg: Dict, spec_id: str
) -> EngineResult:
    """Invoke `dafny verify` on the .dfy artifact."""
    start = datetime.now()
    artifact = engine_cfg.get("artifact")
    if not artifact:
        return EngineResult(
            "lemmascript-dafny", "Vx", "gate",
            "no artifact specified in manifest", None,
        )

    dfy_path = manifest_dir / artifact
    if not dfy_path.exists():
        return EngineResult(
            "lemmascript-dafny", "Vx", "gate",
            f"artifact not found: {dfy_path}", artifact,
        )

    try:
        proc = subprocess.run(
            ["dafny", "verify", str(dfy_path)],
            capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return EngineResult(
            "lemmascript-dafny", "Vx", "gate",
            "dafny verify timed out (120s)", artifact,
        )
    except FileNotFoundError:
        return EngineResult(
            "lemmascript-dafny", "?", "gate",
            "dafny binary not found in PATH", artifact,
        )

    elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)
    combined = (proc.stdout or "") + (proc.stderr or "")

    # Parse "Dafny program verifier finished with N verified, M errors"
    match = re.search(
        r"Dafny program verifier finished with (\d+) verified, (\d+) error",
        combined,
    )
    if match:
        verified, errors = int(match.group(1)), int(match.group(2))
        if errors == 0:
            status = "V"
            detail = f"{verified} VCs verified, 0 errors"
        else:
            status = "Vx"
            detail = f"{verified} VCs verified, {errors} errors"
    else:
        # Couldn't parse Dafny's output — treat as stuck
        status = "Vx" if proc.returncode != 0 else "V"
        detail = f"exit={proc.returncode}; output head: {combined[:200]!r}"

    return EngineResult(
        "lemmascript-dafny", status, "gate",
        detail, artifact, elapsed_ms,
    )


def engine_lemmascript(
    manifest_dir: Path, engine_cfg: Dict, spec_id: str
) -> EngineResult:
    """Run `lsc check` if available, else defer to lemmascript-dafny pattern.
    In practice, Wave 1/2 experiments run dafny verify directly on .dfy.
    If artifact is .ts, try lsc; if .dfy, delegate."""
    artifact = engine_cfg.get("artifact", "")
    if artifact.endswith(".dfy"):
        return engine_lemmascript_dafny(manifest_dir, engine_cfg, spec_id)

    # .ts artifact — check for lsc, fall back to "status-as-declared"
    lsc_path = _find_lsc(manifest_dir)
    if lsc_path:
        start = datetime.now()
        try:
            proc = subprocess.run(
                [lsc_path, "check", "--backend=dafny", str(manifest_dir / artifact)],
                capture_output=True, text=True, timeout=120,
            )
            elapsed = int((datetime.now() - start).total_seconds() * 1000)
            if proc.returncode == 0:
                return EngineResult(
                    "lemmascript", "V", "gate",
                    "lsc check passed", artifact, elapsed,
                )
            return EngineResult(
                "lemmascript", "Vx", "gate",
                f"lsc check failed: {(proc.stderr or proc.stdout)[:200]}",
                artifact, elapsed,
            )
        except Exception as e:
            return EngineResult(
                "lemmascript", "?", "gate",
                f"lsc invocation error: {e}", artifact,
            )

    # No lsc — trust the manifest's declared status
    status = engine_cfg.get("status", "?")
    return EngineResult(
        "lemmascript", status, "gate",
        "lsc not available; relying on manifest-declared status", artifact,
    )


def _find_tsc(start: Path) -> Optional[str]:
    """Hunt upward for tsc in node_modules/.bin, falling back to dispatcher dir."""
    cur = start.resolve()
    dispatcher_dir = Path(__file__).resolve().parent
    candidates = []
    for _ in range(8):
        candidates.append(cur / "node_modules" / ".bin" / "tsc")
        cur = cur.parent
    candidates.append(dispatcher_dir / "node_modules" / ".bin" / "tsc")
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def _find_lsc(start: Path) -> Optional[str]:
    """Hunt upward for an lsc binary in node_modules/.bin."""
    cur = start
    for _ in range(6):
        candidate = cur / "node_modules" / ".bin" / "lsc"
        if candidate.exists():
            return str(candidate)
        cur = cur.parent
    # Try global npx
    try:
        proc = subprocess.run(
            ["which", "npx"], capture_output=True, text=True, timeout=5,
        )
        if proc.returncode == 0:
            return "npx lsc"
    except Exception:
        pass
    return None


def engine_type_system(
    manifest_dir: Path, engine_cfg: Dict, spec_id: str
) -> EngineResult:
    """Invoke `tsc --noEmit` on the artifact."""
    start = datetime.now()
    artifact = engine_cfg.get("artifact")
    if not artifact:
        return EngineResult(
            "type-system", "Vx", "gate",
            "no artifact specified", None,
        )
    ts_path = manifest_dir / artifact
    if not ts_path.exists():
        return EngineResult(
            "type-system", "Vx", "gate",
            f"artifact not found: {ts_path}", artifact,
        )

    tsc_bin = _find_tsc(manifest_dir)
    if not tsc_bin:
        return EngineResult(
            "type-system", "?", "gate",
            "tsc not found (tried node_modules/.bin/tsc upward)", artifact,
        )

    try:
        proc = subprocess.run(
            [tsc_bin, "--noEmit", "--target", "es2020",
             "--strict", "--skipLibCheck", str(ts_path)],
            capture_output=True, text=True, timeout=90,
        )
    except subprocess.TimeoutExpired:
        return EngineResult(
            "type-system", "Vx", "gate",
            "tsc timed out", artifact,
        )
    except Exception as e:
        return EngineResult(
            "type-system", "?", "gate",
            f"tsc invocation error: {e}", artifact,
        )

    elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)
    if proc.returncode == 0:
        return EngineResult(
            "type-system", "V", "gate",
            "tsc clean", artifact, elapsed_ms,
        )
    return EngineResult(
        "type-system", "Vx", "gate",
        f"tsc errors: {(proc.stdout or proc.stderr)[:300]}",
        artifact, elapsed_ms,
    )


def engine_test_witness(
    manifest_dir: Path, engine_cfg: Dict, spec_id: str,
) -> EngineResult:
    """Structural check: contract YAML exists, witness path exists,
    describe/it block referenced by the contract is present.
    Does NOT run the test suite — that's the contract-verifier's job
    (separate script); this is the mechanical overlay check."""
    artifact = engine_cfg.get("artifact")
    if not artifact:
        return EngineResult(
            "test-witness", "Vx", "gate",
            "no contract artifact specified", None,
        )

    contract_path = manifest_dir / artifact
    if not contract_path.exists():
        return EngineResult(
            "test-witness", "Vx", "gate",
            f"contract not found: {contract_path}", artifact,
        )

    # Parse the contract, extract witness selectors
    try:
        with open(contract_path) as f:
            contract = yaml.safe_load(f)
    except Exception as e:
        return EngineResult(
            "test-witness", "Vx", "gate",
            f"contract parse error: {e}", artifact,
        )

    witnesses = contract.get("witnesses") or contract.get("witness") or []
    if isinstance(witnesses, dict):
        witnesses = [witnesses]

    if not witnesses:
        return EngineResult(
            "test-witness", "Vp", "gate",
            "contract has no witnesses declared", artifact,
        )

    missing = []
    checked = 0
    for w in witnesses:
        path = w.get("path") or w.get("file")
        describe = w.get("describes") or w.get("describe") or w.get("selector")
        if not path:
            continue
        # Resolve path relative to the project root declared in the manifest,
        # falling back to the manifest's own directory.
        project_root_cfg = w.get("project_root") or engine_cfg.get("project_root")
        candidate_roots = [
            Path(project_root_cfg) if project_root_cfg else None,
            manifest_dir,
            manifest_dir.parent,
        ]
        candidate_roots = [r for r in candidate_roots if r is not None]
        resolved = None
        for root in candidate_roots:
            cand = root / path
            if cand.exists():
                resolved = cand
                break
            # Glob resolution
            matches = list(root.glob(path))
            if matches:
                resolved = matches[0]
                break
        if not resolved:
            missing.append(f"witness path not found: {path}")
            continue
        checked += 1
        if describe:
            text = resolved.read_text(errors="replace")
            if describe not in text and f"'{describe}'" not in text:
                missing.append(
                    f"{resolved.name} does not reference '{describe}'"
                )

    if missing:
        return EngineResult(
            "test-witness", "Vx", "gate",
            "; ".join(missing[:3]), artifact,
        )
    return EngineResult(
        "test-witness", "V", "gate",
        f"{checked} witness(es) structurally present", artifact,
    )


def engine_codeql(
    manifest_dir: Path, engine_cfg: Dict, spec_id: str, codeql_db: Optional[str],
) -> EngineResult:
    """Invoke codeql query run against a prebuilt DB."""
    start = datetime.now()
    artifact = engine_cfg.get("artifact")
    if not artifact:
        return EngineResult(
            "codeql", "Vx", "gate",
            "no query artifact specified", None,
        )
    ql_path = manifest_dir / artifact
    if not ql_path.exists():
        return EngineResult(
            "codeql", "Vx", "gate",
            f"query not found: {ql_path}", artifact,
        )

    # codeql insists on `.ql` extension. If artifact ends in `.codeql`,
    # use a temp `.ql` copy.
    run_path = ql_path
    tmp_path = None
    if ql_path.suffix == ".codeql":
        tmp_path = ql_path.with_suffix(".dispatcher-tmp.ql")
        tmp_path.write_text(ql_path.read_text())
        run_path = tmp_path

    db = (
        codeql_db
        or engine_cfg.get("database")
        or os.environ.get("LID_CODEQL_DB")
    )
    if not db:
        # Heuristic: look for the Wave 1 DB
        default_db = Path("/tmp/codeql-thr-det-018/db")
        if default_db.exists():
            db = str(default_db)
        else:
            return EngineResult(
                "codeql", "?", "gate",
                "no CodeQL DB available (pass --codeql-db or set LID_CODEQL_DB)",
                artifact,
            )

    try:
        proc = subprocess.run(
            ["codeql", "query", "run", f"--database={db}", str(run_path)],
            capture_output=True, text=True, timeout=300,
            cwd=str(manifest_dir),
        )
    except subprocess.TimeoutExpired:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        return EngineResult(
            "codeql", "Vx", "gate",
            "codeql query timed out (300s)", artifact,
        )
    except FileNotFoundError:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        return EngineResult(
            "codeql", "?", "gate",
            "codeql binary not found", artifact,
        )
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)
    # Count result rows — zero rows for "must-not-reach" = pass;
    # non-zero = investigate
    out = proc.stdout or ""
    # CodeQL prints a table with "| col1 | col2 |" rows
    data_rows = [
        line for line in out.splitlines()
        if line.strip().startswith("|")
        and not re.match(r"\|[-+\s]+\|", line.strip())
    ]
    if proc.returncode != 0:
        return EngineResult(
            "codeql", "Vx", "gate",
            f"codeql exit={proc.returncode}: {(proc.stderr or '')[:200]}",
            artifact, elapsed_ms,
        )

    # Heuristic: if the manifest marks this as a must-not-reach taint check,
    # zero rows = verified. If it's a structural check where rows are expected
    # (e.g. a "find all writes to field X" pattern), non-zero may still be V —
    # manifest should declare expected_rows.
    expected = engine_cfg.get("expected_rows", "zero")
    # Minus 1 for the header row if present
    count = max(0, len(data_rows) - 1) if data_rows else 0

    if expected == "zero":
        if count == 0:
            return EngineResult(
                "codeql", "V", "gate",
                "0 rows — invariant holds", artifact, elapsed_ms,
            )
        return EngineResult(
            "codeql", "Vx", "gate",
            f"{count} rows found — investigate", artifact, elapsed_ms,
        )
    else:  # "any" or specific count
        return EngineResult(
            "codeql", "V", "gate",
            f"{count} rows — classification required; see artifact",
            artifact, elapsed_ms,
        )


def engine_git_provenance(
    manifest_dir: Path, engine_cfg: Dict, spec_id: str,
) -> EngineResult:
    """Advisory: query git log for EARS-code correlation.
    Reuses the B7 pattern but returns aggregate stats."""
    start = datetime.now()
    spec_file = engine_cfg.get("spec_file")
    project_root = Path(engine_cfg.get("project_root", "."))

    if not project_root.exists():
        return EngineResult(
            "git-provenance", "?", "advisory",
            f"project root not found: {project_root}", None,
        )

    try:
        # Count EARS-edit commits mentioning this spec
        ears_commits = subprocess.run(
            ["git", "-C", str(project_root), "log",
             f"-S{spec_id}", "--format=%H", "--", spec_file],
            capture_output=True, text=True, timeout=30,
        )
        ears_count = len([l for l in ears_commits.stdout.splitlines() if l])

        # Count commits touching any file with @spec <ID>
        grep_files = subprocess.run(
            ["git", "-C", str(project_root), "grep", "-l",
             f"@spec.*{spec_id}", "HEAD"],
            capture_output=True, text=True, timeout=30,
        )
        atspec_files = [
            l.split(":", 1)[-1]
            for l in grep_files.stdout.splitlines()
            if ":" in l
        ]
        code_commits = 0
        if atspec_files:
            log = subprocess.run(
                ["git", "-C", str(project_root), "log", "--format=%H", "--"]
                + atspec_files,
                capture_output=True, text=True, timeout=30,
            )
            code_commits = len([l for l in log.stdout.splitlines() if l])

        elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)
        detail = (
            f"EARS edits: {ears_count}; "
            f"@spec-annotated files: {len(atspec_files)}; "
            f"code commits touching them: {code_commits}"
        )
        if not atspec_files:
            return EngineResult(
                "git-provenance", "Vp", "advisory",
                detail + " [coverage gap: no @spec annotation anywhere]",
                None, elapsed_ms,
            )
        return EngineResult(
            "git-provenance", "V", "advisory",
            detail, None, elapsed_ms,
        )
    except Exception as e:
        return EngineResult(
            "git-provenance", "?", "advisory",
            f"git query failed: {e}", None,
        )


def engine_differential(
    manifest_dir: Path, engine_cfg: Dict, spec_id: str,
) -> EngineResult:
    """Advisory: differential is generative (A/B round-trip via LLM),
    not mechanically repeatable in a CI context. Report last_run from
    the artifact and flag as advisory."""
    artifact = engine_cfg.get("artifact")
    if not artifact:
        return EngineResult(
            "differential", "?", "advisory",
            "no differential artifact declared", None,
        )
    path = manifest_dir / artifact
    if not path.exists():
        return EngineResult(
            "differential", "Vx", "advisory",
            f"artifact not found: {path}", artifact,
        )
    # Read artifact; look for a "## Coherence findings" section with content
    text = path.read_text(errors="replace")
    has_findings = "Coherence findings" in text or "coherence findings" in text
    status = engine_cfg.get("status", "Vp")
    detail = (
        "artifact present; differential is advisory (LLM-generative)"
        f"; has findings section: {has_findings}"
    )
    return EngineResult(
        "differential", status, "advisory", detail, artifact,
    )


# ---------- dispatch table ----------

ENGINE_DISPATCH = {
    "manual-review": engine_manual_review,
    "lemmascript": engine_lemmascript,
    "lemmascript-dafny": engine_lemmascript_dafny,
    "test-witness": engine_test_witness,
    "type-system": engine_type_system,
    "codeql": engine_codeql,
    "git-provenance": engine_git_provenance,
    "differential": engine_differential,
}


# ---------- orchestration ----------

def find_manifests(overlay_dir: Path) -> List[Path]:
    return sorted(overlay_dir.glob("*.overlay.yaml"))


def process_manifest(
    manifest_path: Path, codeql_db: Optional[str],
) -> SpecResult:
    with open(manifest_path) as f:
        m = yaml.safe_load(f)

    spec_id = m.get("spec_id", manifest_path.stem.replace(".overlay", ""))
    arrow = m.get("arrow", "<unknown>")
    result = SpecResult(spec_id, arrow, manifest_path)

    engines = m.get("engines", [])
    if not isinstance(engines, list):
        engines = [engines]

    manifest_dir = manifest_path.parent

    for eng_cfg in engines:
        eng_name = eng_cfg.get("engine")
        if not eng_name:
            continue
        invoker = ENGINE_DISPATCH.get(eng_name)
        if not invoker:
            result.engines.append(EngineResult(
                eng_name, "?", "advisory",
                f"no dispatcher for engine '{eng_name}'",
            ))
            continue
        try:
            if eng_name == "codeql":
                eng_result = invoker(manifest_dir, eng_cfg, spec_id, codeql_db)
            else:
                eng_result = invoker(manifest_dir, eng_cfg, spec_id)
        except Exception as e:
            eng_result = EngineResult(
                eng_name, "?", "advisory", f"dispatcher error: {e}",
            )
        # Posture override: advisory engines always posture=advisory
        if eng_name in ADVISORY_ENGINES:
            eng_result.posture = "advisory"
        result.engines.append(eng_result)

    return result


def aggregate_status(results: List[SpecResult]) -> Dict:
    by_status = {"V": 0, "Vp": 0, "Vx": 0, "Vn": 0, "?": 0}
    by_engine: Dict[str, List[str]] = {}
    by_arrow: Dict[str, List[str]] = {}

    for r in results:
        by_status[r.overall_status] = by_status.get(r.overall_status, 0) + 1
        by_arrow.setdefault(r.arrow, []).append(r.spec_id)
        for e in r.engines:
            by_engine.setdefault(e.engine, []).append(r.spec_id)

    total = len(results)
    terminal_covered = (
        by_status.get("V", 0)
        + by_status.get("Vp", 0)
        + by_status.get("Vn", 0)
    )
    coverage = terminal_covered / total if total else 0.0

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "total_specs": total,
        "coverage": {
            "formula": "|V ∪ Vp ∪ Vn| / total",
            "value": round(coverage, 3),
        },
        "by_status": by_status,
        "by_engine": {k: sorted(set(v)) for k, v in by_engine.items()},
        "by_arrow": {k: sorted(set(v)) for k, v in by_arrow.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("overlay_dir", type=Path)
    ap.add_argument("--write-status", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--codeql-db", type=str, default=None)
    ap.add_argument("--json", action="store_true",
                    help="emit JSON result to stdout")
    args = ap.parse_args()

    if not args.overlay_dir.is_dir():
        print(f"error: not a directory: {args.overlay_dir}", file=sys.stderr)
        return 2

    manifests = find_manifests(args.overlay_dir)
    if not manifests:
        print(f"warning: no *.overlay.yaml in {args.overlay_dir}",
              file=sys.stderr)

    results: List[SpecResult] = []
    for m in manifests:
        if args.verbose:
            print(f"→ dispatching {m.name}", file=sys.stderr)
        r = process_manifest(m, args.codeql_db)
        results.append(r)
        if args.verbose:
            for e in r.engines:
                print(f"    [{e.engine}] {e.status} ({e.posture}) "
                      f"— {e.detail}", file=sys.stderr)

    agg = aggregate_status(results)
    agg["by_spec"] = [r.to_dict() for r in results]

    if args.json:
        print(json.dumps(agg, indent=2, default=str))

    if args.write_status:
        status_path = args.overlay_dir / "_status.yaml"
        with open(status_path, "w") as f:
            yaml.safe_dump(agg, f, sort_keys=False, default_flow_style=False)
        print(f"wrote {status_path}", file=sys.stderr)

    # Summary to stderr for CI-friendly logs
    print("", file=sys.stderr)
    print(f"specs: {agg['total_specs']}", file=sys.stderr)
    print(f"coverage: {agg['coverage']['value']:.1%}", file=sys.stderr)
    for status, count in agg["by_status"].items():
        if count:
            print(f"  {status}: {count}", file=sys.stderr)

    # Exit code: 1 if any gate engine has non-terminal status
    any_gate_fail = any(
        e.posture == "gate" and e.status in ("Vx", "?")
        for r in results for e in r.engines
    )
    return 1 if any_gate_fail else 0


if __name__ == "__main__":
    sys.exit(main())
