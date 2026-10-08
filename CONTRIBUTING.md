# Contributing

This repository is one skill, a worked example for it, and
the scripts that record the evidence transcript, build and
check the demo images, and test the repository.

## Run the checks first

```sh
make check
```

That runs `tests/test_worked_example.py` and
`tests/test_integrations.py`. Both need `python3` and no
Python package outside the standard library. The second also
needs
`git`, `wc` and `sh`, and a clone with its history,
because it reads `git log`. When `HEAD` carries a release
tag, it also checks the tag against the manifests' version;
without one, that test is skipped.

**The suites pin prose.** These will fail on an
innocent-looking edit:

- the claim line at the top of the README must appear
  verbatim;
- each install block must carry its own `release=` pin at
  the version both plugin manifests ship;
- `SKILL.md` must stay under 500 lines;
- the approval section of the worked example must be the one
  in `SKILL.md`, with `<N>` replaced by the number of
  entries;
- every count in the worked example must be one the
  transcript shows;
- `evidence/demo-manifest.json` records the SHA-256 of
  `SKILL.md`, of `agents/openai.yaml`, of the worked example,
  of each fixture file, of `scripts/record_session.py` and of
  the transcript, so an edit to any of those files, prose
  included, fails until the manifest is refreshed as
  described next.

If you change one of those, change the thing it describes
too.

## Changing the skill, the example or the recording script

After an edit to `SKILL.md`, to `agents/openai.yaml`, to the
worked example, to a fixture file, or to
`scripts/record_session.py`, run:

```sh
make record
make demo
```

`make record` runs `scripts/record_session.py`. It rebuilds
the synthetic repository in a throwaway directory, runs the
commands listed in the manifest, writes the transcript, and
rewrites the manifest's hashes, date and `git` version. If a
command exits non-zero it writes neither the transcript nor
the manifest, and exits 1.
It needs `sh`, `git` and `wc`. The committed transcript was
recorded with the BSD `wc`, which pads its count with
spaces; GNU `wc` does not, so recording on Linux changes that
line's spacing. `make demo` rebuilds the two images from the
transcript. `make assets` rebuilds the social preview and
needs Chrome or Chromium; `make asset-check` does not.

If you change the fixture, update the worked example's counts
and the transcript quoted in it to match.

## What is most useful

Open an issue for any of these. The labels
`good first issue` and `help wanted` mark the ones that are
ready to pick up.

- **A case the counting rules miss.** The README's "Known
  limits" section lists the ones found so far. Name another
  one, with a small repository state that shows it.
- **A report of trying it.** Say which host ran it, what the
  changes were, and where the plan differed from what
  `SKILL.md` asks for.

## Pull requests

Prose changes to `SKILL.md` are welcome. Say what the text
told an agent to do before the change and what it tells it
after.

Keep `SKILL.md` under 500 lines; the suite enforces it.
Frontmatter carries `name` and `description` and nothing
else. Keep the package free of program files; the suite
enforces that.

The top-level `skill` is a symlink to `skills/plan-commits/`.
Do not reverse that orientation.

Commit with your own identity and no `Co-authored-by`
trailer of any kind. The suite fails on one anywhere in
history, so do not apply review suggestions through the
GitHub UI, and do not squash-merge a pull request that has
more than one author.
