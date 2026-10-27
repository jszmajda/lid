#!/usr/bin/env python3
"""Check what LID's plugins ship before a merge to main.

    tools/packaging-checks/packaging_checks.py [--rev REV] [--no-host]
    tools/packaging-checks/packaging_checks.py --write-workflow-doc

A run exports one commit (by default the one holding the current change),
fetches main from github.com/jszmajda/lid, and runs three parts from the
export's own copy of this tool:

  static       frontmatter, sizes, versions, CHANGELOG, workflow doc, links,
               manifests, symlink; no model, no host
  claude-code  loads the plugins into `claude -p` and reads what Claude Code
               recorded: registration, the model's skill listing, delivered
               skill bodies, and the refusal of guarded skills
  opencode     loads the plugins into the alternate-model runner's opencode
               container and reads `opencode debug skill`; no model

It prints one result line for the pull request's "Packaging checks" line and
exits non-zero unless every part is pass or skipped. --no-host leaves the host
parts owed to the maintainer. --write-workflow-doc regenerates the shipped
workflow doc in the working copy, stamped per the version rule.

Design: docs/intent/packaging-checks/packaging-checks-design.md
Specs:  docs/intent/packaging-checks/packaging-checks-specs.md
"""

import argparse
import concurrent.futures
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_REMOTE = "https://github.com/jszmajda/lid.git"

CORE_PLUGIN = "linked-intent-dev"
CORE_PLUGIN_JSON = "plugins/linked-intent-dev/.claude-plugin/plugin.json"
CHANGELOG = "plugins/linked-intent-dev/CHANGELOG.md"
CORE_SKILL = "plugins/linked-intent-dev/skills/linked-intent-dev"
WORKFLOW_DOC = "plugins/linked-intent-dev/skills/update-lid/references/workflow-doc.md"
MARKETPLACES = (".claude-plugin/marketplace.json", ".cursor-plugin/marketplace.json")
LINK_CHECKED = ("CONTRIBUTING.md", "docs/setup.md")
HOST_TRIGGERS = ("tools/packaging-checks/", "tools/alt-model-evals/Dockerfile",
                 "tools/alt-model-evals/run_eval.py")

MAX_DESCRIPTION = 1024
MAX_BODY_BYTES = 50000
MAX_LINE = 2000
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_HEADING = re.compile(r"^\[(\d+\.\d+\.\d+)\]( — \d{4}-\d{2}-\d{2})?$")
GUARD = "disable-model-invocation"

CLAUDE_MODEL = "claude-sonnet-5-5"
CLAUDE_TIMEOUT = 300

STAMP_LINE = re.compile(
    r"^     Assembled from the linked-intent-dev plugin \(version (\d+\.\d+\.\d+)\) at release\.$",
    re.M)
HEADER = """<!-- GENERATED FILE — do not edit here.
     Assembled from the linked-intent-dev plugin (version @VERSION@) at release.
     Changes belong upstream (in the plugin) or in this project's instruction file.
     Re-sync via /update-lid where available; see docs/setup.md otherwise. -->

# LID Workflow (vendored)

The full linked-intent-development workflow, vendored for agent harnesses without a plugin system. Read this before making code changes in this project. The reference material this workflow cites (`references/...` paths) is appended as sections at the end of this document — the content is here, not in a references directory. References to `docs/decisions/` and `docs/intent/...` paths inside LID-specific passages describe LID's own repository — consult them at the LID repo, not in this project. Mentions of the `update-lid` skill, `/arrow-maintenance`, and `/lid-coach` name LID plugin skills a harness without a plugin system does not have; this project is already set up, so treat them as pointers to the LID repository rather than steps to run.

---

"""


class HostUnavailable(Exception):
    """A host part could not start or finish: not installed, no login, no runtime."""


class Finding:
    def __init__(self, group, where, reason, error=False, inconclusive=False):
        self.group = group
        self.where = where
        self.reason = reason
        self.error = error
        self.inconclusive = inconclusive

    def kind(self):
        return "error" if self.error else "inconclusive" if self.inconclusive else "fail"


# @spec PKG-CHECK-030
def part_state(findings):
    kinds = {f.kind() for f in findings}
    for state in ("fail", "error", "inconclusive"):
        if state in kinds:
            return state
    return "pass"


class Part:
    def __init__(self, name, findings, detail="", state=None):
        self.name = name
        self.findings = findings
        self.detail = detail
        self.state = state or part_state(findings)


# @spec PKG-CHECK-030
def exit_code(states):
    return 0 if all(s in ("pass", "skipped") for s in states.values()) else 1


# ------------------------------------------------------------- frontmatter

class NoBlock(Exception):
    pass


class RepeatedKey(yaml.YAMLError):
    pass


