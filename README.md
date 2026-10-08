# plan-commits

A skill that has a coding agent plan granular commits for the
uncommitted changes in a git repository: logical groups
labelled `mechanical` or `semantic`, and for every file a
summary and its added, updated and deleted line counts, taken
from `git diff --numstat` or `wc -l` (see Known limits). The
plan ends with an approval section for the operator, and the
skill text tells the agent not to stage or commit anything.

Line counts come from git diff --numstat and wc -l.

No agent invoked the skill for the demo below: it is
the output of `git` and `wc` in a synthetic repository, and
a plan that Claude, an AI model, wrote from that output
during release preparation. Two agent invocations are
recorded separately, under Evidence.

<picture>
  <source
    media="(prefers-reduced-motion: reduce)"
    srcset="assets/poster.svg"
  />
  <img
    src="assets/demo.svg"
    alt="In a synthetic repository, a terminal runs git status, git diff --numstat, and wc -l on the one untracked file. Each command exits with status 0. No agent is invoked."
    width="100%"
  />
</picture>

The demo is reconstructed from
[`evidence/transcripts/count-session.txt`](evidence/transcripts/count-session.txt),
the recorded output of three of the `git` and `wc` commands
that steps 1 and 2 of `SKILL.md` name, in a synthetic
repository.
`scripts/record_session.py` wrote its `$` lines and its
`exit status` lines. The plan written from those counts
is the [worked example](examples/worked-example.md).

**Not measured, stated up front.**

- The count-session transcript is the output of `git` and
  `wc`, run from a shell. The worked example was written by
  Claude, an AI model, while it prepared this release, by
  reading `SKILL.md`; the skill was not installed, loaded or
  invoked for it.
- Whether an agent that reads `SKILL.md` groups, orders and
  summarises changes well has not been measured.
- No test checks the counts, groups or summaries of a plan
  written by an agent that invoked the skill. The plan the
  tests check that way is the worked example; for the two
  agent invocations, the tests check only that each
  transcript ends at the approval section and that no
  recorded call runs `git add`, `git commit` or `git push`.
- Neither install block below was run, from a shell or in
  a Claude Code or Codex session. The agent invocations
  loaded the skill from a plugin directory (Claude Code) and
  from a repository's `.agents/skills/` (Codex), not through
  the install blocks.

## What the claim covers

`SKILL.md` step 2 tells the agent to take each changed file's
added and deleted line counts from `git diff --numstat`; a
new file's line count from `git diff --cached --numstat` if
it is staged or from `wc -l` if it is untracked; not to
write approximate counts; and to prefer exact numbers. The
one exception it gives is a gitlink, which it records as 0
lines added. Known limits lists the
cases those commands do not cover. The transcript shows the output
of `git diff --numstat` and `wc -l` in the synthetic
repository, which has no staged file, and
[`tests/test_worked_example.py`](tests/test_worked_example.py)
checks that each count in the worked example's plan equals
the number the transcript gives for that file. The claim is about where the counts come
from. It is not a claim that an agent copies them correctly.

## What is in it

- [`skills/plan-commits/SKILL.md`](skills/plan-commits/SKILL.md)
  is the skill: read context, collect diffs and counts, group
  commits, detail each file, render the plan, save it if
  asked, and stop for approval. It includes the plan's output
  format and its approval section.
- [`skills/plan-commits/agents/openai.yaml`](skills/plan-commits/agents/openai.yaml)
  is the Codex interface file.
- [`examples/worked-example.md`](examples/worked-example.md)
  is a plan for a synthetic four-file change, with the
  fixture it was written from under
  [`examples/fixture/`](examples/fixture/).

The skill package is `SKILL.md` and `agents/openai.yaml`. It
holds no program.
The repository around it also holds Python scripts that
record the transcript, render the agent invocation
transcripts, build and check the images, and test the
repository. They are not part of the skill, and neither
install block copies them.

## Not included

