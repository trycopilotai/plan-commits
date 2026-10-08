#!/usr/bin/env python3
"""Record the counting session again and refresh the evidence manifest.

    python3 scripts/record_session.py

It builds the synthetic repository of the worked example in a
throwaway directory: the files under ``examples/fixture/before/``
are committed, then replaced by the files under
``examples/fixture/after/``, which leaves the changes uncommitted.
It then runs, in that repository, the commands listed in
``evidence/demo-manifest.json``: three of the commands that
steps 1 and 2 of ``SKILL.md`` name, ``git status``,
``git diff --numstat`` and ``wc -l``.

The transcript has the form of a shell session. The script writes
each command line, then the command's output with standard error
merged in, then an ``echo "exit status: $?"`` line and the exit
status line. The ``echo`` line is written by the script, not run.
The output itself is not edited.

The manifest's hashes of ``SKILL.md``, ``agents/openai.yaml``, this
script, the fixture files, the worked example and the transcript
are then rewritten, with the date and the ``git`` version. If any
command exits non-zero, the script prints the capture, writes
neither file, and exits 1.

Set ``RECORD_RAW_DIR`` to a directory to also keep a copy of the
capture there.

This runs ``git``, ``wc`` and ``sh``. It starts no agent and does
not invoke the skill.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "demo-manifest.json"
FIXTURE = ROOT / "examples" / "fixture"
IDENTITY = {
    "GIT_AUTHOR_NAME": "Example Author",
    "GIT_AUTHOR_EMAIL": "author@example.com",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
    "GIT_COMMITTER_NAME": "Example Author",
    "GIT_COMMITTER_EMAIL": "author@example.com",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment(home: Path) -> dict:
    """A small environment with no user or system git configuration."""
    values = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "LC_ALL": "C",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    values.update(IDENTITY)
    return values


def copy_tree(source: Path, destination: Path) -> None:
    for path in sorted(source.rglob("*")):
        if path.is_dir() or path.name == ".DS_Store" or "__pycache__" in path.parts:
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(path), str(target))


def build_fixture(repository: Path, home: Path) -> None:
    """Commit the before tree, then put the after tree in its place."""
    env = environment(home)
    repository.mkdir(parents=True)
    copy_tree(FIXTURE / "before", repository)
    for command in (
        ["git", "-c", "init.defaultBranch=main", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "Add slugger"],
    ):
        subprocess.run(command, cwd=str(repository), env=env, check=True)
    for path in sorted(repository.iterdir()):
        if path.name == ".git":
            continue
        if path.is_dir():
            shutil.rmtree(str(path))
        else:
            path.unlink()
    copy_tree(FIXTURE / "after", repository)


def record(commands: list, repository: Path, home: Path) -> tuple:
    """Run each command through ``sh`` and return the capture and a failure flag."""
    lines = []
    failed = False
    for command in commands:
        result = subprocess.run(
            ["sh", "-c", command],
            cwd=str(repository),
            env=environment(home),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        lines.append("$ " + command)
        lines.extend(result.stdout.splitlines())
        lines.append('$ echo "exit status: $?"')
        lines.append("exit status: %d" % result.returncode)
        if result.returncode != 0:
            failed = True
    return "\n".join(lines) + "\n", failed


def capture(commands: list) -> tuple:
    """Build the fixture in a throwaway directory and record the commands."""
    with tempfile.TemporaryDirectory() as scratch:
        base = Path(scratch).resolve()
        home = base / "home"
        home.mkdir()
        repository = base / "slugger"
        build_fixture(repository, home)
        return record(commands, repository, home)


def git_version() -> str:
    return subprocess.run(
        ["git", "--version"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    ).stdout.strip()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    commands = manifest["invocation"]["commands"]
    raw, failed = capture(commands)

    raw_dir = os.environ.get("RECORD_RAW_DIR")
    if raw_dir:
        Path(raw_dir, "count-session.source.txt").write_text(raw, encoding="utf-8")

    if failed:
        sys.stdout.write(raw)
        print("a command exited non-zero; nothing written")
        return 1
    transcript = ROOT / manifest["output"]["path"]
    transcript.write_text(raw, encoding="utf-8")

    manifest["date"] = datetime.date.today().isoformat()
    manifest["invocation"]["git"] = git_version()
    for key in ("skill", "interface", "worked_example"):
        manifest[key]["sha256"] = sha256(ROOT / manifest[key]["path"])
    manifest["programs"] = [
        {"path": "scripts/record_session.py", "sha256": sha256(Path(__file__).resolve())}
    ]
    fixture = []
    for path in sorted(FIXTURE.rglob("*")):
        if path.is_file() and path.name != ".DS_Store" and "__pycache__" not in path.parts:
            fixture.append(
                {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
            )
    manifest["fixture"] = fixture
    manifest["output"]["sha256"] = sha256(transcript)
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("wrote %s" % transcript.relative_to(ROOT))
    print("wrote %s" % MANIFEST.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