class StrictLoader(yaml.SafeLoader):
    """PyYAML's safe loader, rejecting a repeated mapping key."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise RepeatedKey("repeated key %r on line %d" % (key, key_node.start_mark.line + 2))
            seen.add(key)
        return super().construct_mapping(node, deep)


def split_frontmatter(data):
    """(block text, body bytes) for a file opening with a `---` block."""
    if not data.startswith(b"---\n"):
        raise NoBlock()
    lines = data.split(b"\n")
    for i in range(1, len(lines)):
        if lines[i] == b"---":
            return b"\n".join(lines[1:i]).decode("utf-8"), b"\n".join(lines[i + 1:])
    raise NoBlock()


def read_frontmatter(path):
    """The parsed frontmatter mapping and body text of a skill or command file."""
    block, body = split_frontmatter(Path(path).read_bytes())
    return yaml.load(block, Loader=StrictLoader) or {}, body.decode("utf-8")


def _unreplace(value, mark):
    if isinstance(value, str):
        return value.replace(mark, "#")
    if isinstance(value, dict):
        return {_unreplace(k, mark): _unreplace(v, mark) for k, v in value.items()}
    if isinstance(value, list):
        return [_unreplace(v, mark) for v in value]
    return value


def _comment_mark(text):
    for code in range(0xE000, 0xF8FF):
        mark = chr(code)
        if mark not in text:
            return mark
    raise RuntimeError("no free private-use character")


# @spec PKG-CHECK-003, PKG-CHECK-004, PKG-CHECK-005, PKG-CHECK-006, PKG-CHECK-007, PKG-CHECK-008
def frontmatter_findings(path, rel, is_skill=True):
    def bad(reason):
        return Finding("frontmatter", rel, reason)

    findings = []
    data = Path(path).read_bytes()
    if b"\r" in data:
        findings.append(bad("line endings: carriage returns found; use line feeds alone"))
        data = data.replace(b"\r\n", b"\n")
    try:
        block, _ = split_frontmatter(data)
    except NoBlock:
        return findings + [bad("no frontmatter block: the file must open with exactly '---' and a "
                               "line feed (no byte-order mark or blank line first), and close it "
                               "with a '---' line")]
    except UnicodeDecodeError:
        return findings + [bad("frontmatter is not UTF-8")]
    try:
        fm = yaml.load(block, Loader=StrictLoader)
    except RepeatedKey as e:
        return findings + [bad("frontmatter has a %s" % e)]
    except yaml.YAMLError as e:
        return findings + [bad("frontmatter does not parse: %s" % " ".join(str(e).split()))]
    if not isinstance(fm, dict):
        return findings + [bad("frontmatter is not a mapping")]

    own = Path(path).parent.name if is_skill else Path(path).stem
    name = fm.get("name")
    if is_skill:
        if not isinstance(name, str) or not name.strip():
            findings.append(bad("name: missing or empty; it must equal the directory name '%s'" % own))
        elif name != own:
            findings.append(bad("name: '%s' differs from its directory name '%s'" % (name, own)))
    elif "name" in fm and name != own:
        findings.append(bad("name: '%s' differs from its filename '%s'" % (name, own)))

    description = fm.get("description")
    if not isinstance(description, str) or not description.strip():
        findings.append(bad("description: missing or empty"))
    elif len(description) > MAX_DESCRIPTION:
        findings.append(bad("description: %d characters, over the 1,024 limit" % len(description)))

    if "#" in block:
        mark = _comment_mark(data.decode("utf-8"))
        try:
            again = _unreplace(yaml.load(block.replace("#", mark), Loader=StrictLoader), mark)
        except yaml.YAMLError:
            again = None
        if again != fm:
            if isinstance(again, dict):
                fields = sorted(str(k) for k in set(fm) | set(again) if fm.get(k) != again.get(k))
                findings.append(bad("%s: a '#' is read as a YAML comment and cuts the value short; "
                                    "quote the value" % ", ".join(fields)))
            else:
                lines = [(i + 2, line) for i, line in enumerate(block.split("\n"))
                         if re.search(r"(^|\s)#", line)]
                fields = [m.group(1) for _, line in lines for m in [re.match(r"^([\w-]+):", line)] if m]
                if fields:
                    findings.append(bad("%s: a '#' is read as a YAML comment and cuts the value short; "
                                        "quote the value" % ", ".join(fields)))
                else:
                    findings.append(bad("a '#' is read as a YAML comment on line %s; frontmatter carries "
                                        "no comments" % ", ".join(str(n) for n, _ in lines)))

    if GUARD in fm:
        written = re.search(r"^%s:[ \t]*(.*?)[ \t]*$" % GUARD, block, re.M)
        if not written or written.group(1) not in ("true", "false"):
            findings.append(bad("%s: written as %r; write the literal true or false"
                                % (GUARD, written.group(1) if written else fm[GUARD])))
    return findings


def plugin_dirs(tree):
    return sorted(p for p in (Path(tree) / "plugins").iterdir() if p.is_dir())


def skill_files(tree):
    return sorted(Path(tree).glob("plugins/*/skills/*/SKILL.md"))


def command_files(tree):
    return sorted(Path(tree).glob("plugins/*/commands/*.md"))


def _lenient_name(path, fallback):
    try:
        fm, _ = read_frontmatter(path)
        name = fm.get("name")
        return name if isinstance(name, str) and name else fallback
    except Exception:
        return fallback


# @spec PKG-CHECK-009
def name_findings(tree):
    findings = []
    seen = {}
    for plugin in plugin_dirs(tree):
        skills = {}
        for skill in sorted(plugin.glob("skills/*/SKILL.md")):
            names = {skill.parent.name, _lenient_name(skill, skill.parent.name)}
            skills[skill.parent.name] = names
            for name in names:
                seen.setdefault(name, set()).add(plugin.name)
        for command in sorted(plugin.glob("commands/*.md")):
            names = {command.stem, _lenient_name(command, command.stem)}
            for skill, skill_names in skills.items():
                shared = names & skill_names
                if shared:
                    findings.append(Finding(
                        "frontmatter", str(command.relative_to(tree)),
                        "command '%s' shares the name '%s' with skill '%s' in plugin %s; a command "
                        "file is only an alias under a name no skill uses"
                        % (command.stem, sorted(shared)[0], skill, plugin.name)))
    for name, plugins in sorted(seen.items()):
        if len(plugins) > 1:
            findings.append(Finding("frontmatter", "plugins", "skill name '%s' repeats across plugins %s"
                                    % (name, ", ".join(sorted(plugins)))))
    return findings


# -------------------------------------------------------------------- size

# @spec PKG-CHECK-010, PKG-CHECK-011
def size_findings(tree):
    tree = Path(tree)
    findings = []
    for skill in skill_files(tree):
        try:
            _, body = split_frontmatter(skill.read_bytes().replace(b"\r\n", b"\n"))
        except NoBlock:
            continue
        if len(body) >= MAX_BODY_BYTES:
            findings.append(Finding("size", str(skill.relative_to(tree)),
                                    "body is %d bytes; keep it under 50,000" % len(body)))
    for path in sorted(tree.glob("plugins/*/skills/*/**/*")):
        rel = path.relative_to(tree)
        if not path.is_file() or "evals" in rel.parts[4:]:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.split("\n"), 1):
            if len(line) > MAX_LINE:
                findings.append(Finding("size", "%s:%d" % (rel, number),
                                        "line is %d characters; keep lines to 2,000" % len(line)))
    return findings


# ---------------------------------------------------------------- versions

def version_of(tree):
    return json.loads((Path(tree) / CORE_PLUGIN_JSON).read_text()).get("version")


def _parse(version):
    m = SEMVER.match(version or "")
    return tuple(int(x) for x in m.groups()) if m else None


# @spec PKG-CHECK-014
def next_versions(version):
    major, minor, patch = _parse(version)
    return {"%d.%d.%d" % (major, minor, patch + 1), "%d.%d.0" % (major, minor + 1),
            "%d.0.0" % (major + 1)}


# @spec PKG-CHECK-014
def is_shipped(rel):
    parts = Path(rel).parts
    return len(parts) >= 3 and parts[0] == "plugins" and "evals" not in parts[2:]


# @spec PKG-CHECK-031
def host_trigger(changed):
    return any(is_shipped(p) or any(p == t or (t.endswith("/") and p.startswith(t))
                                    for t in HOST_TRIGGERS) for p in changed)


def _changelog_entries(text):
    """[(heading text, entry body)] for each `## ` heading."""
    matches = list(re.finditer(r"^## (?!#)(.*)$", text, re.M))
    return [(m.group(1).strip(), text[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)])
            for i, m in enumerate(matches)]


# @spec PKG-CHECK-012, PKG-CHECK-013, PKG-CHECK-016
def local_version_findings(tree):
    """Version checks that need only the checked tree."""
    tree = Path(tree)
    findings = []
    version = version_of(tree)

    def bad(where, reason):
        findings.append(Finding("versions", where, reason))

    versions = {}
    for plugin in plugin_dirs(tree):
        manifest = plugin / ".claude-plugin" / "plugin.json"
        if manifest.exists():
            versions[plugin.name] = json.loads(manifest.read_text()).get("version")
        cursor = plugin / ".cursor-plugin" / "plugin.json"
        if cursor.exists() and "version" in json.loads(cursor.read_text()):
            bad(str(cursor.relative_to(tree)), "carries a version; Cursor manifests carry none")
    if len(set(versions.values())) != 1 or not _parse(version):
        bad("plugins/*/.claude-plugin/plugin.json",
            "the three plugins must carry the same version X.Y.Z; found %s"
            % ", ".join("%s %s" % kv for kv in sorted(versions.items())))
    for rel in MARKETPLACES:
        try:
            entries = json.loads((tree / rel).read_text()).get("plugins", [])
        except (OSError, ValueError):
            continue  # reported by the structure checks
        for entry in entries:
            if isinstance(entry, dict) and "version" in entry:
                bad(rel, "entry %s carries a version; versions live only in each plugin.json"
                    % entry.get("name"))

    entries = _changelog_entries((tree / CHANGELOG).read_text())
    previous = None
    for heading, _ in entries:
        m = VERSION_HEADING.match(heading)
        if not m:
            bad(CHANGELOG, "heading '## %s' is not a version heading '## [X.Y.Z] — YYYY-MM-DD'" % heading)
            continue
        current = _parse(m.group(1))
        if previous is not None and current >= previous:
            bad(CHANGELOG, "heading '## %s' is out of order or repeated; versions run newest first" % heading)
        previous = current
    first = VERSION_HEADING.match(entries[0][0]) if entries else None
    if not first or first.group(1) != version:
        bad(CHANGELOG, "the first entry must be the current version %s" % version)

    doc = (tree / WORKFLOW_DOC).read_text()
    stamp, _ = split_stamp(doc)
    if stamp is None or assemble_workflow_doc(tree / CORE_SKILL, stamp) != doc:
        bad(WORKFLOW_DOC, "the workflow doc is stale: it differs from a fresh assembly of the core skill "
            "source; run packaging_checks.py --write-workflow-doc")
    return findings


# @spec PKG-CHECK-014, PKG-CHECK-015, PKG-CHECK-016
def _version_only(tree, main, rel):
    """True when a plugin.json differs from main's only in its version."""
    if not rel.endswith("/.claude-plugin/plugin.json"):
        return False
    try:
        ours = json.loads((Path(tree) / rel).read_text())
        theirs = json.loads((Path(main) / rel).read_text())
    except (OSError, ValueError):
        return False
    ours.pop("version", None)
    theirs.pop("version", None)
    return ours == theirs


