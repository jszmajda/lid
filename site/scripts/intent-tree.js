#!/usr/bin/env node
// Measures a LID design tree and writes its tree file: node names, structure, and spec counts,
// with nothing of the docs' text. Plain Node, no dependencies.
//
//   node site/scripts/intent-tree.js <design-dir> [--no-names] > tree.yaml
//
// The site's build imports measureTree() to draw the repository's own reference trees.
// @spec ONB-SHOWCASE-070, ONB-SHOWCASE-071, ONB-SHOWCASE-084
import { existsSync, lstatSync, readdirSync, readFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SPEC_FILE = /-specs\.md$/; // @spec ONB-SHOWCASE-072
// A list item at any indentation whose text starts with a status marker and a bold ID.
// @spec ONB-SHOWCASE-078
const SPEC_LINE = /^\s*[-*+]\s+`?\[([xX ]|D)\]`?\s+\*\*[A-Z][A-Z0-9-]*-\d+\*\*/;

// Counts the specs in one spec file. @spec ONB-SHOWCASE-079, ONB-SHOWCASE-080, ONB-SHOWCASE-081, ONB-SHOWCASE-082
export function countSpecs(text) {
  let specs = 0;
  let built = 0;
  let fenced = false;
  for (const line of text.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) {
      fenced = !fenced;
      continue;
    }
    if (fenced) continue;
    const m = line.match(SPEC_LINE);
    if (!m || m[1] === "D") continue;
    specs += 1;
    if (m[1] === "x" || m[1] === "X") built += 1;
  }
  return { specs, built };
}

const stem = (file) => file.replace(SPEC_FILE, "");
const byName = (a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0);

// Returns the nodes a directory contributes, or [] when it holds no spec file at any depth.
// @spec ONB-SHOWCASE-073, ONB-SHOWCASE-074, ONB-SHOWCASE-075, ONB-SHOWCASE-076, ONB-SHOWCASE-077
function readDir(dir) {
  const entries = readdirSync(dir).sort();
  const specFiles = [];
  const children = [];
  for (const name of entries) {
    const path = join(dir, name);
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) continue;
    if (stat.isDirectory()) {
      if (name.startsWith(".") || name === "decisions") continue;
      const node = nodeFor(path);
      if (node) children.push(node);
    } else if (stat.isFile() && SPEC_FILE.test(name)) {
      specFiles.push(name);
    }
  }
  return { specFiles, children };
}

const leaf = (dir, file, name) => ({ name, ...countSpecs(readFileSync(join(dir, file), "utf8")) });

function nodeFor(dir) {
  const { specFiles, children } = readDir(dir);
  const name = basename(dir);
  if (!children.length) {
    if (!specFiles.length) return null;
    if (specFiles.length === 1) return leaf(dir, specFiles[0], name);
    return { name, children: specFiles.map((f) => leaf(dir, f, stem(f))).sort(byName) };
  }
  const own = specFiles.map((f) => leaf(dir, f, specFiles.length === 1 ? name : stem(f)));
  return { name, children: [...own, ...children].sort(byName) };
}

const stripNames = (node) => {
  const { name, children, ...rest } = node;
  return children ? { ...rest, children: children.map(stripNames) } : rest;
};

// Measures the design tree under `designDir`. Throws when there is nothing to measure.
// @spec ONB-SHOWCASE-085, ONB-SHOWCASE-093
export function measureTree(designDir, { names = true } = {}) {
  const dir = resolve(designDir);
  if (!existsSync(dir) || !lstatSync(dir).isDirectory()) throw new Error(`no design directory at ${designDir}`);
  const { specFiles, children } = readDir(dir);
  const top = [...specFiles.map((f) => leaf(dir, f, stem(f))), ...children].sort(byName);
  if (!top.length) throw new Error(`no spec files (*-specs.md) under ${designDir}`);
  const tree = { children: top };
  return names ? tree : { children: top.map(stripNames) };
}

// Writes a tree as the tree file's YAML.
export function treeToYaml(tree) {
  const lines = ["children:"];
  const write = (node, indent) => {
    const pad = " ".repeat(indent);
    const fields = [];
    if (node.name !== undefined) fields.push(`name: ${node.name}`);
    if (node.children) {
      fields.push("children:");
    } else if (node.specs !== undefined) {
      fields.push(`specs: ${node.specs}`, `built: ${node.built}`);
    }
    if (!fields.length) fields.push("{}");
    lines.push(`${pad}- ${fields[0]}`);
    for (const f of fields.slice(1)) lines.push(`${pad}  ${f}`);
    if (node.children) for (const c of node.children) write(c, indent + 4);
  };
  for (const c of tree.children) write(c, 2);
  return lines.join("\n") + "\n";
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const dir = args.find((a) => !a.startsWith("--"));
  if (!dir) {
    process.stderr.write("usage: node site/scripts/intent-tree.js <design-dir> [--no-names]\n");
    process.exit(2);
  }
  try {
    process.stdout.write(treeToYaml(measureTree(dir, { names: !args.includes("--no-names") })));
  } catch (e) {
    process.stderr.write(`intent-tree: ${e.message}\n`);
    process.exit(1);
  }
}
