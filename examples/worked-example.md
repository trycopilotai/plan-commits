# Worked example

This is synthetic example material. The repository, its
files and its changes were made up for this example and come
from no real project.

No agent invoked the skill to produce this page. The plan
below was written by Claude, an AI model, while it prepared
this release, by reading `SKILL.md` and applying it to the
fixture and the recorded counts; the skill was not
installed, loaded or invoked for it. It shows the output
format on a small input. It is not evidence of what an agent
does with the skill.

## The input

A repository named `slugger` with one commit, built from
[`fixture/before/`](fixture/before/). Its working tree then
holds the files in [`fixture/after/`](fixture/after/), so
four files have uncommitted changes:

- `README.md` gains a note about a new option;
- `slugify.py` gains that option, `max_length`;
- `cli.py` changes its indentation from tabs to four spaces
  and nothing else;
- `tests/test_slugify.py` is new and untracked.

[`scripts/record_session.py`](../scripts/record_session.py)
builds that repository in a throwaway directory and runs
three of the commands from steps 1 and 2 of `SKILL.md` in
it. The repository has no staged file, so
`git diff --cached --numstat` is not run. Their
output, unedited, is
[`evidence/transcripts/count-session.txt`](../evidence/transcripts/count-session.txt):

```text
$ git status --porcelain=v1 --untracked-files=all
 M README.md
 M cli.py
 M slugify.py
?? tests/test_slugify.py
$ git diff --numstat
3	0	README.md
4	4	cli.py
5	2	slugify.py
$ wc -l tests/test_slugify.py
      15 tests/test_slugify.py
```

The transcript's `echo "exit status: $?"` lines, which the
recording script writes and does not run, and its
`exit status` lines are left out above; each command exited
0.

## The plan

```text
Commit plan: 4 commits, 4 files

1. [semantic] Document the max_length option of slugify
   - Label: semantic
   - README.md
     - Summary: adds a blank line and a two-line note that
       slugify(text, max_length=None) cuts the slug to at
       most max_length characters and drops a trailing dash.
     - SLOCS added/updated/deleted: 3/0/0
2. [semantic] Add tests for slugify
   - Label: semantic
   - tests/test_slugify.py
     - Summary: new file with two tests: words are
       lowercased and joined with dashes, and max_length=6
       turns "Hello World" into "hello" with no trailing
       dash.
     - SLOCS added/updated/deleted: 15/0/0
3. [semantic] Add a max_length option to slugify
   - Label: semantic
   - slugify.py
     - Summary: slugify takes an optional max_length. When
       it is set, the slug is cut to that many characters
       and a trailing dash is removed. Without it, the
       result is the same as before.
     - SLOCS added/updated/deleted: 5/0/2
4. [mechanical] Indent cli.py with spaces
   - Label: mechanical
   - Regen: expand -t 4 cli.py > cli.py.tmp && mv cli.py.tmp cli.py
   - cli.py
     - Summary: indentation changes from tabs to four
       spaces. No other line changes.
     - SLOCS added/updated/deleted: 4/0/4

Approval
- Status: awaiting operator approval. This skill has not
  staged or committed anything.
- To approve: reply with the entry numbers to commit as
  planned, for example "approve 1-4" or "approve 1".
- To change: reply with an entry number and the change; the
  plan is re-rendered and approval is asked again.
- Entries that are not approved are left uncommitted.
- This skill does not commit. Approved entries are committed
  after this reply, by the operator or by a caller acting on
  the approval.
```

## What is checked

[`tests/test_worked_example.py`](../tests/test_worked_example.py)
checks, against the transcript and the fixture:

- each file's added and deleted counts equal the
  `git diff --numstat` line for that file, or for the new
  file the `wc -l` count, and every `updated` count is 0;
- each changed file appears in exactly one entry;
- each entry carries its label in brackets and on a
  `Label:` line, and only the mechanical entry has a
  `Regen:` line;
- the mechanical entry comes after every semantic entry;
- the transcript quoted above is the transcript without its
  `echo` and `exit status` lines, and every command exited 0;
- tabs expanded to four spaces in `fixture/before/cli.py`
  give `fixture/after/cli.py`, which is what the `Regen`
  command does;
- the plan ends with the approval section that `SKILL.md`
  shows.

Nothing checks the commit subjects, the summaries, the
grouping, or the order beyond the mechanical entry coming
last. They are one reading of `SKILL.md`.