def main_version_findings(tree, main, changed):
    """Version checks that compare the checked tree with main."""
    tree, main = Path(tree), Path(main)
    findings = []
    version, main_version = version_of(tree), version_of(main)

    def bad(where, reason):
        findings.append(Finding("versions", where, reason))

    if not _parse(version) or not _parse(main_version):
        return findings
    shipped = sorted(p for p in changed if is_shipped(p) and not _version_only(tree, main, p))
    if shipped:
        if version not in next_versions(main_version):
            bad(CORE_PLUGIN_JSON, "version %s: a change to shipped plugin files (%s) needs the next version "
                "after main's %s, one of %s" % (version, shipped[0], main_version,
                                                ", ".join(sorted(next_versions(main_version)))))
    elif version != main_version:
        bad(CORE_PLUGIN_JSON, "version %s: no shipped plugin file changed, so the version must equal "
            "main's %s" % (version, main_version))

    if version != main_version:
        entries = _changelog_entries((tree / CHANGELOG).read_text())
        top = entries[0][1] if entries else ""
        headings = re.findall(r"^### Migration.*$", top, re.M)
        if _parse(version)[:2] != _parse(main_version)[:2]:
            want = "### Migration (v%d.%d → v%d.%d)" % (_parse(main_version)[:2] + _parse(version)[:2])
            if headings != [want]:
                bad(CHANGELOG, "a new major.minor needs exactly one Migration heading, '%s'; found %s"
                    % (want, headings or "none"))
        elif headings:
            bad(CHANGELOG, "a patch entry holds no Migration section; found %s" % headings)

    stamp, rest = split_stamp((tree / WORKFLOW_DOC).read_text())
    main_doc = main / WORKFLOW_DOC
    main_stamp, main_rest = split_stamp(main_doc.read_text()) if main_doc.exists() else (None, None)
    if rest != main_rest:
        if stamp != version:
            bad(WORKFLOW_DOC, "workflow doc stamp %s: its content changed, so it takes the new version %s"
                % (stamp, version))
    elif stamp != main_stamp:
        bad(WORKFLOW_DOC, "workflow doc stamp %s: its content is unchanged from main, so it keeps main's "
            "stamp %s" % (stamp, main_stamp))
    return findings


