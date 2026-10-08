#!/usr/bin/env python3
"""The repository suite.

Some facts this repository states in more than one place are
pinned here where a script can compare them: the name and
version, the package contents, the claim and the transcript
behind it, the demo images, the install blocks, and the
evidence hashes. It also rebuilds the synthetic repository
and checks that the recorded commands still print what the
transcript shows.

Runs offline with the standard library, `git`, `wc` and `sh`:

    python3 tests/test_integrations.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "plan-commits"
PACKAGE = ROOT / "skills" / NAME
SKILL = PACKAGE / "SKILL.md"
INTERFACE = PACKAGE / "agents" / "openai.yaml"
PACKAGE_FILES = {"SKILL.md", "agents/openai.yaml"}
README = ROOT / "README.md"
TRANSCRIPT = ROOT / "evidence" / "transcripts" / "count-session.txt"
MANIFEST = ROOT / "evidence" / "demo-manifest.json"
EXAMPLE = ROOT / "examples" / "worked-example.md"
FIXTURE = ROOT / "examples" / "fixture"
RECORDER = ROOT / "scripts" / "record_session.py"
RENDERER = ROOT / "scripts" / "render_invocation.py"
INVOCATION_TRANSFORMS = [
    "replace-plugin-root",
    "replace-capture-root",
    "replace-scratch-root",
    "replace-home",
    "replace-hostname",
]
CLAIM = "Line counts come from git diff --numstat and wc -l."
COMMANDS = [
    "git status --porcelain=v1 --untracked-files=all",
    "git diff --numstat",
    "wc -l tests/test_slugify.py",
]
REPOSITORY = "https://github.com/trycopilotai/" + NAME
# Built from parts so that this file does not itself hold the
# home-directory prefixes it looks for.
ABSOLUTE_PATH = re.compile("(/" + "Users/|/" + "home/|/" + "private/|/" + "var/folders/|/tmp/)")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    ).stdout


def load(path: Path, name: str):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest(product: str) -> dict:
    return json.loads(read(ROOT / product / "plugin.json"))


def package_files() -> set:
    found = set()
    for directory, _names, files in os.walk(str(PACKAGE)):
        for name in files:
            path = Path(directory) / name
            found.add(path.relative_to(PACKAGE).as_posix())
    return found


def fixture_files() -> list:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in FIXTURE.rglob("*")
        if path.is_file()
    )


def frontmatter(text: str) -> dict:
    """The `key: value` pairs between the two `---` lines."""
    lines = text.splitlines()
    if lines[0] != "---":
        raise AssertionError("SKILL.md does not open with frontmatter")
    end = lines.index("---", 1)
    fields: dict = {}
    key = None
    for line in lines[1:end]:
        match = re.match(r"^([a-z_-]+):\s*(.*)$", line)
        if match:
            key = match.group(1)
            fields[key] = match.group(2).strip()
            continue
        if key is None or not line.startswith(" "):
            raise AssertionError("unexpected frontmatter line: " + line)
        fields[key] = (fields[key] + " " + line.strip()).strip()
    for name, value in fields.items():
        if value.startswith(">-"):
            fields[name] = value[2:].strip()
    return fields


def interface_yaml(text: str) -> dict:
    """The quoted scalars under `interface:` in agents/openai.yaml."""
    lines = text.splitlines()
    if lines[0] != "interface:":
        raise AssertionError("openai.yaml does not start with interface:")
    fields: dict = {}
    key = None
    for line in lines[1:]:
        match = re.match(r"^  ([a-z_]+):\s*(.*)$", line)
        if match:
            key = match.group(1)
            fields[key] = match.group(2).strip()
            continue
        fields[key] = (fields[key] + " " + line.strip()).strip()
    for name, value in fields.items():
        if not (value.startswith('"') and value.endswith('"')):
            raise AssertionError(name + " is not a double-quoted scalar")
        fields[name] = value[1:-1]
    return fields


def install_blocks() -> list:
    return re.findall(r"```sh\nset -eu\n(.*?)```", read(README), flags=re.S)


def spacing_free(text: str) -> list:
    """Each line with runs of spaces and tabs collapsed to one space."""
    return [" ".join(line.split()) for line in text.splitlines()]


class LayoutTest(unittest.TestCase):
    def test_skill_is_a_symlink_into_the_canonical_package(self) -> None:
        link = ROOT / "skill"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(str(link)), "skills/" + NAME)
        self.assertFalse(PACKAGE.is_symlink())

    def test_package_is_the_two_files_the_readme_names(self) -> None:
        self.assertEqual(package_files(), PACKAGE_FILES)

    def test_package_holds_no_program(self) -> None:
        for relative in sorted(package_files()):
            path = PACKAGE / relative
            self.assertFalse(path.is_symlink(), relative)
            self.assertIn(path.suffix, {".md", ".yaml"}, relative)
            self.assertFalse(os.access(str(path), os.X_OK), relative)
            self.assertFalse(path.read_bytes().startswith(b"#!"), relative)

    def test_history_has_no_co_author_trailer(self) -> None:
        messages = git("log", "--all", "--format=%B")
        self.assertNotIn("co-authored-by", messages.lower())


class SkillTest(unittest.TestCase):
    def test_frontmatter_is_name_and_description_only(self) -> None:
        fields = frontmatter(read(SKILL))
        self.assertEqual(sorted(fields), ["description", "name"])
        self.assertEqual(fields["name"], NAME)
        self.assertRegex(NAME, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(NAME), 64)
        self.assertTrue(fields["description"])
        self.assertLessEqual(len(fields["description"]), 1024)

    def test_skill_stays_under_five_hundred_lines(self) -> None:
        self.assertLess(len(read(SKILL).splitlines()), 500)

    def test_skill_names_the_counting_commands_and_the_stop(self) -> None:
        text = " ".join(read(SKILL).split())
        for command in COMMANDS[:2]:
            self.assertIn("`" + command + "`", text)
        self.assertIn("`wc -l <file>`", text)
        self.assertIn("Do not run `git add`, `git commit`, `git push`", text)
        self.assertIn("It does not stage, commit or push.", text)


class ManifestTest(unittest.TestCase):
    def test_both_manifests_agree(self) -> None:
        claude = manifest(".claude-plugin")
        codex = manifest(".codex-plugin")
        for field in (
            "name",
            "version",
            "description",
            "license",
            "homepage",
            "repository",
            "keywords",
            "skills",
        ):
            self.assertEqual(claude[field], codex[field], field)
        self.assertEqual(claude["name"], NAME)
        self.assertEqual(claude["skills"], "./skills/")
        self.assertEqual(claude["repository"], REPOSITORY)
        self.assertEqual(claude["license"], "MIT")
        self.assertRegex(claude["version"], r"^\d+\.\d+\.\d+$")

    def test_a_release_tag_on_head_is_the_manifest_version(self) -> None:
        tags = git("tag", "--points-at", "HEAD").split()
        releases = [tag for tag in tags if tag.startswith("v")]
        if not releases:
            self.skipTest("HEAD carries no release tag")
        self.assertEqual(releases, ["v" + manifest(".claude-plugin")["version"]])

    def test_codex_interface_matches_the_agent_file(self) -> None:
        interface = manifest(".codex-plugin")["interface"]
        for field in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "websiteURL",
        ):
            self.assertTrue(interface.get(field), field)
        self.assertEqual(interface["longDescription"], manifest(".codex-plugin")["description"])
        prompts = interface["defaultPrompt"]
        self.assertEqual(len(prompts), 1)
        self.assertIn("$" + NAME, prompts[0])
        agent = interface_yaml(read(INTERFACE))
        self.assertEqual(agent["default_prompt"], prompts[0])
        self.assertEqual(agent["display_name"], interface["displayName"])
        self.assertEqual(agent["short_description"], interface["shortDescription"])


class ReadmeTest(unittest.TestCase):
    def test_claim_is_on_its_own_line(self) -> None:
        self.assertIn(CLAIM, read(README).splitlines())
        self.assertLessEqual(len(CLAIM), 60)

    def test_transcript_shows_the_commands_behind_the_claim(self) -> None:
        lines = read(TRANSCRIPT).splitlines()
        self.assertIn("$ git diff --numstat", lines)
        self.assertIn("$ wc -l tests/test_slugify.py", lines)
        statuses = [line for line in lines if line.startswith("exit status: ")]
        self.assertEqual(statuses, ["exit status: 0"] * len(COMMANDS))

    def test_each_install_block_pins_the_manifest_version(self) -> None:
        version = manifest(".claude-plugin")["version"]
        blocks = install_blocks()
        self.assertEqual(len(blocks), 2)
        roots = []
        for block in blocks:
            self.assertEqual(
                re.findall(r"^release=(\S+)$", block, flags=re.M),
                ["v" + version],
            )
            self.assertIn(REPOSITORY + " \\\n", block)
            self.assertIn('--branch "$release"', block)
            target = re.findall(r'^install_target="\$HOME/(\S+)"$', block, flags=re.M)
            self.assertEqual(len(target), 1)
            roots.append(target[0])
        self.assertEqual(
            sorted(roots),
            [".agents/skills/" + NAME, ".claude/skills/" + NAME],
        )

    def test_relative_links_resolve(self) -> None:
        for document in (README, EXAMPLE):
            targets = re.findall(r"\]\(([^)#]+)\)", read(document))
            self.assertTrue(targets)
            for target in targets:
                if target.startswith("http"):
                    continue
                self.assertTrue((document.parent / target).exists(), target)

    def test_readme_says_what_was_not_measured(self) -> None:
        text = " ".join(read(README).split())
        self.assertIn("Not measured, stated up front.", text)
        self.assertIn("No agent invoked the skill for the demo below", text)
        self.assertIn("has not been measured", text)
        self.assertIn("Neither install block below was run", text)

    def test_demo_is_offered_with_a_reduced_motion_poster(self) -> None:
        text = read(README)
        picture = re.search(r"<picture>(.*?)</picture>", text, flags=re.S)
        self.assertIsNotNone(picture)
        body = picture.group(1)
        self.assertIn('media="(prefers-reduced-motion: reduce)"', body)
        self.assertIn('srcset="assets/poster.svg"', body)
        self.assertIn('src="assets/demo.svg"', body)


class EvidenceTest(unittest.TestCase):
    def test_manifest_hashes_match_the_files(self) -> None:
        record = json.loads(read(MANIFEST))
        for key, path in (("skill", SKILL), ("interface", INTERFACE), ("worked_example", EXAMPLE)):
            self.assertEqual(
                record[key],
                {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)},
                key,
            )
        self.assertEqual(
            record["fixture"],
            [{"path": path, "sha256": sha256(ROOT / path)} for path in fixture_files()],
        )
        self.assertEqual(
            record["programs"],
            [{"path": "scripts/record_session.py", "sha256": sha256(RECORDER)}],
        )
        self.assertEqual(record["output"]["path"], TRANSCRIPT.relative_to(ROOT).as_posix())
        self.assertEqual(record["output"]["sha256"], sha256(TRANSCRIPT))
        self.assertIs(record["output"]["edited"], False)
        self.assertEqual(record["output"]["transforms"], [])
        self.assertIs(record["agent"]["invoked_the_skill"], False)

    def test_manifest_commands_are_the_ones_in_the_transcript(self) -> None:
        record = json.loads(read(MANIFEST))
        commands = [
            line[2:]
            for line in read(TRANSCRIPT).splitlines()
            if line.startswith("$ ") and not line.startswith("$ echo")
        ]
        self.assertEqual(record["invocation"]["commands"], commands)
        self.assertEqual(commands, COMMANDS)

    def test_transcript_holds_no_absolute_path(self) -> None:
        self.assertIsNone(ABSOLUTE_PATH.search(read(TRANSCRIPT)))

    def test_a_fresh_run_prints_what_the_transcript_shows(self) -> None:
        """Rebuild the fixture and rerun the commands; compare up to spacing.

        Spacing is ignored because BSD and GNU `wc` pad the count
        differently.
        """
        recorder = load(RECORDER, "record_session")
        fresh, failed = recorder.capture(COMMANDS)
        self.assertFalse(failed, fresh)
        self.assertEqual(spacing_free(fresh), spacing_free(read(TRANSCRIPT)))


class InvocationEvidenceTest(unittest.TestCase):
    def invocations(self) -> list:
        return json.loads(read(MANIFEST))["invocations"]

    def published(self) -> list:
        return [entry for entry in self.invocations() if entry["published"]]

    def test_one_published_invocation_per_declared_client(self) -> None:
        entries = self.published()
        self.assertEqual(
            [(e["product"], e["invocation"]) for e in entries],
            [("Claude Code", "/" + NAME), ("Codex", "$" + NAME)],
        )
        for entry in entries:
            self.assertIs(entry["invoked_the_skill"], True)
            self.assertTrue(entry["version"] and entry["model"] and entry["outcome"])
            self.assertRegex(entry["raw_output_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(entry["renderer"], RENDERER.relative_to(ROOT).as_posix())
            names = [t["name"] for t in entry["transforms"]]
            if entry["product"] == "Codex":
                self.assertEqual(names[0], "replace-isolation-root")
                names = names[1:]
            self.assertEqual(names, INVOCATION_TRANSFORMS)
            self.assertIn(entry["invocation"], entry["prompt"])
            self.assertIn("Stay inside this directory.", entry["prompt"])

    def test_unpublished_runs_keep_a_hash_and_an_outcome(self) -> None:
        hidden = [entry for entry in self.invocations() if not entry["published"]]
        self.assertEqual(len(hidden), 1)
        for entry in hidden:
            self.assertIs(entry["published"], False)
            self.assertRegex(entry["raw_output_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(entry["outcome"])
            self.assertNotIn("transcript", entry)

    def test_transcript_set_and_hashes_match_the_manifest(self) -> None:
        entries = self.published()
        named = sorted(e["transcript"]["path"] for e in entries)
        on_disk = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "evidence" / "transcripts").glob("*-invocation.txt")
        )
        self.assertEqual(named, on_disk)
        for entry in entries:
            path = ROOT / entry["transcript"]["path"]
            self.assertEqual(entry["transcript"]["sha256"], sha256(path))
            self.assertIn(entry["date"], path.name)

    def test_transcripts_show_the_skill_being_loaded_and_the_stop(self) -> None:
        by_product = {e["product"]: read(ROOT / e["transcript"]["path"]) for e in self.published()}
        self.assertIn('1. Skill {"skill": "plan-commits:plan-commits"}', by_product["Claude Code"])
        self.assertIn(".agents/skills/plan-commits/SKILL.md", by_product["Codex"])
        for text in by_product.values():
            final = text.split("## final message", 1)[1]
            self.assertIn("Status: awaiting operator approval.", final)
            calls = text.split("## tool calls", 1)[1].split("## final message", 1)[0]
            for command in ("git add", "git commit", "git push"):
                self.assertNotIn(command, calls)

    def test_transcripts_carry_only_replaced_paths(self) -> None:
        for entry in self.published():
            text = read(ROOT / entry["transcript"]["path"])
            self.assertIn(entry["prompt"].rstrip("\n"), text)
            self.assertIsNone(ABSOLUTE_PATH.search(text))
            users = "Use" + "rs"
            for leak in ("-%s-" % users, "claude-5" + "01"):
                self.assertNotIn(leak, text)

    def test_readme_links_both_transcripts_and_names_the_transforms(self) -> None:
        section = read(README).split("### Agent invocations", 1)[1].split("\n## ", 1)[0]
        for entry in self.published():
            self.assertIn("](%s)" % entry["transcript"]["path"], section)
        for name in ["replace-isolation-root"] + INVOCATION_TRANSFORMS:
            self.assertIn("`%s`" % name, section)
        self.assertIn("not a benchmark", section)
        self.assertIn("`...[N more characters]`", section)

    def test_rendering_rule_matches_the_renderer(self) -> None:
        renderer = load(RENDERER, "render_invocation")
        for entry in self.published():
            self.assertIn("longer than %d characters" % renderer.LIMIT, entry["rendering"])


class RendererTest(unittest.TestCase):
    def render(self, client: str, events: list, *extra: str) -> str:
        with tempfile.TemporaryDirectory() as raw:
            prompt = Path(raw) / "prompt.txt"
            prompt.write_text("Use /plan-commits here.\n", encoding="utf-8")
            stream = Path(raw) / "raw.jsonl"
            stream.write_text(
                "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(RENDERER), "--client", client, "--prompt", str(prompt),
                 "--home", "/h/me", *extra, str(stream)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=True,
            )
        return result.stdout

    def claude_events(self, *paths: str) -> list:
        uses = [
            {"type": "tool_use", "id": "t%d" % i, "name": "Read", "input": {"file_path": path}}
            for i, path in enumerate(paths)
        ]
        results = [
            {"type": "tool_result", "tool_use_id": "t%d" % i, "is_error": i == 1}
            for i in range(len(paths))
        ]
        return [
            {"type": "system", "subtype": "init", "model": "m1", "claude_code_version": "9.9"},
            {"type": "assistant", "message": {"content": uses}},
            {"type": "user", "message": {"content": results}},
            {"type": "result", "result": "Plan shown on box.local."},
        ]

    def test_claude_code_paths_are_replaced_as_whole_prefixes(self) -> None:
        text = self.render(
            "claude-code",
            self.claude_events(
                "/h/me/fix/wordcount.py",
                "/h/me/fix2/x",
                "/h/me/plug/skills/s/SKILL.md",
                "/private/tmp/claude-1000/-h-me-slug/tasks/a.out",
                "/h/me/other",
            ),
            "--root", "/h/me/fix", "--plugin-root", "/h/me/plug",
            "--hostname", "box.local", "--hostname", "box",
        )
        self.assertIn("client: Claude Code 9.9\nmodel: m1\n", text)
        self.assertIn("## prompt\n\nUse /plan-commits here.\n", text)
        self.assertIn('1. Read {"file_path": "/work/wordcount.py"}\n  status: ok', text)
        self.assertIn('2. Read {"file_path": "~/fix2/x"}\n  status: error', text)
        self.assertIn('"/plugin/skills/s/SKILL.md"', text)
        self.assertIn('"/scratch/tasks/a.out"', text)
        self.assertIn('"~/other"', text)
        self.assertTrue(text.endswith("## final message\n\nPlan shown on host.\n"))

    def test_isolation_root_is_replaced_first_in_both_forms(self) -> None:
        text = self.render(
            "claude-code",
            self.claude_events(
                "/private/q/iso1/fix/a.py",
                "/q/iso1/plug/SKILL.md",
                "/q/iso1/origin.git",
                "/q/iso10/x",
            ),
            "--isolation-root", "/private/q/iso1",
            "--root", "/private/q/iso1/fix", "--plugin-root", "/private/q/iso1/plug",
        )
        self.assertIn('"/work/a.py"', text)
        self.assertIn('"/plugin/SKILL.md"', text)
        self.assertIn('"/iso/origin.git"', text)
        self.assertIn('"/q/iso10/x"', text)

    def test_codex_commands_keep_exit_status_and_are_cut_consistently(self) -> None:
        long = "x" * 400
        text = self.render(
            "codex",
            [
                {"type": "item.completed", "item": {"type": "command_execution",
                 "command": "cat " + long, "status": "completed", "exit_code": 0}},
                {"type": "item.completed", "item": {"type": "agent_message", "text": "Done."}},
            ],
            "--root", "/h/me/fix",
        )
        self.assertIn("...[104 more characters]", text)
        self.assertIn("  status: completed, exit 0", text)
        self.assertTrue(text.endswith("## final message\n\nDone.\n"))


class DemoTest(unittest.TestCase):
    def test_images_agree_with_the_transcript(self) -> None:
        verifier = load(ROOT / "scripts" / "verify_demo.py", "verify_demo")
        generator = verifier.load_generator()
        self.assertEqual(verifier.problems_in(generator, read(TRANSCRIPT)), [])


class SocialPreviewTest(unittest.TestCase):
    def test_preview_is_the_size_github_expects(self) -> None:
        header = (ROOT / "assets" / "social-preview.png").read_bytes()[:24]
        self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", header[16:24]), (1280, 640))

    def test_stamp_binds_the_source_and_the_render(self) -> None:
        recorded = {}
        for line in read(ROOT / "assets" / "social-preview.sha256").splitlines():
            value, name = line.split()
            recorded[name] = value
        for name in ("social-preview.html", "social-preview.png"):
            self.assertEqual(recorded[name], sha256(ROOT / "assets" / name), name)

    def test_preview_source_carries_the_claim(self) -> None:
        text = " ".join(read(ROOT / "assets" / "social-preview.html").split())
        self.assertIn(CLAIM, text)


class SupportFilesTest(unittest.TestCase):
    def test_license_is_mit(self) -> None:
        self.assertTrue(read(ROOT / "LICENSE").startswith("MIT License\n"))

    def test_security_names_this_repository_for_reports(self) -> None:
        self.assertIn(
            REPOSITORY + "/security/advisories/new",
            read(ROOT / "SECURITY.md"),
        )

    def test_contributing_names_the_check_command(self) -> None:
        self.assertIn("make check", read(ROOT / "CONTRIBUTING.md"))


if __name__ == "__main__":
    unittest.main()
