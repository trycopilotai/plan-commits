#!/usr/bin/env python3
"""Check the worked example against the transcript and the fixture.

The worked example in examples/worked-example.md is a commit
plan written by reading SKILL.md, without invoking the skill. This suite checks the parts
of it that can be derived from other files: the line counts
against evidence/transcripts/count-session.txt, the file
coverage, the labels, the Regen command against the fixture,
the approval section against SKILL.md, and that the mechanical
entries come last. It does not check the commit subjects, the
summaries, the grouping, or the order beyond that.

Runs offline with the standard library:

    python3 tests/test_worked_example.py
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "worked-example.md"
FIXTURE = ROOT / "examples" / "fixture"
TRANSCRIPT = ROOT / "evidence" / "transcripts" / "count-session.txt"
SKILL = ROOT / "skills" / "plan-commits" / "SKILL.md"

ENTRY = re.compile(r"^(\d+)\. \[(mechanical|semantic)\] (\S.*)$")
FILE = re.compile(r"^   - (\S+)$")
COUNTS = re.compile(r"^     - SLOCS added/updated/deleted: (\d+)/(\d+)/(\d+)$")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """The body of a `## ` section, up to the next one."""
    start = text.index("\n## " + heading + "\n") + len(heading) + 5
    end = text.find("\n## ", start)
    if end == -1:
        return text[start:]
    return text[start:end]


def fenced(text: str) -> list:
    """The lines of the first ```text block in ``text``."""
    match = re.search(r"```text\n(.*?)```", text, flags=re.S)
    if match is None:
        raise AssertionError("no text block")
    return match.group(1).splitlines()


def outputs() -> dict:
    """Each recorded command mapped to the lines it printed."""
    found: dict = {}
    command = None
    for line in read(TRANSCRIPT).splitlines():
        if line.startswith("$ echo"):
            command = None
            continue
        if line.startswith("$ "):
            command = line[2:]
            found[command] = []
            continue
        if command is not None:
            found[command].append(line)
    return found


def recorded_counts() -> dict:
    """Path to (added, deleted), from numstat and, for new files, wc -l."""
    counts: dict = {}
    recorded = outputs()
    for line in recorded["git diff --numstat"]:
        added, deleted, path = line.split("\t")
        counts[path] = (int(added), int(deleted))
    for command, lines in recorded.items():
        if command.startswith("wc -l "):
            for line in lines:
                total, path = line.split()
                counts[path] = (int(total), 0)
    return counts


def plan_lines() -> list:
    return fenced(section(read(EXAMPLE), "The plan"))


def entries() -> list:
    """Each entry as a dict of its number, label, subject, lines and files."""
    found = []
    current = None
    path = None
    for line in plan_lines():
        if line == "Approval":
            break
        match = ENTRY.match(line)
        if match:
            current = {
                "number": int(match.group(1)),
                "label": match.group(2),
                "subject": match.group(3),
                "lines": [],
                "files": {},
            }
            found.append(current)
            continue
        if current is None:
            continue
        current["lines"].append(line)
        match = FILE.match(line)
        if match:
            path = match.group(1)
            current["files"][path] = None
            continue
        match = COUNTS.match(line)
        if match:
            current["files"][path] = tuple(int(value) for value in match.groups())
    return found


def approval(lines: list) -> list:
    return lines[lines.index("Approval") :]


class WorkedExampleTest(unittest.TestCase):
    def test_counts_equal_the_recorded_counts(self) -> None:
        """Each file's counts are its numstat or wc -l counts, updated 0."""
        planned = {}
        for entry in entries():
            for path, counts in entry["files"].items():
                self.assertIsNotNone(counts, path)
                planned[path] = counts
        expected = {
            path: (added, 0, deleted)
            for path, (added, deleted) in recorded_counts().items()
        }
        self.assertEqual(planned, expected)

    def test_every_changed_file_is_in_exactly_one_entry(self) -> None:
        """The status lists the same files the plan does, each once."""
        status = [line[3:] for line in outputs()[
            "git status --porcelain=v1 --untracked-files=all"
        ]]
        planned = [path for entry in entries() for path in entry["files"]]
        self.assertEqual(len(planned), len(set(planned)))
        self.assertEqual(sorted(planned), sorted(status))

    def test_entries_are_numbered_and_labelled(self) -> None:
        """Entries count up from 1; each has a matching Label line."""
        found = entries()
        self.assertEqual([entry["number"] for entry in found], list(range(1, len(found) + 1)))
        header = "Commit plan: %d commits, %d files" % (
            len(found),
            sum(len(entry["files"]) for entry in found),
        )
        self.assertEqual(plan_lines()[0], header)
        for entry in found:
            self.assertIn("   - Label: " + entry["label"], entry["lines"])
            regen = [line for line in entry["lines"] if line.startswith("   - Regen: ")]
            if entry["label"] == "mechanical":
                self.assertEqual(len(regen), 1, entry["subject"])
            else:
                self.assertEqual(regen, [], entry["subject"])

    def test_mechanical_entries_come_last(self) -> None:
        labels = [entry["label"] for entry in entries()]
        self.assertIn("mechanical", labels)
        first = labels.index("mechanical")
        self.assertEqual(set(labels[first:]), {"mechanical"})

    def test_regen_command_reproduces_the_change(self) -> None:
        """Tabs expanded to four spaces turn the before cli.py into the after one."""
        regen = [
            line
            for entry in entries()
            for line in entry["lines"]
            if line.startswith("   - Regen: ")
        ]
        self.assertEqual(
            regen, ["   - Regen: expand -t 4 cli.py > cli.py.tmp && mv cli.py.tmp cli.py"]
        )
        before = read(FIXTURE / "before" / "cli.py")
        self.assertIn("\t", before)
        self.assertEqual(before.expandtabs(4), read(FIXTURE / "after" / "cli.py"))

    def test_plan_ends_with_the_approval_section_skill_md_shows(self) -> None:
        """The approval lines are SKILL.md's, with <N> as the entry count."""
        template = approval(fenced(section(read(SKILL), "5. Render the plan")))
        count = str(len(entries()))
        expected = [line.replace("<N>", count) for line in template]
        self.assertEqual(approval(plan_lines()), expected)
        self.assertIn("This skill has not staged or committed anything.", " ".join(" ".join(expected).split()))

    def test_quoted_transcript_is_the_transcript(self) -> None:
        """The input section quotes the transcript minus its echo and exit status lines."""
        quoted = fenced(section(read(EXAMPLE), "The input"))
        transcript = [
            line
            for line in read(TRANSCRIPT).splitlines()
            if not line.startswith("$ echo") and not line.startswith("exit status: ")
        ]
        self.assertEqual(quoted, transcript)
        statuses = [
            line for line in read(TRANSCRIPT).splitlines() if line.startswith("exit status: ")
        ]
        self.assertEqual(set(statuses), {"exit status: 0"})

    def test_example_says_it_is_synthetic_and_not_an_invocation(self) -> None:
        text = " ".join(read(EXAMPLE).split())
        self.assertIn("This is synthetic example material.", text)
        self.assertIn("No agent invoked the skill to produce this page.", text)


if __name__ == "__main__":
    unittest.main()