def version_findings(tree, main, changed):
    return local_version_findings(tree) + main_version_findings(tree, main, changed)


# @spec PKG-CHECK-017
def tag_findings(version, tagged):
    if tagged is None:
        return [Finding("versions", "tags", "could not list the tags of the GitHub remote", error=True)]
    if not tagged:
        return [Finding("versions", "tags", "main's version %s has no v%s tag; tag main's merge commit "
                        "and publish its Release" % (version, version))]
    return []


# --------------------------------------------------------------- structure

def _slug(heading):
    text = re.sub(r"`|\*|(?<!\w)_|_(?!\w)", "", heading.strip().lower())
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def _anchors(path):
    text = re.sub(r"^```.*?^```", "", path.read_text(), flags=re.S | re.M)
    anchors, counts = set(), {}
    for heading in re.findall(r"^#{1,6} (.*?)\s*#*\s*$", text, re.M):
        slug = _slug(heading)
        n = counts.get(slug, 0)
        anchors.add(slug if n == 0 else "%s-%d" % (slug, n))
        counts[slug] = n + 1
    anchors.update(re.findall(r"<a\s+(?:id|name)=\"([^\"]+)\"", text))
    return anchors


# @spec PKG-CHECK-018, PKG-CHECK-019, PKG-CHECK-020
def structure_findings(tree):
    tree = Path(tree)
    findings = []
    for rel in LINK_CHECKED:
        source = tree / rel
        if not source.exists():
            findings.append(Finding("structure", rel, "file is missing"))
            continue
        text = re.sub(r"^```.*?^```", "", source.read_text(), flags=re.S | re.M)
        text = re.sub(r"`[^`\n]*`", "", text)
        for target in re.findall(r"\[[^\]]*\]\(<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\)", text):
            if re.match(r"^[a-z]+:", target):
                continue
            path, _, anchor = target.partition("#")
            dest = (source.parent / path).resolve() if path else source.resolve()
            if not dest.exists():
                findings.append(Finding("structure", rel, "link %s: no such file" % target))
            elif anchor and dest.suffix == ".md" and anchor not in _anchors(dest):
                findings.append(Finding("structure", rel, "link %s: no such heading #%s" % (target, anchor)))
    for rel in MARKETPLACES:
        try:
            manifest = json.loads((tree / rel).read_text())
        except (OSError, ValueError) as e:
            findings.append(Finding("structure", rel, "not valid JSON: %s" % e))
            continue
        for entry in manifest.get("plugins", []):
            source = entry.get("source", "") if isinstance(entry, dict) else ""
            normalized = source[2:] if source.startswith("./") else source
            if not (normalized.startswith("plugins/") and (tree / normalized).is_dir()):
                findings.append(Finding("structure", rel, "plugin source %s does not resolve to a directory "
                                        "under plugins/" % source))
    claude = tree / "CLAUDE.md"
    if not claude.is_symlink() or claude.resolve() != (tree / "AGENTS.md").resolve():
        findings.append(Finding("structure", "CLAUDE.md", "must be a symlink resolving to AGENTS.md"))
    return findings


