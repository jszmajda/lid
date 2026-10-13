#!/usr/bin/env bash
# B10 harness: build a code-only audit tree for B-direction auditors.
#
#   prep_audit_tree.sh <clone-dir> <out-dir>
#
# Produces:
#   <out-dir>/            crates/ + Cargo.toml only — no docs/, no README/TODO/CLAUDE.md,
#                         no .git — with every @spec annotation stripped from .rs files.
#   <out-dir>.citations   the pre-strip @spec citation map (spec-id -> file:line), kept
#                         OUTSIDE the audit tree; the orchestrator uses it to compute
#                         per-spec file slices. Never give this file to an auditor.
set -euo pipefail

CLONE="$1"
OUT="$2"

[ -d "$CLONE/crates" ] || { echo "not a portfolio-tracker clone: $CLONE" >&2; exit 1; }
rm -rf "$OUT"
mkdir -p "$OUT"

# Citation map BEFORE stripping (slice computation + traceability): any spec-ID
# mention — @spec annotations AND doc-comment references like "(SHEET-MAP-001)".
grep -rnE '[A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]{3}' "$CLONE/crates" --include='*.rs' > "$OUT.citations" || true

cp -Rc "$CLONE/crates" "$OUT/crates"
cp "$CLONE/Cargo.toml" "$OUT/Cargo.toml"
[ -f "$CLONE/Cargo.lock" ] && cp "$CLONE/Cargo.lock" "$OUT/Cargo.lock"
rm -rf "$OUT"/crates/*/target 2>/dev/null || true

# Strip spec references: remove the comment portion of any line carrying an
# @spec annotation OR a spec-ID mention (doc comments sometimes paraphrase the
# spec — leaving them would hand B-direction auditors the answer), then squeeze
# runs of blank lines.
find "$OUT/crates" -name '*.rs' -print0 | xargs -0 perl -i -pe 's{//.*\@spec.*$}{}; s{//.*\b[A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]{3}\b.*$}{};'
find "$OUT/crates" -name '*.rs' -print0 | xargs -0 perl -i -ne 'print unless /^\s*$/ && $prev_blank++; $prev_blank = 0 unless /^\s*$/;'

# Verify nothing leaked (annotations or comment-borne spec IDs).
if grep -rq '@spec' "$OUT/crates" || grep -rqE '//.*\b[A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]{3}\b' "$OUT/crates"; then
  echo "FATAL: spec reference survived stripping in $OUT" >&2
  exit 1
fi
echo "audit tree ready: $OUT ($(find "$OUT/crates" -name '*.rs' | wc -l | tr -d ' ') .rs files); citations: $OUT.citations"
