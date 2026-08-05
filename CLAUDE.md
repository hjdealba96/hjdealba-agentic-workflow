# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A Claude Code **plugin marketplace** named `hjdealba-agentic-workflow`. It ships no application
code — every deliverable is a prompt (`SKILL.md`) plus JSON manifests. There is nothing to
compile and no runtime. "Correct" means the plugin loader accepts the structure and the
skill's description causes Claude to load it at the right moment.

Two plugins: `git-workflow` (skills `commit`, `branch`, `open-pr`) and `docs-workflow`
(skills `docs-system`, `reference-doc`).

Full authoring conventions live in [`docs/AUTHORING.md`](./docs/AUTHORING.md); the
distribution rationale is in [`README.md`](./README.md). Read `AUTHORING.md` before adding
or restructuring a skill — it records measured results, not just preferences.

## Commands

Validate before pushing — once at the root for the catalog, once per plugin directory for
skill frontmatter:

```bash
claude plugin validate . --strict
claude plugin validate ./git-workflow --strict
claude plugin validate ./docs-workflow --strict
python3 scripts/validate_structure.py
```

The last one is what CI gates on — offline and deterministic, covering the structural
rules the schema can't express. **Trigger evals do not run in CI** (no Claude
credentials on this repository), so they stay a manual step.

Test a change without publishing, by registering the working copy as a local marketplace:

```bash
/plugin marketplace add .
/plugin install git-workflow@hjdealba-agentic-workflow
/reload-plugins
```

Run a skill's trigger eval (the closest thing here to a test suite):

```bash
python3 scripts/run_trigger_eval.py                                  # every skill
python3 scripts/run_trigger_eval.py docs-workflow/skills/reference-doc
```

**This is a local tool, not CI tooling.** It spawns `claude -p` per query, so it needs
the CLI and working credentials — which is why it sits in `scripts/` rather than
`.github/`. Don't add a workflow for it; this repository has no API key, and a
workflow that can never run reads as coverage that doesn't exist.

The wrapper is not optional indirection: the upstream runner it calls **silently
reports 0.00 on every query on Windows.** It also handles the harness preconditions
that otherwise produce false negatives. Detail in its docstring, measured scores in
`AUTHORING.md`.

## Architecture

### Two-tier knowledge split

This is the central design decision and every skill implements it.

| Layer | Holds | Lives in |
| --- | --- | --- |
| The skill | Static conventions true in any repository | `SKILL.md` in this repo |
| Learnings | Facts true of one repository | `<consuming-repo>/.claude/learnings/<plugin>/<skill>.md` |

The test for which layer a rule belongs to: *would it still be correct in a different
repository?* "Use imperative mood in commit subjects" is universal — author it into the
skill body. "PRs target `develop`" is one team's convention — that's a learning.

Learnings **cannot** be co-located with `SKILL.md`. Installing a plugin doesn't copy it
into the project; it writes an `enabledPlugins` flag into the project's
`.claude/settings.json` and points at one shared cache at
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. That path is shared by every
project that installs the plugin, and the `<version>` segment is replaced on every update.
Both facts are fatal to co-location. The path is namespaced by plugin (not flat) so a
plugin skill can't silently take over the learnings file of a project's own same-named
skill.

Consequences when editing a skill:

- Every skill carries a `## Step 0: Load Project Learnings` section that reads the file
  **if it exists** and explicitly does **not** create it. A repo with no learnings file
  runs on built-in defaults with zero setup.
- Every skill ends with a `## Capturing Learnings` section containing a
  durable-vs-one-off table. That table is load-bearing — without it a skill records "make
  this shorter" as a permanent rule and degrades.
- Learnings are appended only on explicit user approval, and a contradicting learning
  updates the existing entry rather than appending a duplicate.
- Prefer runtime discovery over a learning where possible: PR template from `.github/`,
  labels via `gh label list`, default branch via `gh repo view`. Learnings cover only what
  discovery can't reach.

**Named profiles are the refinement of this.** Where the per-repo fact is a well-known
*model* rather than a free-form rule, the model's semantics are universal and belong in the
skill — `branch/reference/branching-models.md` holds what GitFlow and trunk-based each mean,
because that's true everywhere. The learning records only `Model:` plus `Deviations:`. The
deviations half is not optional: teams run "GitFlow without release branches" far more often
than textbook GitFlow, and a bare enum would force every hybrid into a wrong answer.

Keep such rules in **one** learning entry. A base-branch rule stored separately from the
model that implies it is how a learnings file ends up contradicting itself.

### Review-then-act via scratch files