# ------------------------------------------------------- workflow doc assembly

# @spec PKG-CHECK-036
def split_stamp(text):
    """(stamp version, text with the stamp line blanked) for a workflow doc."""
    m = STAMP_LINE.search(text)
    if not m:
        return None, text
    return m.group(1), text[:m.start()] + text[m.end():]


# @spec PKG-CHECK-036
def assemble_workflow_doc(skill_dir, version):
    skill_dir = Path(skill_dir)
    _, body = split_frontmatter((skill_dir / "SKILL.md").read_bytes())
    body = body.decode("utf-8").lstrip("\n")
    exception = re.search(r"^## LID-on-LID exception\n.*?\n(?=\n## )", body, re.S | re.M)
    if exception:
        body = body[:exception.start()] + body[exception.end():]
    out = HEADER.replace("@VERSION@", version) + body
    for name in re.findall(r"^- `references/([^`]+)`", body, re.M):
        if not out.endswith("\n"):
            out += "\n"
        out += "\n\n---\n\n<!-- Appended reference: %s -->\n\n" % name
        out += (skill_dir / "references" / name).read_text()
    return out


# ------------------------------------------------------------ host parts

def list_skills(tree):
    """[(plugin, skill directory, frontmatter, body)] for each skill in the tree."""
    out = []
    for skill in skill_files(tree):
        try:
            fm, body = read_frontmatter(skill)
            if not isinstance(fm, dict):
                fm, body = None, None
        except Exception:
            fm, body = None, None
        out.append((skill.parent.parent.parent.name, skill.parent.name, fm, body))
    return out


def guarded(fm):
    return bool(fm) and fm.get(GUARD) is True


def claude_projects_root():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return Path(base) / "projects"


