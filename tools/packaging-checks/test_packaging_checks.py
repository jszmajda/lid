#!/usr/bin/env python3
"""Tests for packaging_checks.py. Run from the repository root:

    python3 tools/packaging-checks/test_packaging_checks.py

Static checks run against fixture trees built in temporary directories. The
end-to-end tests build a local git repository and a bare one standing in for
the GitHub remote. The host parts run against stub hosts, so no model, key,
container runtime, or network is needed.
"""

# @spec PKG-CHECK-037
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import packaging_checks as pc  # noqa: E402

CORE_BODY = """# Linked-Intent Development

Body of the workflow.

## LID-on-LID exception

Applies only in the LID repository.

## Reference files

- `references/ears-syntax.md` — EARS syntax.
- `references/lld-templates.md` — LLD template.
"""


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)


def skill_md(name, description, body="Body.\n", extra=""):
    return '---\nname: %s\ndescription: "%s"\n%s---\n\n%s' % (name, description, extra, body)


def changelog(version, earlier=("1.4.0",), top_extra=""):
    entries = ["## [%s] — 2026-10-24\n\n### Fixed\n- A fix.\n%s" % (version, top_extra)]
    for v in earlier:
        if v != version:
            entries.append("## [%s] — 2026-10-10\n\n### Added\n- A thing.\n" % v)
    return "# Changelog\n\nIntro.\n\n" + "\n".join(entries)


def build_tree(root, version="1.4.0", earlier=("1.4.0",), stamp=None, top_extra=""):
    """A minimal well-formed repository tree at `version`."""
    root = Path(root)
    for plugin in ("linked-intent-dev", "arrow-maintenance", "lid-experimental"):
        write(root / "plugins" / plugin / ".claude-plugin" / "plugin.json",
              json.dumps({"name": plugin, "description": "x", "version": version}))
        write(root / "plugins" / plugin / ".cursor-plugin" / "plugin.json",
              json.dumps({"name": plugin, "description": "x"}))
    core = root / "plugins" / "linked-intent-dev"
    write(core / "CHANGELOG.md", changelog(version, earlier, top_extra))
    write(core / "skills" / "linked-intent-dev" / "SKILL.md",
          skill_md("linked-intent-dev", "Core workflow.", CORE_BODY))
    write(core / "skills" / "linked-intent-dev" / "references" / "ears-syntax.md",
          "# EARS Syntax Reference\n\nNo trailing newline.")
    write(core / "skills" / "linked-intent-dev" / "references" / "lld-templates.md",
          "# LLD Templates Reference\n\nText.\n")
    write(core / "skills" / "update-lid" / "SKILL.md",
          skill_md("update-lid", "Configure LID.", extra="disable-model-invocation: true\n"))
    write(core / "skills" / "update-lid" / "evals" / "evals.json", "{}\n")
    write(core / "skills" / "update-lid" / "references" / "workflow-doc.md",
          pc.assemble_workflow_doc(core / "skills" / "linked-intent-dev", stamp or version))
    write(root / "plugins" / "arrow-maintenance" / "skills" / "arrow-maintenance" / "SKILL.md",
          skill_md("arrow-maintenance", "Audit the overlay."))
    exp = root / "plugins" / "lid-experimental"
    write(exp / "skills" / "bidirectional-differential" / "SKILL.md",
          skill_md("bidirectional-differential", "Audit coherence."))
    write(exp / "commands" / "differential-audit.md",
          '---\ndescription: "Run the differential audit."\n---\n\nInvoke the skill.\n')
    for manifest, prefix in ((".claude-plugin", "./"), (".cursor-plugin", "./")):
        write(root / manifest / "marketplace.json", json.dumps({
            "name": "jszmajda-lid", "owner": {"name": "x"},
            "plugins": [{"name": p, "source": prefix + "plugins/" + p, "description": "x"}
                        for p in ("linked-intent-dev", "arrow-maintenance", "lid-experimental")]}))
    write(root / "AGENTS.md", "# Agents\n")
    if not (root / "CLAUDE.md").is_symlink():
        os.symlink("AGENTS.md", root / "CLAUDE.md")
    write(root / "CONTRIBUTING.md",
          "# Contributing\n\nSee [setup](docs/setup.md#claude-code) and [the bar](#the-bar).\n"
          "External [link](https://example.com/x).\n\n## The bar\n\nText.\n")
    write(root / "docs" / "setup.md",
          "# Setup\n\n## Claude Code\n\nBack to [contributing](../CONTRIBUTING.md).\n")
    return root


class TreeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tree = build_tree(self.tmp / "tree")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def reasons(self, findings):
        return " | ".join("%s: %s" % (f.where, f.reason) for f in findings)


# ------------------------------------------------------------- frontmatter