Skills that produce something for approval write it to `claude-git-workflow/` at the root
of the repository they're running in — resolved via `git rev-parse --show-toplevel`, since
the skill may be invoked from a subdirectory — then consume that file with
`git commit -F` / `gh pr create --body-file`. This means the user's exact bytes are used
even if they hand-edit. Never substitute `-m` or `--body`.

The root location is chosen for navigability: a path the user is already working in beats
one under the system temp directory, which on Windows lands somewhere in
`AppData\Local\Temp` and reads as tool-owned. The cost is a `.gitignore` entry, so any
skill writing a scratch file must run `git check-ignore -q claude-git-workflow` and, if
unignored, propose adding `claude-git-workflow/` to the root `.gitignore` — appending only
on approval, same protocol as a learnings entry.

**Don't flatten this to loose files at the root.** One directory per plugin means one
`.gitignore` entry covers every present and future skill, a directory entry avoids the glob
semantics that make a bare `commit-message.md` match in every subdirectory, and it can't
collide with a same-named file in a consuming repo. Full reasoning in `AUTHORING.md`.

**The suggestion is not a gate.** If the user declines, the skill states the consequence
(`commit` stages the message file with `git add -A`; `open-pr` leaves an untracked file)
and proceeds. Deliberately no pathspec exclusion — the user is informed and decides.

**This pattern applies only where the artifact is consumed by a command.** `docs-workflow`
writes no scratch files: its output *is* the tracked file under `docs/`, reviewable with
`git diff` and revertible with `git checkout`. Staging that through a scratch directory
would add a copy step and no review value. Those skills present the plan before writing
instead — that's the review step.

### Structural rules the loader enforces

- **Only `plugin.json` belongs in `.claude-plugin/`.** `skills/` must sit at the plugin
  root — a `skills/` folder nested inside `.claude-plugin/` is silently ignored.
- **`source` in `marketplace.json` is a relative path** (`./git-workflow`). Paths
  containing `..` are rejected.
- **Bundled files must resolve through `${CLAUDE_PLUGIN_ROOT}`** — never `..`, an absolute
  path, or `~`, because installs are copied into the cache. This constrains files shipped
  *with* the skill only; reading and writing paths in the repository the skill runs in
  (learnings, scratch files) is expected.

### Versioning

`version` lives in `plugin.json` and **nowhere else** — setting it in the marketplace entry
too makes the validator warn on drift and can serve users a stale version. Bump it on every
substantive change or no installed copy updates. Patch = wording that doesn't change
behavior; minor = a new skill or a materially changed rule; major = removing/renaming a
skill or reversing a convention.

Adding a skill to an existing plugin needs no `marketplace.json` change — skills are
discovered automatically. Adding a *new* plugin needs an entry with `name`, `source`,
`description`, `category`, `tags` (no `version`), and a plugin must not be registered until
it ships at least one skill: an empty plugin validates and installs as a silent no-op.
Renaming or removing a plugin later requires a `renames` entry, or existing installs break
silently.

## Conventions when editing skills

**Invocation mode is a deliberate per-skill choice** in `SKILL.md` frontmatter. Default
(no fields) suits most skills. `disable-model-invocation: true` for side effects whose
timing the user must own — `open-pr` has it because it publishes to a real remote.
`user-invocable: false` for background knowledge that isn't a meaningful command.

**Descriptions are tuned against evals, not intuition.** What measurably moved scores:
lead with the action rather than the standard (a URL early in the description dilutes the
signal), pack in literal quoted trigger phrases as early as possible, and state the
prohibition explicitly ("Never run `git commit` without consulting it"). Implicit triggers
like "implement the retry logic" stay weak — don't over-tune for them.

**Trigger evals must include negatives, and the best negatives are the other skills in the
same plugin.** Over-triggering is as damaging as under-triggering.

**Body style that works here:** rule first then rationale, tables for anything enumerable,
a numbered `## Workflow` section for procedures, invalid examples shown alongside valid
ones with the reason each fails, and an explicit statement of when to confirm with the
user.

**Line endings are pinned to LF** by `.gitattributes` for all text files, overriding
`core.autocrlf`, because this repo is authored from both WSL and Windows. Git commands
inside skills should pass `--ignore-cr-at-eol` so CRLF churn isn't mistaken for a real
change.

## Ancestor copies

These skills were derived from `~/.claude/skills/` (`conventional-commit`,
`conventional-branch`, `open-pr`) and `mudflap-android/.claude/skills/`. Those copies still
exist and, at user scope, load alongside the plugin under their old names. **This
repository is the source of truth — don't edit the ancestors.**
