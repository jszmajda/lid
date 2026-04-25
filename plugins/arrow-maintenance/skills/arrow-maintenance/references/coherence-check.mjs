#!/usr/bin/env node

/**
 * LID Coherence Check — optional reference implementation.
 *
 * This script is one way to perform the deterministic checks the arrow-maintenance
 * skill specifies. It is language-neutral in concept: equivalent implementations
 * in Python, bash, Ruby, Go, or any other language are fully acceptable. The
 * arrow-maintenance skill invokes whatever `bin/coherence-check.*` is present and
 * treats its output as authoritative; if nothing is present, the skill performs
 * the checks in-prompt (slower, more expensive).
 *
 * Install: copy this file to your project as `bin/coherence-check.mjs`, mark it
 * executable, and run `./bin/coherence-check.mjs` (or `node bin/coherence-check.mjs`).
 * Adjust the file globs and spec-ID regex to match your project's conventions.
 *
 * Checks performed (aligned with audit-checklist.md):
 *   1. @spec annotation integrity (orphaned refs, reverse orphans)
 *   2. Arrow reference integrity (broken file references in arrow detail docs)
 *   3. Arrow staleness (audited >30 days ago; UNMAPPED/MAPPED status)
 *   4. Coverage summary (per-arrow and repo-wide)
 *
 * Not a blocker. Not a CI gate. Just a fast report. Exit code is always 0.
 */

import { readFileSync, readdirSync, existsSync } from 'fs';
import { join, resolve } from 'path';
import { execSync } from 'child_process';

const ROOT = resolve(process.cwd());
const SPECS_DIR = join(ROOT, 'docs', 'specs');
const ARROWS_DIR = join(ROOT, 'docs', 'arrows');
const ARROWS_INDEX = join(ARROWS_DIR, 'index.yaml');

// ───────── Helpers ─────────

function fileExists(relPath) {
  return existsSync(join(ROOT, relPath));
}

function readFile(absPath) {
  try {
    return readFileSync(absPath, 'utf-8');
  } catch {
    return null;
  }
}

function daysSince(dateStr) {
  if (!dateStr) return Infinity;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return Infinity;
  return Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
}

// ───────── 1. @spec annotation integrity ─────────

function collectSpecIdsFromCode() {
  let output;
  try {
    output = execSync(
      `grep -rn "@spec" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" --include="*.go" --include="*.rs" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=build --exclude-dir=target --exclude-dir=cdk.out --exclude-dir=coverage --exclude-dir=.next --exclude-dir=__pycache__ .`,
      { cwd: ROOT, encoding: 'utf-8', maxBuffer: 50 * 1024 * 1024 }
    );
  } catch (e) {
    output = e.stdout || '';
  }

  const codeRefs = new Map(); // specId -> [{file, line}]
  // Negative lookahead (?![a-z]) prevents mid-CamelCase matches like "GSI-B" from "GSI-ByReminderDue"
  // Post-filter (below): require at least one digit — excludes "A-Z" and "YYYYMMDD-HHMM" false positives
  const idPattern = /[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?![a-z])/g;

  for (const line of output.split('\n').filter(Boolean)) {
    const match = line.match(/^\.\/(.+?):(\d+):(.*)/);
    if (!match) continue;
    const [, file, lineNum, rest] = match;

    if (!/\bspec\b/i.test(rest)) continue; // filter to @spec context

    let m;
    while ((m = idPattern.exec(rest)) !== null) {
      const id = m[0];
      if (!/\d/.test(id)) continue; // skip ID-shaped tokens with no digits
      if (!codeRefs.has(id)) codeRefs.set(id, []);
      codeRefs.get(id).push({ file, line: parseInt(lineNum) });
    }
  }

  return codeRefs;
}