class FrontmatterTest(TreeCase):
    def check(self, rel, content, is_skill=True):
        path = self.tree / rel
        write(path, content)
        return pc.frontmatter_findings(path, rel, is_skill=is_skill)

    def test_valid_skill_passes(self):
        # @spec PKG-CHECK-003, PKG-CHECK-004, PKG-CHECK-005, PKG-CHECK-006
        self.assertEqual(self.check("plugins/a/skills/demo/SKILL.md", skill_md("demo", "Fine.")), [])

    def test_opening_block(self):
        # @spec PKG-CHECK-003
        good = skill_md("demo", "Fine.").encode()
        for label, content in (("bom", b"\xef\xbb\xbf" + good), ("blank", b"\n" + good),
                               ("unclosed", b"---\nname: demo\ndescription: x\n")):
            findings = self.check("plugins/a/skills/demo/SKILL.md", content)
            self.assertTrue(any("no frontmatter block" in f.reason for f in findings), label)

    def test_carriage_returns_fail(self):
        # @spec PKG-CHECK-003
        findings = self.check("plugins/a/skills/demo/SKILL.md",
                              skill_md("demo", "Fine.").replace("\n", "\r\n").encode())
        self.assertTrue(any("line endings" in f.reason for f in findings), self.reasons(findings))

    def test_repeated_key_and_non_mapping(self):
        # @spec PKG-CHECK-004
        dup = '---\nname: demo\ndescription: "a"\ndescription: "b"\n---\n\nBody.\n'
        self.assertTrue(any("repeated key" in f.reason
                            for f in self.check("plugins/a/skills/demo/SKILL.md", dup)))
        seq = "---\n- a\n- b\n---\n\nBody.\n"
        self.assertTrue(any("mapping" in f.reason
                            for f in self.check("plugins/a/skills/demo/SKILL.md", seq)))
        bad = '---\nname: demo\ndescription: "unclosed\n---\n\nBody.\n'
        self.assertTrue(any("parse" in f.reason
                            for f in self.check("plugins/a/skills/demo/SKILL.md", bad)))

    def test_names(self):
        # @spec PKG-CHECK-005
        self.assertTrue(any("name" in f.reason for f in
                            self.check("plugins/a/skills/demo/SKILL.md", skill_md("other", "x"))))
        self.assertTrue(any("name" in f.reason for f in
                            self.check("plugins/a/skills/demo/SKILL.md",
                                       '---\ndescription: "x"\n---\n\nBody.\n')))
        self.assertTrue(any("name" in f.reason for f in
                            self.check("plugins/a/commands/alias.md",
                                       '---\nname: other\ndescription: "x"\n---\n\nB.\n',
                                       is_skill=False)))
        self.assertEqual(self.check("plugins/a/commands/alias.md",
                                    '---\ndescription: "x"\n---\n\nB.\n', is_skill=False), [])

    def test_description_length(self):
        # @spec PKG-CHECK-006
        rel = "plugins/a/skills/demo/SKILL.md"
        self.assertEqual(self.check(rel, skill_md("demo", "x" * 1024)), [])
        self.assertTrue(any("1,024" in f.reason for f in self.check(rel, skill_md("demo", "x" * 1025))))
        self.assertTrue(any("description" in f.reason
                            for f in self.check(rel, "---\nname: demo\n---\n\nBody.\n")))
        self.assertTrue(any("description" in f.reason for f in self.check(rel, skill_md("demo", ""))))

    def test_hash_read_as_comment(self):
        # @spec PKG-CHECK-007
        rel = "plugins/a/skills/demo/SKILL.md"
        truncated = "---\nname: demo\ndescription: Use it for issue #86 and more\n---\n\nBody.\n"
        findings = self.check(rel, truncated)
        self.assertTrue(any("description" in f.reason and "comment" in f.reason for f in findings),
                        self.reasons(findings))
        full_line = '---\n# a comment\nname: demo\ndescription: "x"\n---\n\nBody.\n'
        findings = self.check(rel, full_line)
        self.assertTrue(any("line 2" in f.reason for f in findings), self.reasons(findings))
        quoted = '---\nname: demo\ndescription: "Use it for issue #86 and C#"\n---\n\nBody.\n'
        self.assertEqual(self.check(rel, quoted), [])
        no_space = "---\nname: demo\ndescription: C#-style names\n---\n\nBody.\n"
        self.assertEqual(self.check(rel, no_space), [])
        colon_after = "---\nname: demo\ndescription: foo # bar: baz\n---\n\nBody.\n"
        findings = self.check(rel, colon_after)
        self.assertTrue(any("description" in f.reason and "comment" in f.reason for f in findings),
                        self.reasons(findings))

    def test_guard_literal(self):
        # @spec PKG-CHECK-008
        rel = "plugins/a/skills/demo/SKILL.md"
        self.assertEqual(self.check(rel, skill_md("demo", "x", extra="disable-model-invocation: true\n")), [])
        self.assertEqual(self.check(rel, skill_md("demo", "x", extra="disable-model-invocation: false\n")), [])
        for spelled in ("yes", "True", '"true"', "on"):
            findings = self.check(rel, skill_md("demo", "x", extra="disable-model-invocation: %s\n" % spelled))
            self.assertTrue(any("disable-model-invocation" in f.reason for f in findings), spelled)


class NamesTest(TreeCase):
    def test_tree_passes(self):
        # @spec PKG-CHECK-009
        self.assertEqual(pc.name_findings(self.tree), [])

    def test_command_sharing_a_skill_name(self):
        # @spec PKG-CHECK-009
        write(self.tree / "plugins/arrow-maintenance/commands/arrow-maintenance.md",
              '---\ndescription: "stub"\n---\n\nRun it.\n')
        findings = pc.name_findings(self.tree)
        self.assertTrue(any("arrow-maintenance" in f.reason for f in findings))

    def test_command_frontmatter_name_matching_a_skill(self):
        # @spec PKG-CHECK-009
        write(self.tree / "plugins/lid-experimental/commands/differential-audit.md",
              '---\nname: bidirectional-differential\ndescription: "x"\n---\n\nB.\n')
        self.assertTrue(pc.name_findings(self.tree))

    def test_skill_name_repeated_across_plugins(self):
        # @spec PKG-CHECK-009
        write(self.tree / "plugins/lid-experimental/skills/update-lid/SKILL.md",
              skill_md("update-lid", "Shadow."))
        self.assertTrue(any("update-lid" in f.reason for f in pc.name_findings(self.tree)))


# -------------------------------------------------------------------- size