def _run_claude(argv, cwd):
    try:
        done = subprocess.run(argv, cwd=str(cwd), stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=CLAUDE_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise HostUnavailable("claude -p did not finish within %d seconds" % CLAUDE_TIMEOUT)
    if done.returncode != 0 and not done.stdout.strip():
        raise HostUnavailable("claude -p exited %d: %s" % (done.returncode, done.stderr.strip()[-300:]))
    return done.stdout


def _events(stdout):
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    return events


def _transcript_path(projects_root, sid):
    found = sorted(Path(projects_root).glob("*/%s.jsonl" % sid))
    return found[0] if found else None


def _read_transcript(projects_root, sid):
    path = _transcript_path(projects_root, sid)
    if not path:
        return None
    entries = []
    for line in path.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except ValueError:
            pass
    return entries


def _texts(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return []


def _parse_listing(text):
    entries, name = {}, None
    for line in text.split("\n"):
        if line.startswith("- "):
            name, _, description = line[2:].partition(": ")
            name = name.strip()
            entries[name] = description
        elif name is not None and line.strip():
            entries[name] += "\n" + line
    return entries


def _remove_transcripts(projects_root, sids, cwd):
    marker = re.sub(r"[^A-Za-z0-9]", "-", Path(cwd).name)
    for sid in sids:
        path = _transcript_path(projects_root, sid)
        if not path:
            continue
        folder = path.parent
        path.unlink()
        shutil.rmtree(folder / sid, ignore_errors=True)
        if marker in folder.name or not any(folder.iterdir()):
            shutil.rmtree(folder, ignore_errors=True)


GUARD_PROMPT = ("This is a plugin loading test. Call the Skill tool once for each of these skills, one call "
                "at a time, even if a skill is not in your list: %s. After the calls, reply DONE.")
QUIET_PROMPT = "This is a plugin loading test. Do not call any tools. Reply DONE."
SLASH_PROMPT = "/%s This is a plugin loading test, not a task. Reply with only the word LOADED."


# @spec PKG-CHECK-021, PKG-CHECK-022, PKG-CHECK-023, PKG-CHECK-024, PKG-CHECK-025, PKG-CHECK-026
def claude_code_part(tree, runner=None, projects_root=None):
    tree = Path(tree)
    runner = runner or _run_claude
    projects_root = Path(projects_root or claude_projects_root())
    skills = list_skills(tree)
    commands = ["%s:%s" % (c.parent.parent.name, c.stem) for c in command_files(tree)]
    plugins = plugin_dirs(tree)
    version = version_of(tree)
    cwd = Path(tempfile.mkdtemp(prefix="lid-packaging-cc-"))
    sids = []
    findings = []

    def bad(where, reason, **kind):
        findings.append(Finding("claude-code", where, reason, **kind))

    def argv(prompt, tools, turns):
        sid = str(uuid.uuid4())
        sids.append(sid)
        cmd = ["claude", "-p", prompt]
        for plugin in plugins:
            cmd += ["--plugin-dir", str(plugin)]
        return sid, cmd + ["--setting-sources", "project", "--model", CLAUDE_MODEL, "--effort", "low",
                           "--session-id", sid, "--tools", tools, "--max-turns", str(turns),
                           "--no-chrome", "--output-format", "stream-json", "--verbose"]

    def unavailable(e):
        return Part("claude-code", [Finding("claude-code", "claude", "%s; log in to Claude Code, or run with "
                                            "--no-host to leave this part to the maintainer" % e, error=True)])

    try:
        names = ["%s:%s" % (p, s) for p, s, fm, _ in skills if guarded(fm)]
        sid, cmd = argv(GUARD_PROMPT % ", ".join(names) if names else QUIET_PROMPT, "Skill",
                        2 + 2 * len(names))
        try:
            events = _events(runner(cmd, cwd))
        except (FileNotFoundError, HostUnavailable) as e:
            return unavailable(e)
        init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
        result = next((e for e in events if e.get("type") == "result"), {})
        if init is None:
            return unavailable("Claude Code did not start a session (%s)"
                               % (result.get("result") or "no opening event"))
        if result.get("is_error"):
            bad("session", "the session ended in an error (%s); rerun, or check the Claude Code login"
                % (result.get("result") or result.get("subtype") or "no detail"), error=True)
        detail = ["Claude Code %s" % init.get("claude_code_version", "?"), init.get("model", "?")]

        loaded = init.get("plugins")
        ours = {p.name for p in plugins}
        if not isinstance(loaded, list) or any("version" not in p for p in loaded
                                               if isinstance(p, dict) and p.get("name") in ours):
            bad("opening event", "it does not list each loaded plugin with its version; Claude Code's record "
                "format may have changed", error=True)
        else:
            loaded = {p.get("name"): p.get("version") for p in loaded if isinstance(p, dict)}
            for plugin in plugins:
                if loaded.get(plugin.name) != version:
                    bad(plugin.name, "loaded at version %s, not the export's %s"
                        % (loaded.get(plugin.name), version))
        registered = init.get("slash_commands")
        if not isinstance(registered, list):
            bad("opening event", "it does not list the registered commands; Claude Code's record format may "
                "have changed", error=True)
        else:
            for name in ["%s:%s" % (p, s) for p, s, _, _ in skills] + commands:
                if registered.count(name) != 1:
                    bad(name, "registered %d times; each name is registered exactly once" % registered.count(name))

        transcript = _read_transcript(projects_root, sid)
        listing = next((e["attachment"].get("content") for e in transcript or []
                        if e.get("type") == "attachment"
                        and (e.get("attachment") or {}).get("type") == "skill_listing"), None)
        if listing is None:
            bad("transcript", "found no skill listing in Claude Code's session transcript; its format may "
                "have changed", error=True)
            listed = None
        else:
            listed = _parse_listing(listing)
            ours = tuple(p.name + ":" for p in plugins)
            others = sum(1 for n in listed if not n.startswith(ours))
            detail.append("isolated: %d other listing entr%s" % (others, "y" if others == 1 else "ies"))
        for plugin, skill, fm, _ in skills:
            name = "%s:%s" % (plugin, skill)
            if fm is None:
                bad(name, "its frontmatter does not parse, so what the host loaded cannot be compared")
                continue
            if listed is None:
                continue
            if guarded(fm):
                if name in listed:
                    bad(name, "guarded skill is listed to the model")
            elif name not in listed:
                bad(name, "not in the model's skill listing")
            elif listed[name] != fm.get("description"):
                bad(name, "listed with a description other than its SKILL.md's: %r" % listed[name][:120])

        calls, refusals = {}, {}
        for event in events:
            for block in (event.get("message") or {}).get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    calls[block.get("id")] = (block.get("input") or {}).get("skill")
                if block.get("type") == "tool_result":
                    refusals[block.get("tool_use_id")] = bool(block.get("is_error"))
        for name in names:
            ids = [i for i, called in calls.items() if called == name]
            if not ids:
                bad(name, "the model did not call this guarded skill, so its refusal is unobserved",
                    inconclusive=True)
            elif not any(refusals.get(i) for i in ids):
                bad(name, "the host did not refuse a model call to this guarded skill")

        def deliver(skill):
            plugin, name, fm, body = skill
            if fm is None:
                return None  # reported above
            sid, cmd = argv(SLASH_PROMPT % ("%s:%s" % (plugin, name)), "", 1)
            try:
                runner(cmd, cwd)
            except (FileNotFoundError, HostUnavailable) as e:
                return Finding("claude-code", "%s:%s" % (plugin, name), str(e), error=True)
            entries = _read_transcript(projects_root, sid)
            if entries is None:
                return Finding("claude-code", "%s:%s" % (plugin, name), "no session transcript was found",
                               error=True)
            delivered = [t for e in entries if e.get("type") == "user" and e.get("isMeta")
                         for t in _texts(e)]
            if not any(body.strip() in t for t in delivered):
                return Finding("claude-code", "%s:%s" % (plugin, name),
                               "invoking it by its slash name did not deliver its SKILL.md body whole")
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            findings.extend(f for f in pool.map(deliver, skills) if f)
        return Part("claude-code", findings, detail=", ".join(detail))
    finally:
        _remove_transcripts(projects_root, sids, cwd)
        shutil.rmtree(cwd, ignore_errors=True)


def _runner_module():
    path = HERE.parent / "alt-model-evals" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def opencode_version():
    return _runner_module().HARNESS_VERSION


def _run_opencode(tree):
    """opencode's own report of its loaded skills, from the alternate-model runner's container."""
    runner = _runner_module()
    try:
        runner.check_docker()
        image = runner.ensure_image()
    except runner.UsageError as e:
        raise HostUnavailable(str(e).split(". ")[0])
    scratch = runner.make_scratch()
    try:
        runner.stage_plugins(Path(tree), scratch / "plugins")
        (scratch / "project").mkdir()
        (scratch / "state").mkdir()
        (scratch / "opencode.json").write_text(
            json.dumps(runner.opencode_config("/work/plugins", "none", "default")))
        cmd = runner.docker_run_argv("lid-packaging-" + scratch.name, image, scratch, "none", "x")
        cmd = cmd[:cmd.index("opencode")] + ["sh", "-c", "opencode debug skill --pure > /work/state/skills.json"]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT)
        if done.returncode != 0:
            raise HostUnavailable("opencode debug skill exited %d: %s"
                                  % (done.returncode, done.stderr.strip()[-300:]))
        return (scratch / "state" / "skills.json").read_text()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# @spec PKG-CHECK-027, PKG-CHECK-028, PKG-CHECK-029
def opencode_part(tree, runner=None):
    runner = runner or _run_opencode
    try:
        detail = "opencode %s" % opencode_version()
    except Exception as e:
        return Part("opencode", [Finding("opencode", "tools/alt-model-evals/run_eval.py",
                                         "could not load the alternate-model runner: %s" % e, error=True)])
    try:
        report = json.loads(runner(tree))
        if not isinstance(report, list) or not all(isinstance(e, dict) for e in report):
            raise ValueError("not a list of skills")
    except HostUnavailable as e:
        return Part("opencode", [Finding("opencode", "opencode", "%s; start a container runtime, or run with "
                                         "--no-host to leave this part to the maintainer" % e, error=True)],
                    detail=detail)
    except ValueError:
        return Part("opencode", [Finding("opencode", "opencode", "could not read opencode's skill report",
                                         error=True)], detail=detail)
    loaded = {e.get("name"): e for e in report if e.get("location") != "<built-in>"}
    findings = []
    honored = True
    for plugin, skill, fm, body in list_skills(tree):
        if fm is None:
            findings.append(Finding("opencode", skill, "its frontmatter does not parse, so what opencode "
                                    "loaded cannot be compared"))
            continue
        name = fm.get("name") or skill
        entry = loaded.get(name)
        if guarded(fm):
            if entry and entry.get("autoinvoke") is not False and entry.get(GUARD) is not True:
                honored = False
            if not entry:
                continue
        if not entry:
            findings.append(Finding("opencode", name, "not among the skills opencode loaded"))
            continue
        if entry.get("description") != fm.get("description"):
            findings.append(Finding("opencode", name, "loaded with a description other than its SKILL.md's"))
        if entry.get("content") != body:
            findings.append(Finding("opencode", name, "opencode serves content other than its SKILL.md body"))
    detail += "; guard: %s; command aliases: not loaded" % ("honored" if honored else "not honored")
    return Part("opencode", findings, detail=detail)


# ----------------------------------------------------------- the record

# @spec PKG-CHECK-033
def result_line(facts, parts):
    def short(value):
        return (value or "?")[:12]

    pieces = ["packaging-checks: commit %s (tree %s) vs main %s"
              % (short(facts.get("commit")), short(facts.get("tree")), short(facts.get("main")))]
    for part in parts:
        text = "%s: %s" % (part.name, part.state)
        if part.state == "fail":
            groups = sorted({f.group for f in part.findings if f.kind() == "fail"})
            if part.name == "static":
                text += " (%s)" % ", ".join(groups)
        if part.detail:
            text += " (%s)" % part.detail
        pieces.append(text)
    return " | ".join(pieces)


# @spec PKG-CHECK-034
def report(parts):
    for part in parts:
        for f in part.findings:
            print("%-11s %-12s %s: %s" % (part.name, f.kind(), f.where, f.reason))


# @spec PKG-CHECK-002, PKG-CHECK-038
def static_part(tree, main_tree, facts):
    tree = Path(tree)
    findings = []
    for path in skill_files(tree):
        findings += frontmatter_findings(path, str(path.relative_to(tree)), is_skill=True)
    for path in command_files(tree):
        findings += frontmatter_findings(path, str(path.relative_to(tree)), is_skill=False)
    findings += name_findings(tree) + size_findings(tree) + structure_findings(tree)
    findings += local_version_findings(tree)
    if facts.get("main") is None:
        findings.append(Finding("versions", "main", "could not fetch main from %s: %s"
                                % (facts.get("remote"), facts.get("fetch_error")), error=True))
    elif not facts.get("contains_main"):
        findings.append(Finding("versions", short_id(facts.get("commit")),
                                "the checked commit does not contain main's tip %s; bring the branch up to "
                                "date with main" % short_id(facts.get("main"))))
    else:
        findings += main_version_findings(tree, main_tree, facts.get("changed", []))
        findings += tag_findings(version_of(main_tree), facts.get("main_tagged"))
    return Part("static", findings)


def short_id(value):
    return (value or "?")[:12]


# @spec PKG-CHECK-031, PKG-CHECK-032, PKG-CHECK-038
def run_inner(facts):
    tree = Path(facts["tree_dir"])
    main_tree = Path(facts["main_dir"]) if facts.get("main_dir") else None
    static = static_part(tree, main_tree, facts)
    if facts.get("main") is not None and not host_trigger(facts.get("changed", [])):
        hosts = [Part("claude-code", [], state="skipped"), Part("opencode", [], state="skipped")]
    elif facts.get("no_host"):
        hosts = [Part("claude-code", [], state="owed"), Part("opencode", [], state="owed")]
    else:
        hosts = [claude_code_part(tree), opencode_part(tree)]
    parts = [static] + hosts
    report(parts)
    print(result_line(facts, parts))
    return exit_code({p.name: p.state for p in parts})


# --------------------------------------------------------- repository plumbing

class GitError(Exception):
    pass


def run(cmd, cwd, binary=False):
    done = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=not binary)
    if done.returncode != 0:
        err = done.stderr if not binary else done.stderr.decode("utf-8", "replace")
        raise GitError("%s: %s" % (" ".join(cmd[:3]), err.strip()[-300:]))
    return done.stdout if binary else done.stdout.strip()


