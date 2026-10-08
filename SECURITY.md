# Security

## Reporting a vulnerability

Report privately through GitHub:
<https://github.com/trycopilotai/plan-commits/security/advisories/new>

That opens a private security advisory visible only to the
maintainers. Do not put the details of a vulnerability in a
public issue.

If that link shows "Not Found", private reporting is not
turned on for this repository. Open a public issue titled
"Security report waiting" that says only that you have a
report, with no details, and a maintainer will arrange a
private channel.

## What is in scope

- **Prompt content that redirects an agent.** `SKILL.md` is
  instructions an agent may follow. Text in it that makes an
  agent send data to a place the operator did not name, write
  outside the repository it was started in other than to a
  path the operator names, or stage, commit or push, is a
  valid report.
- **The install blocks.** The two README blocks run
  `mkdir -p`, `mktemp -d`, `git clone`, `cp`, `mv` and
  `rm -rf`, all inside one skills directory under `$HOME`. A
  repository state that makes either block write or delete
  outside its install target is in scope.
- **The build and test scripts.** These are not part of the
  skill and neither install block copies them.
  `scripts/record_session.py` creates a temporary directory,
  copies the fixture files into it, runs `git init`,
  `git add` and `git commit` there with a fixed example
  identity and with user and system `git` configuration
  turned off, then runs each command listed in
  `evidence/demo-manifest.json` through `sh` in that
  directory. If every command exits 0, it rewrites the
  transcript and the manifest.
  With `RECORD_RAW_DIR` set it also writes a copy of the
  capture into that directory. `scripts/generate_demo.py`
  writes two SVG files; `scripts/verify_demo.py` reads files
  and writes none. `assets/build.py` finds a Chrome or
  Chromium binary from a fixed candidate list, runs it
  headless with a temporary profile directory, and writes the
  preview PNG and its stamp.
  `scripts/render_invocation.py` reads a client's raw JSON
  output and a prompt file, both named on its command line,
  and writes a transcript to standard output; it runs
  nothing and writes no file. `tests/test_worked_example.py`
  reads files. `tests/test_integrations.py` runs `git`
  against the repository root, builds the fixture repository
  and runs the manifest's commands in a temporary directory
  the way the recording script does, loads the two demo
  scripts to compare the images with the transcript, and
  runs `scripts/render_invocation.py` with the current
  Python on small JSON inputs it writes to a temporary
  directory.

## What the skill tells an agent to do

These are properties of the text, stated so you can decide
whether to use it. They are known limits, not findings:

- `SKILL.md` tells the agent to run `git status`,
  `git diff --numstat`, `git diff --cached --numstat`,
  `wc -l` and to read the diff, all in the repository it is
  planning for. `wc -l` on an untracked
  symbolic link follows it, so it can read a file outside
  the repository; the README's known limits say so.
- It tells the agent to read the repository's agent
  instructions, for example `AGENTS.md`, and follow the
  commit rules they give. What those instructions say is up
  to whoever wrote that repository.
- It tells the agent to write the plan to a file only when
  the operator asks, at the path the operator names.
- It tells the agent not to run `git add`, `git commit`,
  `git push` or any other command that changes the index,
  the history or a remote. Nothing in this repository
  enforces that. An agent acts with whatever permissions its
  host gives it, and nothing here narrows them.
- The commands that `scripts/record_session.py` runs are
  read from `evidence/demo-manifest.json`. Anyone who can
  edit that file chooses what the script runs.

## What is out of scope

The behaviour of `git`, `wc`, `swe-day`, Claude Code, Codex,
or any other host is out of scope here. Report those to
their own maintainers.