class SizeTest(TreeCase):
    def test_body_limit(self):
        # @spec PKG-CHECK-010
        path = self.tree / "plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md"
        head = '---\nname: arrow-maintenance\ndescription: "x"\n---\n'
        lines = ("a" * 99 + "\n") * 500  # 50,000 bytes in lines well under 2,000 characters
        write(path, head + lines[:-1])
        self.assertEqual(pc.size_findings(self.tree), [])
        write(path, head + lines)
        self.assertTrue(any("50,000" in f.reason for f in pc.size_findings(self.tree)))

    def test_line_limit_ignores_evals(self):
        # @spec PKG-CHECK-011
        write(self.tree / "plugins/linked-intent-dev/skills/update-lid/evals/evals.json",
              "x" * 3000 + "\n")
        self.assertEqual(pc.size_findings(self.tree), [])
        write(self.tree / "plugins/linked-intent-dev/skills/linked-intent-dev/references/ears-syntax.md",
              "ok\n" + "y" * 2001 + "\n")
        findings = pc.size_findings(self.tree)
        self.assertTrue(any("ears-syntax.md" in f.where and "2,000" in f.reason for f in findings))


# ---------------------------------------------------------------- versions

class VersionsTest(TreeCase):
    def setUp(self):
        super().setUp()
        self.main = build_tree(self.tmp / "main", version="1.4.0")

    def raise_to(self, version, top_extra=""):
        self.tree = build_tree(self.tmp / ("v" + version), version=version, top_extra=top_extra,
                               stamp="1.4.0")
        return self.tree

    def findings(self, changed):
        return pc.version_findings(self.tree, self.main, changed)

    SHIPPED = ["plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md"]

    def test_unchanged_tree_passes(self):
        # @spec PKG-CHECK-012, PKG-CHECK-013, PKG-CHECK-014, PKG-CHECK-016
        self.tree = self.main
        self.assertEqual(self.findings([]), [])

    def test_versions_must_agree_and_stay_out_of_other_manifests(self):
        # @spec PKG-CHECK-012
        self.raise_to("1.4.1")
        write(self.tree / "plugins/lid-experimental/.claude-plugin/plugin.json",
              json.dumps({"name": "lid-experimental", "version": "0.3.0"}))
        self.assertTrue(any("same version" in f.reason for f in self.findings(self.SHIPPED)))
        self.raise_to("1.4.1")
        mk = json.loads((self.tree / ".claude-plugin/marketplace.json").read_text())
        mk["plugins"][0]["version"] = "1.4.1"
        write(self.tree / ".claude-plugin/marketplace.json", json.dumps(mk))
        write(self.tree / "plugins/arrow-maintenance/.cursor-plugin/plugin.json",
              json.dumps({"name": "arrow-maintenance", "version": "1.4.1"}))
        found = self.reasons(self.findings(self.SHIPPED))
        self.assertIn(".claude-plugin/marketplace.json", found)
        self.assertIn("arrow-maintenance/.cursor-plugin/plugin.json", found)

    def test_changelog_headings(self):
        # @spec PKG-CHECK-013
        self.raise_to("1.4.1")
        path = self.tree / "plugins/linked-intent-dev/CHANGELOG.md"
        good = path.read_text()
        for label, text in (
                ("unreleased", good.replace("## [1.4.1]", "## [Unreleased]\n\n- x\n\n## [1.4.1]")),
                ("hyphen date", good.replace("## [1.4.1] — 2026-10-24", "## [1.4.1] - 2026-10-24")),
                ("out of order", good.replace("## [1.4.0]", "## [1.4.2]")),
                ("repeated", good.replace("## [1.4.0]", "## [1.4.1]")),
                ("first not version", good.replace("## [1.4.1]", "## [1.4.3]"))):
            write(path, text)
            self.assertTrue(any("CHANGELOG" in f.where for f in self.findings(self.SHIPPED)), label)

    def test_shipped_change_must_raise_to_next_version(self):
        # @spec PKG-CHECK-014
        self.tree = build_tree(self.tmp / "same", version="1.4.0")
        self.assertTrue(any("next version" in f.reason for f in self.findings(self.SHIPPED)))
        self.raise_to("1.4.1")
        self.assertEqual(self.findings(self.SHIPPED), [])
        self.raise_to("1.4.2")
        self.assertTrue(any("next version" in f.reason for f in self.findings(self.SHIPPED)))

    def test_changelog_counts_and_evals_do_not(self):
        # @spec PKG-CHECK-014
        self.tree = build_tree(self.tmp / "same", version="1.4.0")
        self.assertTrue(self.findings(["plugins/linked-intent-dev/CHANGELOG.md"]))
        self.assertEqual(self.findings(["plugins/linked-intent-dev/skills/update-lid/evals/evals.json"]), [])

    def test_no_shipped_change_keeps_main_version(self):
        # @spec PKG-CHECK-014
        self.raise_to("1.4.1")
        self.assertTrue(any("equal" in f.reason for f in self.findings(["docs/setup.md"])))

    def test_version_only_raise_is_not_a_shipped_change(self):
        # @spec PKG-CHECK-014
        self.raise_to("1.4.1")
        manifests = ["plugins/%s/.claude-plugin/plugin.json" % p
                     for p in ("linked-intent-dev", "arrow-maintenance", "lid-experimental")]
        self.assertTrue(any("equal" in f.reason for f in self.findings(manifests + ["docs/setup.md"])))
        path = self.tree / "plugins/arrow-maintenance/.claude-plugin/plugin.json"
        data = json.loads(path.read_text())
        data["description"] = "changed"
        write(path, json.dumps(data))
        self.assertEqual(self.findings(manifests), [])

    def test_migration_heading(self):
        # @spec PKG-CHECK-015
        self.raise_to("1.5.0")
        self.assertTrue(any("Migration" in f.reason for f in self.findings(self.SHIPPED)))
        self.raise_to("1.5.0", top_extra="\n### Migration (v1.4 → v1.5)\n- step\n")
        self.assertEqual(self.findings(self.SHIPPED), [])
        self.raise_to("1.5.0", top_extra="\n### Migration (v1.3 → v1.5)\n- step\n")
        self.assertTrue(any("Migration" in f.reason for f in self.findings(self.SHIPPED)))
        self.raise_to("1.5.0", top_extra="\n### Migration (v1.4 → v1.5)\n- a\n\n### Migration notes\n- b\n")
        self.assertTrue(any("Migration" in f.reason for f in self.findings(self.SHIPPED)))
        self.raise_to("1.4.1", top_extra="\n### Migration (v1.4 → v1.4)\n- step\n")
        self.assertTrue(any("Migration" in f.reason for f in self.findings(self.SHIPPED)))

    def test_workflow_doc_stale_after_source_edit(self):
        # @spec PKG-CHECK-016
        self.raise_to("1.4.1")
        core = self.tree / "plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md"
        write(core, core.read_text().replace("Body of the workflow.", "Edited body."))
        changed = self.SHIPPED + ["plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md"]
        self.assertTrue(any("workflow doc" in f.reason for f in self.findings(changed)))
        doc = self.tree / "plugins/linked-intent-dev/skills/update-lid/references/workflow-doc.md"
        write(doc, pc.assemble_workflow_doc(core.parent, "1.4.0"))
        self.assertTrue(any("stamp" in f.reason for f in self.findings(changed)))
        write(doc, pc.assemble_workflow_doc(core.parent, "1.4.1"))
        self.assertEqual(self.findings(changed + [str(doc.relative_to(self.tree))]), [])

    def test_workflow_doc_restamped_without_content_change(self):
        # @spec PKG-CHECK-016
        self.tree = build_tree(self.tmp / "restamp", version="1.4.1", stamp="1.4.1")
        self.assertTrue(any("stamp" in f.reason for f in self.findings(self.SHIPPED)))

    def test_next_versions(self):
        # @spec PKG-CHECK-014
        self.assertEqual(pc.next_versions("1.4.0"), {"1.4.1", "1.5.0", "2.0.0"})