def remote_url():
    return os.environ.get("PACKAGING_CHECKS_REMOTE") or DEFAULT_REMOTE


def single_commit(output, rev):
    ids = output.split()
    if len(ids) != 1:
        raise GitError("revision %s names %d commits; pass --rev with exactly one" % (rev, len(ids)))
    return ids[0]


# @spec PKG-CHECK-001
def resolve_commit(repo, rev=None):
    if (Path(repo) / ".jj").is_dir() and shutil.which("jj"):
        if rev is None:
            empty = run(["jj", "log", "-r", "@", "--no-graph", "-T", 'if(empty, "1", "0")'], repo)
            rev = "@-" if empty == "1" else "@"
        return single_commit(run(["jj", "log", "-r", rev, "--no-graph", "-T", 'commit_id ++ "\\n"'], repo), rev)
    return run(["git", "rev-parse", "--verify", "%s^{commit}" % (rev or "HEAD")], repo)


# @spec PKG-CHECK-001
def export(repo, commit, dest):
    data = run(["git", "archive", "--format=tar", commit], repo, binary=True)
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(str(dest))


# @spec PKG-CHECK-002
def fetch_main(repo):
    run(["git", "fetch", "--quiet", "--no-tags", remote_url(), "main"], repo)
    return run(["git", "rev-parse", "FETCH_HEAD"], repo)