- **`swe-day`**, a skill that runs one bounded unit of
  software work end to end. It calls this skill as
  `planCommits()` at its steps 10, 13 and 16, and at each of
  those checkpoints stops for the operator's approval of the
  plan before committing. Its own text lets a per-repository
  wrapper mark some groups as committable without that
  approval. It is published as `trycopilotai/swe-day`, at
  [github.com/trycopilotai/swe-day](https://github.com/trycopilotai/swe-day),
  and is not part of this repository. plan-commits does not
  need it: without it, invoke plan-commits directly.
- **A commit step.** The skill does not commit. Committing an
  approved plan is left to the operator or to a caller acting
  on the operator's approval; step 7 of `SKILL.md` says how
  the plan is meant to be used for that. No program here does
  it.
- **`git` and `wc`.** The skill tells the agent to run them.
  They are not shipped here.

## What changed from the original

`SKILL.md` was written fresh for this release from one
private protocol document of 71 lines, plus two lines taken
from a second private document, a companion commit
procedure. No file is copied from either. `SKILL.md` keeps
the protocol's seven numbered steps. Against the protocol:

- new: the frontmatter, the opening paragraphs, and the
  output template in step 5;
- step 1: "load AGENTS.md guardrails" became "read the
  repository's agent instructions, for example `AGENTS.md`,
  and follow the commit rules they give"; "inspect git
  status" became the command
  `git status --porcelain=v1 --untracked-files=all`, which
  lists each untracked file that is not ignored;
- step 2: "read the diff of each file before you summarise
  it" was added, and the protocol's rule "for new files, use
  `wc -l <file>`" became `git diff --cached --numstat` for a
  new staged file and `wc -l` for a new untracked file;
- step 3: the example "Makefile changes" became "build file
  changes";
- step 4 now says what SLOCS stands for;
- steps 2 to 5 are otherwise reworded. Apart from the
  changes listed here and the template and approval section
  in step 5, they keep the protocol's rules;
- step 6: the example save path, which named a directory in
  the private repository, became "the path the operator
  names"; "do not alter unrelated files" is unchanged;
- step 7 changes what the agent does. The protocol's step
  told the agent, when instructed, to stage each group (with
  `git add -p` if needed), commit it, and verify a clean
  status. Now the
  plan ends with an approval section, the agent stops there,
  and it is told not to stage, commit or push, "even when a
  group looks safe to commit", and that this stop applies
  even when the repository's instructions say to commit
  after planning. The approval section is new.
- step 7 also gives guidance to whoever commits after
  approval: stage one entry at a time, using `git add -p`
  where a file's lines belong to more than one entry, from
  the protocol's "use `git add -p` if needed"; verify with
  `git status` at the end, where the protocol's "verify
  clean status" now also accepts a tree in which only the
  changes of entries that were not approved remain; use the
  entry's subject as the commit subject, and put a
  mechanical entry's `Regen` command in the commit body,
  from the companion commit procedure; and re-run the skill
  if the changes move, which is new.

The step 7 change was made so the plan can serve as the
approval checkpoint `swe-day` asks for.

## Known limits

These are properties of the instructions as written. They
are known limits, not findings:

- `git diff --numstat` with no arguments compares the
  working tree with the index. Staged changes to files that
  were already tracked are not in its output, and `SKILL.md`
  does not tell the agent to count them some other way. Step
  2 covers a new staged file with
  `git diff --cached --numstat`.
- For a binary file, `git diff --numstat` prints `-` in
  place of both counts. `SKILL.md` does not say what to
  record then.
- `wc -l` counts newline characters, so a new untracked
  file whose last line has no newline is reported one line
  short.
- For a submodule whose pointer moved, `git diff --numstat`
  prints `1` added and `1` deleted, while step 2 says to
  record a gitlink as 0 lines added. For a new submodule,
  `wc -l` on its directory fails.
- `git diff --numstat` quotes a path that holds unusual
  characters, for example a non-ASCII name, and escapes
  those characters.
- `updated` is always 0 when the counts come from
  `git diff --numstat`, which reports only added and deleted
  lines. `SKILL.md` names no other source for it.
- A file renamed in the working tree, without `git mv`,
  shows as a deleted file in `git diff --numstat` (0 added,
  all its lines deleted) and as a new untracked file for
  `wc -l`. `SKILL.md` does not tell the agent to recognise
  it as a rename.
- A deleted file shows as 0 added and all its lines deleted.
  `SKILL.md` does not mention deleted files, though the
  counts cover them.
- For a new untracked file that is a symbolic link, `wc -l`
  follows the link, so it counts the target, which may be
  outside the repository, or fails if the target is missing.
- For a new untracked binary file, `wc -l` counts newline
  bytes, which are not lines of source.
- A change of file mode only, for example making a file
  executable, shows as `0` added and `0` deleted.
  `SKILL.md` does not say how to describe it.
- Step 7 lets one file's lines go to more than one entry,
  staged with `git add -p`. `git diff --numstat` and `wc -l`
  count whole files, and `SKILL.md` does not say how to
  count the part of a file that belongs to each entry. The
  worked example puts each file in one entry.
- `git status --untracked-files=all` does not list ignored
  files unless `--ignored` is passed, so the plan does not
  cover changes to ignored files.
- `.codex-plugin/plugin.json` has no `interface.logo` or
  `interface.composerIcon` field, and this repository ships
  no logo for one. The manifest is not ready for submission
  to a public Codex plugin directory.
- The instruction not to stage, commit or push is text.
  Nothing in this repository enforces it; an agent that has
  permission to run `git` can still commit.
- In one unpublished Codex run, the agent searched the
  parent directory for `AGENTS.md`, outside the repository it
  was told to stay in; step 1 does not say where to look for
  agent instructions.

## Use it

Both installs below are pinned to a tag rather than to
`main`.

### Claude Code

Save this as `install.sh` and run it with `sh install.sh`.
It sets `set -eu` and an `EXIT` trap, so pasting it straight
into an interactive shell will end that shell if the clone
fails.

```sh
set -eu
release=v0.1.2
install_target="$HOME/.claude/skills/plan-commits"
install_parent="$(dirname "$install_target")"
mkdir -p "$install_parent"
install_tmp="$(mktemp -d "$install_parent/.plan-commits.XXXXXX")"
install_stage="$install_tmp/package"
rollback_install() {
  if [ ! -e "$install_target" ]; then
    if [ -e "$install_tmp/previous" ]; then
      mv "$install_tmp/previous" "$install_target"
    fi
  fi
  rm -rf "$install_tmp"
}
trap rollback_install EXIT
git clone --quiet --depth 1 --branch "$release" \
  https://github.com/trycopilotai/plan-commits \
  "$install_tmp/clone"
mkdir -p "$install_stage"
cp -R "$install_tmp/clone/skill/." "$install_stage/"
if [ -e "$install_target" ]; then
  mv "$install_target" "$install_tmp/previous"
fi
mv "$install_stage" "$install_target"
trap - EXIT
rm -rf "$install_tmp"
```

The name to invoke is `/plan-commits`.

### Codex

Save this one the same way. The only line that differs from
the block above is `install_target`.

```sh
set -eu
release=v0.1.2
install_target="$HOME/.agents/skills/plan-commits"
install_parent="$(dirname "$install_target")"
mkdir -p "$install_parent"
install_tmp="$(mktemp -d "$install_parent/.plan-commits.XXXXXX")"
install_stage="$install_tmp/package"
rollback_install() {
  if [ ! -e "$install_target" ]; then
    if [ -e "$install_tmp/previous" ]; then
      mv "$install_tmp/previous" "$install_target"
    fi
  fi
  rm -rf "$install_tmp"
}
trap rollback_install EXIT
git clone --quiet --depth 1 --branch "$release" \
  https://github.com/trycopilotai/plan-commits \
  "$install_tmp/clone"
mkdir -p "$install_stage"
cp -R "$install_tmp/clone/skill/." "$install_stage/"
if [ -e "$install_target" ]; then
  mv "$install_target" "$install_tmp/previous"
fi
mv "$install_stage" "$install_target"
trap - EXIT
rm -rf "$install_tmp"
```

The name to invoke is `$plan-commits`.

Each block works in a temporary `.plan-commits.*` directory
beside the target and removes it on exit. An existing install
at the target is replaced.

Both blocks copy through `skill/`, a symlink to
`skills/plan-commits/`, so the installed directory holds
`SKILL.md` and `agents/` as real files. They assume a
checkout that keeps symlinks; with `core.symlinks` off the
copy fails and the block rolls back. The repository also
carries `.claude-plugin/plugin.json` and
`.codex-plugin/plugin.json` for a marketplace. No
marketplace lists this skill, so no marketplace install is
described here.

## Evidence

`evidence/transcripts/count-session.txt` is the recorded
output behind the claim at the top of this file.
[`scripts/record_session.py`](scripts/record_session.py)
builds the synthetic repository in a throwaway directory
(the files under `examples/fixture/before/` committed, then
replaced by those under `examples/fixture/after/`) and runs
the three commands listed in
[`evidence/demo-manifest.json`](evidence/demo-manifest.json)
in it. It writes the `$` lines and the exit status lines;
the `echo` lines among them are written, not run. The rest
is the output of `git` and `wc`. The transcript is not
edited: no path or host name appears in that output, so
there was nothing to replace. The manifest records the
SHA-256 of `SKILL.md`, of `agents/openai.yaml`, of the worked
example, of each fixture file, of the recording script and of
the transcript, with the commands, the `git` version and the
date.

No agent invoked the skill for the count session or the
worked example. The worked-example plan was written by
Claude during release preparation and is illustrative, not
evidence that the skill ran.

### Agent invocations

Claude Code was started once and Codex twice, with the
v0.1.0 skill text (unchanged since), on one synthetic
fixture: a one-file Python repository with one commit and
three uncommitted changes, a modified tracked file, a new
staged file and a new untracked file, so that
`git diff --numstat`, `git diff --cached --numstat` and
`wc -l` each apply. The
prompt asked for a commit plan for the working tree. One run
per client is published, on one fixture; it is
not a benchmark.

- [`evidence/transcripts/2026-10-08-claude-code-invocation.txt`](evidence/transcripts/2026-10-08-claude-code-invocation.txt):
  Claude Code 2.1.220, invoked with `/plan-commits`. It
  loaded the skill, ran the counting commands, wrote a
  three-commit plan whose counts match those commands, and
  stopped at the approval section.
- [`evidence/transcripts/2026-10-08-codex-invocation.txt`](evidence/transcripts/2026-10-08-codex-invocation.txt):
  Codex 0.146.0, invoked with `$plan-commits`. It read
  `SKILL.md`, ran the same commands, wrote a three-commit
  plan with the same counts, and stopped at the approval
  section. It is the second Codex run, made in a fresh
  temporary directory; the first Codex run searched outside
  the fixture and is listed in the manifest, with its raw
  output's SHA-256, as not published.

After each run, `git log` and `git status` in the fixture
showed nothing committed or staged beyond the starting
state. The runs do not show how an agent handles the cases
under Known limits, or what it does after approval.

[`scripts/render_invocation.py`](scripts/render_invocation.py)
renders each transcript from the client's raw JSON output,
which is not committed; its SHA-256 is in the manifest. It
writes the prompt, each tool call's name, arguments and
status, and the final message verbatim, and cuts any
argument longer than 300 characters, marking the cut
`...[N more characters]`. Its only edits are path and name
replacements, each declared in the manifest:
`replace-isolation-root` (Codex only, applied first),
`replace-plugin-root`, `replace-capture-root`,
`replace-scratch-root`, `replace-home` and
`replace-hostname`.

`make check` runs two suites.
[`tests/test_worked_example.py`](tests/test_worked_example.py)
checks the worked example's counts, file coverage, labels,
mechanical-last order, `Regen` command, quoted transcript and
approval section against the transcript, the fixture and
`SKILL.md`.
[`tests/test_integrations.py`](tests/test_integrations.py)
ties this file, both plugin manifests, the evidence manifest,
the transcript, the demo images and the social preview to
each other, and
rebuilds the synthetic repository to check that the commands
still print what the transcript shows, up to spacing.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security

See [`SECURITY.md`](SECURITY.md).

## License

MIT. See [`LICENSE`](LICENSE).

## Not affiliated with GitHub or GitHub Copilot

The `trycopilotai` organisation name is not a claim of any
relationship with GitHub Copilot. This project is not
affiliated with, endorsed by, or sponsored by GitHub, Inc.
GitHub and GitHub Copilot are trademarks of GitHub, Inc.