class CommitTest(unittest.TestCase):
    def test_ambiguous_revision_is_reported(self):
        # @spec PKG-CHECK-001
        self.assertEqual(pc.single_commit("abc123\n", "@-"), "abc123")
        with self.assertRaises(pc.GitError) as caught:
            pc.single_commit("abc123\ndef456\n", "@-")
        self.assertIn("--rev", str(caught.exception))


class ExecutableTest(unittest.TestCase):
    def test_tool_is_executable(self):
        # @spec PKG-CHECK-001
        self.assertTrue(os.access(HERE / "packaging_checks.py", os.X_OK))


class TagTest(unittest.TestCase):
    def test_tag_state(self):
        # @spec PKG-CHECK-017
        self.assertEqual(pc.tag_findings("1.4.0", True), [])
        self.assertTrue(any("v1.4.0" in f.reason for f in pc.tag_findings("1.4.0", False)))
        self.assertTrue(pc.tag_findings("1.4.0", None)[0].error)


# --------------------------------------------------------------- structure

class StructureTest(TreeCase):
    def test_tree_passes(self):
        # @spec PKG-CHECK-018, PKG-CHECK-019, PKG-CHECK-020
        self.assertEqual(pc.structure_findings(self.tree), [])

    def test_broken_links(self):
        # @spec PKG-CHECK-018
        write(self.tree / "CONTRIBUTING.md",
              "# C\n\n[a](docs/missing.md) [b](docs/setup.md#nowhere) [c](#absent)\n")
        found = self.reasons(pc.structure_findings(self.tree))
        for target in ("docs/missing.md", "#nowhere", "#absent"):
            self.assertIn(target, found)

    def test_anchor_keeps_literal_underscores(self):
        # @spec PKG-CHECK-018
        write(self.tree / "docs/setup.md", "# Setup\n\n## Claude Code\n\n## The `run_eval.py` flags\n\n## _Emphasis_ here\n")
        write(self.tree / "CONTRIBUTING.md",
              "# C\n\n[a](docs/setup.md#the-run_evalpy-flags) [b](docs/setup.md#emphasis-here)\n")
        self.assertEqual(pc.structure_findings(self.tree), [])

    def test_manifests(self):
        # @spec PKG-CHECK-019
        write(self.tree / ".cursor-plugin/marketplace.json", "{not json")
        mk = json.loads((self.tree / ".claude-plugin/marketplace.json").read_text())
        mk["plugins"][0]["source"] = "./plugins/gone"
        write(self.tree / ".claude-plugin/marketplace.json", json.dumps(mk))
        found = self.reasons(pc.structure_findings(self.tree))
        self.assertIn(".cursor-plugin/marketplace.json", found)
        self.assertIn("plugins/gone", found)

    def test_claude_symlink(self):
        # @spec PKG-CHECK-020
        (self.tree / "CLAUDE.md").unlink()
        write(self.tree / "CLAUDE.md", "# Agents\n")
        self.assertTrue(any("CLAUDE.md" in f.where for f in pc.structure_findings(self.tree)))


# ------------------------------------------------------- workflow doc assembly

