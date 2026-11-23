// Checks the tree counter. Run from the repository root:
//   node --test site/tests/intent-tree.test.js
import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { after, describe, it } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { measureTree, treeToYaml } from "../scripts/intent-tree.js";

const script = join(dirname(fileURLToPath(import.meta.url)), "..", "scripts", "intent-tree.js");
const roots = [];
after(() => roots.forEach((r) => rmSync(r, { recursive: true, force: true })));

// Builds a directory tree from { "path/file.md": "content" }.
function fixture(files) {
  const root = mkdtempSync(join(tmpdir(), "intent-tree-"));
  roots.push(root);
  for (const [path, content] of Object.entries(files)) {
    mkdirSync(dirname(join(root, path)), { recursive: true });
    writeFileSync(join(root, path), content);
  }
  return root;
}
const specs = (...markers) => markers.map((m, i) => `- \`[${m}]\` **AREA-${String(i + 1).padStart(3, "0")}**: The system SHALL do thing ${i}.`).join("\n") + "\n";

describe("the tree counter", () => {
  // @spec ONB-SHOWCASE-073, ONB-SHOWCASE-077, ONB-SHOWCASE-083
  it("reads a node-as-folder tree, with sub-HLDs and leaves in alphabetical order", () => {
    const root = fixture({
      "zeta/zeta-design.md": "# Zeta",
      "zeta/zeta-specs.md": specs("x", " "),
      "alpha/alpha-design.md": "# Alpha sub-HLD",
      "alpha/two/two-specs.md": specs("x"),
      "alpha/one/one-specs.md": specs("x", "x", "x"),
    });
    assert.deepEqual(measureTree(root), {
      children: [
        { name: "alpha", children: [{ name: "one", specs: 3, built: 3 }, { name: "two", specs: 1, built: 1 }] },
        { name: "zeta", specs: 2, built: 1 },
      ],
    });
  });

  // @spec ONB-SHOWCASE-074
  it("makes one leaf per spec file in a flat layout", () => {
    const root = fixture({ "specs/api-specs.md": specs("x", "x"), "specs/storage-specs.md": specs(" ") });
    assert.deepEqual(measureTree(root).children, [{ name: "specs", children: [{ name: "api", specs: 2, built: 2 }, { name: "storage", specs: 1, built: 0 }] }]);
  });

  // @spec ONB-SHOWCASE-075
  it("adds a directory's own spec file as a leaf beneath it when it also has children", () => {
    const root = fixture({ "core/core-specs.md": specs("x"), "core/inner/inner-specs.md": specs("x", "x") });
    assert.deepEqual(measureTree(root).children, [{ name: "core", children: [{ name: "core", specs: 1, built: 1 }, { name: "inner", specs: 2, built: 2 }] }]);
  });

  // @spec ONB-SHOWCASE-093
  it("makes a spec file directly in the design directory a leaf beneath the HLD", () => {
    const root = fixture({ "top-specs.md": specs("x"), "area/area-specs.md": specs(" ") });
    assert.deepEqual(measureTree(root).children, [{ name: "area", specs: 1, built: 0 }, { name: "top", specs: 1, built: 1 }]);
  });

  // @spec ONB-SHOWCASE-072, ONB-SHOWCASE-076
  it("counts only -specs.md files and skips hidden, decisions, symlinked, and empty directories", () => {
    const root = fixture({
      "area/area-specs.md": specs("x"),
      "area/notes.md": specs("x", "x", "x"),
      ".hidden/hidden-specs.md": specs("x"),
      "decisions/decisions-specs.md": specs("x"),
      "empty/empty-design.md": "# nothing to count",
    });
    symlinkSync(join(root, "area"), join(root, "linked"));
    assert.deepEqual(measureTree(root).children, [{ name: "area", specs: 1, built: 1 }]);
  });

  // @spec ONB-SHOWCASE-078, ONB-SHOWCASE-079, ONB-SHOWCASE-080, ONB-SHOWCASE-081, ONB-SHOWCASE-082
  it("counts list items with status markers and bold IDs, built when [x], never [D], never in code fences, duplicates included", () => {
    const text = [
      "- `[x]` **A-001**: built, backticked",
      "* [X] **A-002**: built, capital, bare",
      "  + `[ ]` **A-003**: open, nested",
      "- `[D]` **A-004**: deferred",
      "- `[x]` **A-001**: repeats an ID",
      "[x] **A-005**: not a list item",
      "- `[x]` A-006: no bold ID",
      "- `[x]` **a-007**: lower-case ID",
      "```",
      "- `[x]` **A-008**: inside a fence",
      "```",
    ].join("\n");
    const root = fixture({ "area/area-specs.md": text });
    assert.deepEqual(measureTree(root).children, [{ name: "area", specs: 4, built: 3 }]);
  });

  // @spec ONB-SHOWCASE-083
  it("writes no names when asked", () => {
    const root = fixture({ "area/area-specs.md": specs("x"), "group/inner/inner-specs.md": specs(" ") });
    assert.deepEqual(measureTree(root, { names: false }), { children: [{ specs: 1, built: 1 }, { children: [{ specs: 1, built: 0 }] }] });
  });

  // @spec ONB-SHOWCASE-070, ONB-SHOWCASE-084
  it("runs from the command line with no dependencies and writes only names, structure, and counts", () => {
    const root = fixture({ "secret-area/secret-area-specs.md": "- `[x]` **SECRET-001**: The system SHALL keep the launch code hidden.\n" });
    const out = execFileSync("node", [script, root], { encoding: "utf8" });
    assert.equal(out, "children:\n  - name: secret-area\n    specs: 1\n    built: 1\n");
    assert.doesNotMatch(out, /SECRET-001|launch code|\//);
    const anon = execFileSync("node", [script, root, "--no-names"], { encoding: "utf8" });
    assert.equal(anon, "children:\n  - specs: 1\n    built: 1\n");
  });

  // @spec ONB-SHOWCASE-070
  it("writes nested trees as YAML", () => {
    assert.equal(
      treeToYaml({ children: [{ name: "a", children: [{ name: "b", specs: 2, built: 1 }, { specs: 3, built: 3 }] }, { name: "c" }] }),
      "children:\n  - name: a\n    children:\n      - name: b\n        specs: 2\n        built: 1\n      - specs: 3\n        built: 3\n  - name: c\n",
    );
  });

  // @spec ONB-SHOWCASE-085
  it("fails with a message on a missing or empty design directory", () => {
    for (const dir of [join(tmpdir(), "no-such-design-dir-xyz"), fixture({ "readme.md": "# nothing" })]) {
      const run = spawnSync("node", [script, dir], { encoding: "utf8" });
      assert.notEqual(run.status, 0);
      assert.match(run.stderr, /\S/);
      assert.equal(run.stdout, "");
    }
  });
});