# @spec PKG-CHECK-017
def tag_exists(tag):
    try:
        return bool(run(["git", "ls-remote", "--tags", remote_url(), "refs/tags/" + tag], Path.cwd()))
    except GitError:
        return None


def gather(repo, commit, work, no_host):
    tree = work / "tree"
    export(repo, commit, tree)
    facts = {"commit": commit, "tree": run(["git", "rev-parse", commit + "^{tree}"], repo),
             "tree_dir": str(tree), "no_host": no_host, "remote": remote_url(), "main": None}
    try:
        main = fetch_main(repo)
    except GitError as e:
        facts["fetch_error"] = str(e)
        return facts
    facts["main"] = main
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", main, commit], cwd=str(repo))
    facts["contains_main"] = ancestor.returncode == 0
    export(repo, main, work / "main")
    facts["main_dir"] = str(work / "main")
    facts["changed"] = run(["git", "diff", "--name-only", "--no-renames", main, commit], repo).splitlines()
    facts["main_tagged"] = tag_exists("v%s" % version_of(work / "main"))
    return facts


# @spec PKG-CHECK-036
def write_workflow_doc(repo):
    version = version_of(repo)
    fresh = assemble_workflow_doc(Path(repo) / CORE_SKILL, version)
    try:
        fetch_main(repo)
        main_doc = run(["git", "show", "FETCH_HEAD:" + WORKFLOW_DOC], repo, binary=True).decode("utf-8")
    except GitError as e:
        print("cannot regenerate the workflow doc without main's copy to compare with: %s" % e)
        return 2
    main_stamp, main_rest = split_stamp(main_doc)
    if split_stamp(fresh)[1] == main_rest:
        fresh = assemble_workflow_doc(Path(repo) / CORE_SKILL, main_stamp)
    (Path(repo) / WORKFLOW_DOC).write_text(fresh)
    print("wrote %s, stamped %s" % (WORKFLOW_DOC, split_stamp(fresh)[0]))
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Check what LID's plugins ship before a merge to main.")
    parser.add_argument("--rev", help="the commit to check (default: the commit holding the current change)")
    parser.add_argument("--no-host", action="store_true",
                        help="skip the host-loading parts; they report owed, for the maintainer to run")
    parser.add_argument("--write-workflow-doc", action="store_true",
                        help="regenerate the shipped workflow doc in the working copy")
    parser.add_argument("--inner", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.inner:
        return run_inner(json.loads(Path(args.inner).read_text()))
    try:
        repo = Path(run(["git", "rev-parse", "--show-toplevel"], Path.cwd()))
        if args.write_workflow_doc:
            return write_workflow_doc(repo)
        commit = resolve_commit(repo, args.rev)
        work = Path(tempfile.mkdtemp(prefix="lid-packaging-"))
        try:
            facts = gather(repo, commit, work, args.no_host)
            script = work / "tree" / "tools" / "packaging-checks" / "packaging_checks.py"
            if not script.exists():
                print("the checked commit %s has no tools/packaging-checks/packaging_checks.py" % commit[:12])
                return 2
            (work / "facts.json").write_text(json.dumps(facts))
            sys.stdout.flush()
            return subprocess.run([sys.executable, str(script), "--inner", str(work / "facts.json")]).returncode
        finally:
            shutil.rmtree(work, ignore_errors=True)
    except GitError as e:
        print("packaging-checks: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