class AssemblyTest(unittest.TestCase):
    def test_reproduces_the_shipped_doc(self):
        # @spec PKG-CHECK-036
        doc = REPO_ROOT / pc.WORKFLOW_DOC
        stamp, _ = pc.split_stamp(doc.read_text())
        self.assertEqual(pc.assemble_workflow_doc(REPO_ROOT / pc.CORE_SKILL, stamp), doc.read_text())

    def test_structure(self):
        # @spec PKG-CHECK-036
        tmp = Path(tempfile.mkdtemp())
        try:
            tree = build_tree(tmp / "t")
            text = pc.assemble_workflow_doc(tree / pc.CORE_SKILL, "9.8.7")
            self.assertEqual(pc.split_stamp(text)[0], "9.8.7")
            self.assertNotIn("LID-on-LID exception", text)
            self.assertNotIn("name: linked-intent-dev", text)
            self.assertLess(text.index("Appended reference: ears-syntax.md"),
                            text.index("Appended reference: lld-templates.md"))
            self.assertIn("No trailing newline.\n\n\n---\n\n<!-- Appended reference: lld-templates.md -->", text)
        finally:
            shutil.rmtree(tmp)


# ------------------------------------------------------------------ states

class StatesTest(unittest.TestCase):
    def test_precedence(self):
        # @spec PKG-CHECK-030
        F = pc.Finding
        self.assertEqual(pc.part_state([]), "pass")
        self.assertEqual(pc.part_state([F("g", "w", "r", inconclusive=True)]), "inconclusive")
        self.assertEqual(pc.part_state([F("g", "w", "r", inconclusive=True), F("g", "w", "r", error=True)]),
                         "error")
        self.assertEqual(pc.part_state([F("g", "w", "r", error=True), F("g", "w", "r")]), "fail")

    def test_exit_code(self):
        # @spec PKG-CHECK-030
        self.assertEqual(pc.exit_code({"static": "pass", "claude-code": "skipped", "opencode": "pass"}), 0)
        for bad in ("fail", "error", "inconclusive", "owed"):
            self.assertEqual(pc.exit_code({"static": "pass", "claude-code": bad, "opencode": "pass"}), 1)

    def test_host_trigger(self):
        # @spec PKG-CHECK-031
        self.assertTrue(pc.host_trigger(["plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md"]))
        self.assertTrue(pc.host_trigger(["plugins/linked-intent-dev/CHANGELOG.md"]))
        self.assertTrue(pc.host_trigger(["tools/packaging-checks/packaging_checks.py"]))
        self.assertTrue(pc.host_trigger(["tools/alt-model-evals/Dockerfile"]))
        self.assertTrue(pc.host_trigger(["tools/alt-model-evals/run_eval.py"]))
        self.assertFalse(pc.host_trigger(["plugins/linked-intent-dev/skills/update-lid/evals/evals.json"]))
        self.assertFalse(pc.host_trigger(["docs/setup.md", "tools/alt-model-evals/test_run_eval.py"]))


# --------------------------------------------------------------- host parts

def stream(*events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


class FakeClaude:
    """Stands in for `claude -p`: writes a session transcript and returns stream-json."""

    def __init__(self, projects, tree, **faults):
        self.projects = Path(projects)
        self.tree = Path(tree)
        self.faults = faults
        self.calls = []

    def skills(self):
        out = []
        for plugin in sorted((self.tree / "plugins").iterdir()):
            for skill in sorted((plugin / "skills").glob("*/SKILL.md")):
                try:
                    fm, body = pc.read_frontmatter(skill)
                except Exception:  # a host loads such a file with empty metadata
                    fm, body = {"description": ""}, skill.read_text()
                out.append((plugin.name, skill.parent.name, fm, body))
        return out

    def __call__(self, argv, cwd):
        cwd = Path(cwd)
        self.calls.append(argv)
        if self.faults.get("missing"):
            raise FileNotFoundError("claude")
        sid = argv[argv.index("--session-id") + 1]
        prompt = argv[2]
        version = json.loads((self.tree / "plugins/linked-intent-dev/.claude-plugin/plugin.json").read_text())["version"]
        plugins = [{"name": p.name, "path": str(p), "source": p.name + "@inline",
                    "version": self.faults.get("version", version)}
                   for p in sorted((self.tree / "plugins").iterdir())]
        if self.faults.get("no_versions"):
            plugins = [{k: v for k, v in p.items() if k != "version"} for p in plugins]
        plugins.append({"name": "cc-plugin-telemetry", "path": "builtin", "source": "cc-plugin-telemetry@builtin"})
        names = ["%s:%s" % (p, s) for p, s, _, _ in self.skills()]
        names += ["%s:%s" % (c.parent.parent.name, c.stem)
                  for c in sorted((self.tree / "plugins").glob("*/commands/*.md"))]
        if self.faults.get("twice"):
            names.append(names[0])
        init = {"type": "system", "subtype": "init", "claude_code_version": "2.1.310",
                "model": "claude-sonnet-5-5", "plugins": plugins, "slash_commands": names + ["bundled"],
                "skills": names}
        if self.faults.get("no_slash"):
            del init["slash_commands"]
        transcript = []
        events = [init]
        if prompt.startswith("/"):
            plugin, skill = prompt.split()[0][1:].split(":")
            body = next(b for p, s, _, b in self.skills() if (p, s) == (plugin, skill))
            if self.faults.get("stub_body") == skill:
                body = "Invoke the skill.\n"
            transcript.append({"type": "user", "isMeta": True, "message": {"role": "user", "content": [
                {"type": "text", "text": "Base directory for this skill: /x\n\n" + body}]}})
        else:
            listing = []
            for plugin, skill, fm, _ in self.skills():
                guarded = fm.get("disable-model-invocation") is True
                if guarded and self.faults.get("leak") != skill:
                    continue
                desc = fm["description"]
                if self.faults.get("stub_description") == skill:
                    desc = "A stub's description."
                listing.append("- %s:%s: %s" % (plugin, skill, desc))
            listing.append("- deep-research: Bundled skill.")
            transcript.append({"type": "attachment", "attachment": {
                "type": "skill_listing", "content": "\n".join(listing)}})
            if not self.faults.get("no_call"):
                for plugin, skill, fm, _ in self.skills():
                    if fm.get("disable-model-invocation") is True and ("%s:%s" % (plugin, skill)) in prompt:
                        tid = "t-" + skill
                        events.append({"type": "assistant", "message": {"content": [
                            {"type": "tool_use", "id": tid, "name": "Skill",
                             "input": {"skill": "%s:%s" % (plugin, skill)}}]}})
                        refused = not self.faults.get("not_refused")
                        text = ("<tool_use_error>Skill %s:%s cannot be used with Skill tool due to "
                                "disable-model-invocation.</tool_use_error>" % (plugin, skill))
                        if self.faults.get("reworded"):
                            text = "<tool_use_error>Only the user can start %s.</tool_use_error>" % skill
                        if not refused:
                            text = "Base directory for this skill: /x\n\nBody."
                        events.append({"type": "user", "message": {"content": [
                            {"type": "tool_result", "tool_use_id": tid, "is_error": refused,
                             "content": text}]}})
        if self.faults.get("max_turns") and not prompt.startswith("/"):
            events.append({"type": "result", "subtype": "error_max_turns", "is_error": True,
                           "result": "Reached maximum number of turns"})
        else:
            events.append({"type": "result", "subtype": "success", "is_error": False, "result": "DONE"})
        if not self.faults.get("no_transcript"):
            folder = self.projects / ("-scratch-" + sid[:8])
            if self.faults.get("marker"):
                folder = self.projects / ("-private-var-" + cwd.name.replace("_", "-"))
                (folder / "memory").mkdir(parents=True, exist_ok=True)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (sid + ".jsonl")).write_text("\n".join(json.dumps(t) for t in transcript) + "\n")
        return stream(*events)


class ClaudeCodePartTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tree = build_tree(self.tmp / "tree")
        self.projects = self.tmp / "projects"
        self.projects.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_part(self, **faults):
        fake = FakeClaude(self.projects, self.tree, **faults)
        return pc.claude_code_part(self.tree, runner=fake, projects_root=self.projects), fake

    def test_healthy_host_passes_and_cleans_up(self):
        # @spec PKG-CHECK-021, PKG-CHECK-022, PKG-CHECK-023, PKG-CHECK-024, PKG-CHECK-025, PKG-CHECK-026
        part, fake = self.run_part()
        self.assertEqual(part.state, "pass", [f.reason for f in part.findings])
        self.assertIn("2.1.310", part.detail)
        self.assertIn("claude-sonnet-5-5", part.detail)
        self.assertIn("1 other", part.detail)
        self.assertEqual(list(self.projects.iterdir()), [])
        argv = fake.calls[0]
        self.assertIn("--plugin-dir", argv)
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "project")

    def test_stub_description_fails(self):
        # @spec PKG-CHECK-024
        part, _ = self.run_part(stub_description="arrow-maintenance")
        self.assertEqual(part.state, "fail")
        self.assertTrue(any("arrow-maintenance" in f.where for f in part.findings))

    def test_guard_leak_fails(self):
        # @spec PKG-CHECK-025
        part, _ = self.run_part(leak="update-lid")
        self.assertEqual(part.state, "fail")

    def test_guard_call_not_made_is_inconclusive(self):
        # @spec PKG-CHECK-025, PKG-CHECK-026
        part, _ = self.run_part(no_call=True)
        self.assertEqual(part.state, "inconclusive")

    def test_stub_body_fails(self):
        # @spec PKG-CHECK-023
        part, _ = self.run_part(stub_body="arrow-maintenance")
        self.assertEqual(part.state, "fail")

    def test_wrong_plugin_version_fails(self):
        # @spec PKG-CHECK-022
        part, _ = self.run_part(version="9.9.9")
        self.assertEqual(part.state, "fail")

    def test_missing_host_is_error_with_hint(self):
        # @spec PKG-CHECK-032
        part, _ = self.run_part(missing=True)
        self.assertEqual(part.state, "error")
        self.assertIn("--no-host", " ".join(f.reason for f in part.findings))

    def test_unreadable_record_is_error(self):
        # @spec PKG-CHECK-026
        part, _ = self.run_part(no_transcript=True)
        self.assertEqual(part.state, "error")

    def test_record_format_drift_is_error_not_fail(self):
        # @spec PKG-CHECK-026, PKG-CHECK-030
        for fault in ("no_versions", "no_slash"):
            part, _ = self.run_part(**{fault: True})
            self.assertEqual(part.state, "error", fault)

    def test_reworded_refusal_still_counts(self):
        # @spec PKG-CHECK-025
        part, _ = self.run_part(reworded=True)
        self.assertEqual(part.state, "pass", [f.reason for f in part.findings])

    def test_guard_not_refused_fails(self):
        # @spec PKG-CHECK-025
        part, _ = self.run_part(not_refused=True)
        self.assertEqual(part.state, "fail")
        self.assertTrue(any("did not refuse" in f.reason for f in part.findings))

    def test_name_registered_twice_fails(self):
        # @spec PKG-CHECK-022
        part, _ = self.run_part(twice=True)
        self.assertEqual(part.state, "fail")
        self.assertTrue(any("registered 2 times" in f.reason for f in part.findings))

    def test_run_folder_removed_even_with_other_contents(self):
        # @spec PKG-CHECK-026
        part, _ = self.run_part(marker=True)
        self.assertEqual(list(self.projects.iterdir()), [])

    def test_unparseable_skill_is_not_a_vacuous_pass(self):
        # @spec PKG-CHECK-023
        write(self.tree / "plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md", "no frontmatter\n")
        part, _ = self.run_part()
        self.assertEqual(part.state, "fail")
        self.assertTrue(any("arrow-maintenance" in f.where for f in part.findings))

    def test_session_ending_in_error_is_explained(self):
        # @spec PKG-CHECK-026
        part, _ = self.run_part(max_turns=True)
        self.assertEqual(part.state, "error")
        self.assertIn("ended in an error", " ".join(f.reason for f in part.findings))


class OpencodePartTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tree = build_tree(self.tmp / "tree")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def report(self, drop=None, desc=None, content=None):
        out = [{"name": "customize-opencode", "description": "x", "location": "<built-in>", "content": "x"}]
        for skill in sorted((self.tree / "plugins").glob("*/skills/*/SKILL.md")):
            fm, body = pc.read_frontmatter(skill)
            name = skill.parent.name
            if name == drop:
                continue
            out.append({"name": name, "location": "/work/plugins/" + str(skill.relative_to(self.tree / "plugins")),
                        "description": desc if name == "arrow-maintenance" and desc else fm["description"],
                        "content": content if name == "arrow-maintenance" and content else body})
        return json.dumps(out)

    def test_healthy_report_passes_with_known_limits(self):
        # @spec PKG-CHECK-027, PKG-CHECK-028, PKG-CHECK-029
        part = pc.opencode_part(self.tree, runner=lambda tree: self.report())
        self.assertEqual(part.state, "pass", [f.reason for f in part.findings])
        self.assertIn("guard: not honored", part.detail)
        self.assertIn("command aliases: not loaded", part.detail)
        self.assertIn(pc.opencode_version(), part.detail)

    def test_guard_honored_when_guarded_skills_absent(self):
        # @spec PKG-CHECK-029
        part = pc.opencode_part(self.tree, runner=lambda tree: self.report(drop="update-lid"))
        self.assertIn("guard: honored", part.detail)
        self.assertEqual(part.state, "pass")

    def test_mismatches_fail(self):
        # @spec PKG-CHECK-028
        for kwargs in ({"drop": "arrow-maintenance"}, {"desc": "Truncated"}, {"content": "Stub.\n"}):
            part = pc.opencode_part(self.tree, runner=lambda tree, k=kwargs: self.report(**k))
            self.assertEqual(part.state, "fail", kwargs)

    def test_report_of_the_wrong_shape_is_error(self):
        # @spec PKG-CHECK-030
        part = pc.opencode_part(self.tree, runner=lambda tree: '{"skills": []}')
        self.assertEqual(part.state, "error")

    def test_unloadable_runner_is_error(self):
        # @spec PKG-CHECK-030
        original = pc._runner_module
        def broken():
            raise FileNotFoundError("tools/alt-model-evals/run_eval.py")
        pc._runner_module = broken
        try:
            part = pc.opencode_part(self.tree, runner=lambda tree: self.report())
        finally:
            pc._runner_module = original
        self.assertEqual(part.state, "error")

    def test_no_container_runtime_is_error(self):
        # @spec PKG-CHECK-032
        def boom(tree):
            raise pc.HostUnavailable("no container runtime is reachable")
        part = pc.opencode_part(self.tree, runner=boom)
        self.assertEqual(part.state, "error")
        self.assertIn("--no-host", " ".join(f.reason for f in part.findings))


# ------------------------------------------------------------- result line

class ReportTest(unittest.TestCase):
    def test_every_finding_is_printed_with_where_and_reason(self):
        # @spec PKG-CHECK-034
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            pc.report([pc.Part("static", [pc.Finding("versions", "plugins/x.json", "a reason")])])
        self.assertIn("plugins/x.json: a reason", out.getvalue())


class ResultLineTest(unittest.TestCase):
    def test_line_names_everything(self):
        # @spec PKG-CHECK-033
        static = pc.Part("static", [pc.Finding("versions", "x", "r")])
        cc = pc.Part("claude-code", [], detail="Claude Code 2.1.310, claude-sonnet-5-5, isolated")
        oc = pc.Part("opencode", [], detail="opencode 1.18.32; guard: not honored")
        line = pc.result_line({"commit": "abcdef1234567", "tree": "0123456789abc", "main": "fedcba9876543"},
                              [static, cc, oc])
        for piece in ("abcdef123456", "0123456789ab", "fedcba987654", "static: fail (versions)",
                      "claude-code: pass", "2.1.310", "opencode: pass", "1.18.32"):
            self.assertIn(piece, line)


# ----------------------------------------------------------- end to end

def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd)] + list(args), check=True,
                          capture_output=True, text=True).stdout.strip()