function collectSpecIdsFromSpecs() {
  const specDefs = new Map();

  if (!existsSync(SPECS_DIR)) return specDefs;

  const files = readdirSync(SPECS_DIR).filter(f => f.endsWith('.md'));

  for (const file of files) {
    const content = readFile(join(SPECS_DIR, file));
    if (!content) continue;

    for (const line of content.split('\n')) {
      // Checklist style: - [x] **SPEC-ID**: description
      const checklist = line.match(/^-\s+\[([ xD])\]\s+\*\*([A-Z][\w-]+)\*\*/);
      if (checklist) {
        const [, marker, id] = checklist;
        const status = marker === 'x' ? 'implemented' : marker === 'D' ? 'deferred' : 'gap';
        specDefs.set(id, { file, status });
        continue;
      }
      // Heading style: ### SPEC-ID
      const heading = line.match(/^###\s+([A-Z][\w-]+)\b/);
      if (heading) {
        specDefs.set(heading[1], { file, status: 'defined' });
        continue;
      }
      // Bold style: **SPEC-ID**: description, with optional leading "- " dash-bullet (no checkbox)
      const bold = line.match(/^(?:-\s+)?\*\*([A-Z][\w-]+)\*\*:/);
      if (bold) {
        specDefs.set(bold[1], { file, status: 'defined' });
        continue;
      }
      // Table-cell style: | **SPEC-ID** | description | ... | (markdown table row)
      const tableCell = line.match(/^\|\s*\*\*([A-Z][\w-]+)\*\*\s*\|/);
      if (tableCell) {
        specDefs.set(tableCell[1], { file, status: 'defined' });
      }
    }
  }

  return specDefs;
}

function checkSpecIntegrity() {
  const codeRefs = collectSpecIdsFromCode();
  const specDefs = collectSpecIdsFromSpecs();

  const reverseOrphans = [];
  const uncovered = [];

  for (const [id, locations] of codeRefs) {
    if (!specDefs.has(id)) reverseOrphans.push({ id, locations });
  }

  for (const [id, info] of specDefs) {
    if (info.status === 'gap' && !codeRefs.has(id)) {
      uncovered.push({ id, file: info.file });
    }
  }

  return { codeRefs, specDefs, reverseOrphans, uncovered };
}

// ───────── 2. Arrow reference integrity ─────────

function parseArrowsIndex() {
  const content = readFile(ARROWS_INDEX);
  if (!content) return { arrows: {} };

  const arrows = {};
  let currentArrow = null;
  let inArrowsSection = false;

  for (const line of content.split('\n')) {
    if (/^arrows:\s*$/.test(line)) { inArrowsSection = true; continue; }
    if (/^[a-z][\w-]*:/.test(line) && !line.startsWith('  ')) {
      inArrowsSection = false;
      currentArrow = null;
      continue;
    }
    if (/^#/.test(line)) continue;
    if (!inArrowsSection) continue;

    const arrowMatch = line.match(/^  ([a-z][\w-]+):\s*$/);
    if (arrowMatch) {
      currentArrow = arrowMatch[1];
      arrows[currentArrow] = {};
      continue;
    }
    if (!currentArrow) continue;

    const kv = line.match(/^\s{4}(\w+):\s*(.+)/);
    if (kv) {
      let [, key, value] = kv;
      value = value.replace(/^["']|["']$/g, '').trim();
      if (value === 'null') value = null;
      if (value === '[]') value = [];
      arrows[currentArrow][key] = value;
    }
  }

  return { arrows };
}

function checkArrowReferences() {
  const { arrows } = parseArrowsIndex();
  const issues = [];

  for (const [name, meta] of Object.entries(arrows)) {
    if (!meta.detail) continue;
    const detailPath = join(ARROWS_DIR, meta.detail);
    if (!existsSync(detailPath)) {
      issues.push({ arrow: name, type: 'missing_detail', path: meta.detail });
      continue;
    }

    const content = readFile(detailPath);
    if (!content) continue;

    const refPattern = /(?:^[-*]\s+|→\s+|:\s+)`?([a-zA-Z][\w./~-]+\.[a-zA-Z]+)`?/gm;
    let m;
    while ((m = refPattern.exec(content)) !== null) {
      const ref = m[1];
      if (ref.includes('://') || ref.includes('*') || ref.includes('...')) continue;
      if (ref.match(/^\d+\.\d+/) || ref.match(/^[a-z]+\.[a-z]+$/)) continue;
      if (ref.includes('/') && !fileExists(ref)) {
        issues.push({ arrow: name, type: 'broken_ref', path: ref, detail: meta.detail });
      }
    }
  }

  return { arrows, issues };
}

// ───────── 3. Staleness ─────────

function checkStaleness() {
  const { arrows } = parseArrowsIndex();
  const stale = [];
  const needsWork = [];

  for (const [name, meta] of Object.entries(arrows)) {
    const status = meta.status;
    if (status === 'UNMAPPED' || status === 'MAPPED') {
      needsWork.push({ arrow: name, status, reason: `status is ${status}` });
      continue;
    }
    if (status === 'OBSOLETE' || status === 'OK') continue;

    const last = meta.audited || meta.sampled;
    const days = daysSince(last);
    if (days > 30) {
      stale.push({ arrow: name, status, lastAudited: last || 'never', daysSince: days === Infinity ? 'never' : days });
    }
  }

  return { stale, needsWork };
}

// ───────── 4. Coverage summary ─────────

function coverageSummary(specDefs, codeRefs) {
  let total = 0, implemented = 0, deferred = 0, gaps = 0;
  for (const [, info] of specDefs) {
    total++;
    if (info.status === 'implemented') implemented++;
    else if (info.status === 'deferred') deferred++;
    else if (info.status === 'gap') gaps++;
  }
  const defined = [...specDefs.values()].filter(v => v.status === 'defined').length;
  return { total, implemented, deferred, gaps, defined, codeRefsTotal: codeRefs.size };
}

// ───────── Report ─────────

function section(title) {
  console.log('');
  console.log('═'.repeat(60));
  console.log(`  ${title}`);
  console.log('═'.repeat(60));
}

function run() {
  console.log('LID Coherence Report');
  console.log(`Generated: ${new Date().toISOString().slice(0, 10)}`);
  console.log(`Root: ${ROOT}`);

  section('@spec Integrity');
  const { codeRefs, specDefs, reverseOrphans, uncovered } = checkSpecIntegrity();
  console.log(`  @spec annotations in code: ${codeRefs.size} unique IDs`);
  console.log(`  Spec definitions: ${specDefs.size} across docs/specs/`);

  if (reverseOrphans.length) {
    console.log(`\n  Reverse orphans (${reverseOrphans.length}) — @spec cites a spec that doesn't exist:`);
    for (const { id, locations } of reverseOrphans.slice(0, 25)) {
      const loc = locations[0];
      console.log(`    ${id}  (${loc.file}:${loc.line}${locations.length > 1 ? ` +${locations.length - 1}` : ''})`);
    }
    if (reverseOrphans.length > 25) console.log(`    ... and ${reverseOrphans.length - 25} more`);
  } else {
    console.log('  No reverse orphans.');
  }

  if (uncovered.length) {
    console.log(`\n  Uncovered [ ] specs (${uncovered.length}) — gap markers with no @spec ref:`);
    for (const { id, file } of uncovered.slice(0, 25)) console.log(`    ${id}  (${file})`);
    if (uncovered.length > 25) console.log(`    ... and ${uncovered.length - 25} more`);
  }

  section('Arrow Reference Integrity');
  const { arrows, issues } = checkArrowReferences();
  console.log(`  Arrows in index: ${Object.keys(arrows).length}`);
  if (issues.length) {
    for (const issue of issues) {
      if (issue.type === 'missing_detail') console.log(`    [MISSING] ${issue.arrow}: ${issue.path}`);
      else console.log(`    [BROKEN]  ${issue.arrow}: ${issue.path} (in ${issue.detail})`);
    }
  } else {
    console.log('  All arrow references valid.');
  }

  section('Staleness');
  const { stale, needsWork } = checkStaleness();
  if (needsWork.length) {
    console.log('  Needs work:');
    for (const w of needsWork) console.log(`    ${w.arrow}: ${w.reason}`);
  }
  if (stale.length) {
    console.log('  Stale (>30 days since audit):');
    for (const s of stale) console.log(`    ${s.arrow}: ${s.status}, ${s.lastAudited} (${s.daysSince} days)`);
  }
  if (!needsWork.length && !stale.length) console.log('  All arrows current.');

  const statusCounts = {};
  for (const [, meta] of Object.entries(arrows)) {
    const s = meta.status || 'UNKNOWN';
    statusCounts[s] = (statusCounts[s] || 0) + 1;
  }
  if (Object.keys(statusCounts).length) {
    console.log('\n  Status summary:');
    for (const [s, c] of Object.entries(statusCounts).sort()) console.log(`    ${s}: ${c}`);
  }

  section('Coverage');
  const cov = coverageSummary(specDefs, codeRefs);
  console.log(`  Total specs: ${cov.total + cov.defined}`);
  console.log(`    [x] implemented: ${cov.implemented}`);
  console.log(`    [ ] active gap:  ${cov.gaps}`);
  console.log(`    [D] deferred:    ${cov.deferred}`);
  console.log(`    (defined, no marker): ${cov.defined}`);
  console.log(`  Unique @spec IDs in code: ${cov.codeRefsTotal}`);
  console.log('');
}

run();