class EndToEndTest(unittest.TestCase):
    """A local repository and a bare one standing in for github.com/jszmajda/lid."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.remote = self.tmp / "remote.git"
        self.repo = self.tmp / "repo"
        build_tree(self.repo, version="1.4.0")
        write(self.repo / "tools/packaging-checks/packaging_checks.py",
              (HERE / "packaging_checks.py").read_text())
        git(self.tmp, "init", "-q", "-b", "main", str(self.repo))
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "tag", "v1.4.0")
        git(self.tmp, "init", "-q", "--bare", str(self.remote))
        git(self.repo, "push", "-q", str(self.remote), "main", "--tags")
        self.env = dict(os.environ, PACKAGING_CHECKS_REMOTE=str(self.remote))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit_change(self, version="1.4.1", message="change"):
        build_tree(self.repo, version=version, stamp="1.4.0")
        path = self.repo / "plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md"
        write(path, path.read_text() + "More.\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)

    def run_tool(self, *args, script=None):
        script = script or (self.repo / "tools/packaging-checks/packaging_checks.py")
        return subprocess.run([sys.executable, str(script)] + list(args), cwd=self.repo, env=self.env,
                              capture_output=True, text=True)

    def test_raised_change_passes_static_and_owes_hosts(self):
        # @spec PKG-CHECK-001, PKG-CHECK-002, PKG-CHECK-032, PKG-CHECK-033, PKG-CHECK-038
        self.commit_change()
        out = self.run_tool("--no-host")
        line = out.stdout.strip().splitlines()[-1]
        self.assertIn("static: pass", line, out.stdout + out.stderr)
        self.assertIn("claude-code: owed", line)
        self.assertIn("opencode: owed", line)
        self.assertIn(git(self.repo, "rev-parse", "HEAD")[:12], line)
        self.assertEqual(out.returncode, 1)

    def test_docs_only_change_skips_hosts(self):
        # @spec PKG-CHECK-031
        write(self.repo / "docs/setup.md", "# Setup\n\n## Claude Code\n\nMore.\n")
        git(self.repo, "commit", "-qam", "docs")
        out = self.run_tool()
        line = out.stdout.strip().splitlines()[-1]
        self.assertIn("claude-code: skipped", line, out.stdout + out.stderr)
        self.assertIn("opencode: skipped", line)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_working_copy_edits_are_not_checked(self):
        # @spec PKG-CHECK-001
        self.commit_change()
        bad = self.repo / "plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md"
        write(bad, "no frontmatter\n")
        out = self.run_tool("--no-host")
        self.assertIn("static: pass", out.stdout, out.stdout + out.stderr)

    def test_runs_the_checked_commits_copy_of_the_tool(self):
        # @spec PKG-CHECK-001
        self.commit_change()
        local = self.repo / "tools/packaging-checks/packaging_checks.py"
        write(local, local.read_text().replace("MAX_DESCRIPTION = 1024", "MAX_DESCRIPTION = 1"))
        out = self.run_tool("--no-host")
        self.assertIn("static: pass", out.stdout, out.stdout + out.stderr)

    def test_branch_behind_main_fails(self):
        # @spec PKG-CHECK-002
        git(self.repo, "checkout", "-q", "-b", "feature")
        self.commit_change()
        git(self.repo, "checkout", "-q", "main")
        write(self.repo / "docs/setup.md", "# Setup\n\n## Claude Code\n\nNewer.\n")
        git(self.repo, "commit", "-qam", "main moves")
        git(self.repo, "push", "-q", str(self.remote), "main")
        git(self.repo, "checkout", "-q", "feature")
        out = self.run_tool("--no-host")
        self.assertIn("static: fail", out.stdout)
        self.assertIn("up to date", out.stdout + out.stderr)

    def test_unreachable_remote_is_error(self):
        # @spec PKG-CHECK-002
        self.commit_change()
        self.env["PACKAGING_CHECKS_REMOTE"] = str(self.tmp / "nowhere.git")
        out = self.run_tool("--no-host")
        self.assertIn("static: error", out.stdout, out.stdout + out.stderr)

    def test_untagged_main_version_fails(self):
        # @spec PKG-CHECK-017
        git(self.remote, "tag", "-d", "v1.4.0")
        self.commit_change()
        out = self.run_tool("--no-host")
        self.assertIn("v1.4.0", out.stdout + out.stderr)
        self.assertIn("static: fail", out.stdout)

    def test_regenerated_doc_passes_its_own_check(self):
        # @spec PKG-CHECK-016, PKG-CHECK-036
        last = self.repo / "plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md"
        write(last, "# LLD Templates Reference\n\nTwo trailing newlines.\n\n")
        core = self.repo / "plugins/linked-intent-dev/skills/linked-intent-dev"
        write(self.repo / pc.WORKFLOW_DOC, pc.assemble_workflow_doc(core, "1.4.0"))
        git(self.repo, "commit", "-qam", "base with two trailing newlines")
        git(self.repo, "push", "-q", str(self.remote), "main")
        for p in ("linked-intent-dev", "arrow-maintenance", "lid-experimental"):
            path = self.repo / "plugins" / p / ".claude-plugin/plugin.json"
            data = json.loads(path.read_text())
            data["version"] = "1.4.1"
            write(path, json.dumps(data))
        self.assertEqual(self.run_tool("--write-workflow-doc").returncode, 0)
        self.assertEqual(pc.split_stamp((self.repo / pc.WORKFLOW_DOC).read_text())[0], "1.4.0")

    def test_write_workflow_doc(self):
        # @spec PKG-CHECK-036
        core = self.repo / "plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md"
        write(core, core.read_text().replace("Body of the workflow.", "Edited."))
        for p in ("linked-intent-dev", "arrow-maintenance", "lid-experimental"):
            path = self.repo / "plugins" / p / ".claude-plugin/plugin.json"
            data = json.loads(path.read_text())
            data["version"] = "1.4.1"
            write(path, json.dumps(data))
        out = self.run_tool("--write-workflow-doc")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        doc = (self.repo / pc.WORKFLOW_DOC).read_text()
        self.assertEqual(pc.split_stamp(doc)[0], "1.4.1")
        self.assertIn("Edited.", doc)


if __name__ == "__main__":
    unittest.main()
