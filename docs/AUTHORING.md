# Authoring skills for this marketplace

Conventions for adding a skill to an existing plugin, or adding a new plugin.
Verified against Claude Code v2.1.220 — the plugin system evolves, so re-check
the [reference docs](https://code.claude.com/docs/en/plugins-reference) when
something behaves unexpectedly.

## Adding a skill to an existing plugin

1. Create `<plugin>/skills/<skill-name>/SKILL.md`. The directory name is what
   determines the invocation name, so keep it kebab-case and meaningful.
2. Write the frontmatter and body (see below).
3. Bump `version` in `<plugin>/.claude-plugin/plugin.json`. Skipping this means
   nobody's installed copy updates.
4. Validate: `claude plugin validate ./<plugin> --strict`.

No change to `marketplace.json` is needed — skills are discovered automatically
inside an already-registered plugin.

## Adding a new plugin

1. Create `<plugin>/.claude-plugin/plugin.json` and `<plugin>/skills/`.
2. Add an entry to the `plugins` array in `.claude-plugin/marketplace.json` with
   `name` and `source` (`./<plugin>`), plus `description`, `category`, `tags`.
   Do **not** add `version` here.
3. Validate both the root and the new plugin directory.

Renaming or removing a plugin later requires a `renames` entry in
`marketplace.json` mapping the old name to the new one (or to `null` if
removed), otherwise existing users' installs break silently.

## SKILL.md frontmatter

Every field is optional; `description` is the one that matters most, because it
is what Claude reads to decide whether the skill is relevant.

```yaml
---
name: commit
description: >
  What the skill does, and the trigger phrases that should surface it.
  Lead with the primary use case.
---
```

Fields worth knowing:

| Field | Notes |
| --- | --- |
| `name` | Display name. Defaults to the directory name. Set it explicitly — for a plugin shipping a single root-level `SKILL.md`, the fallback is the install directory, which is a version string that changes on every update. |
| `description` | What it does *and when to use it*. Combined with `when_to_use`, truncated at 1,536 characters in the skill listing, so front-load the key case. |
| `when_to_use` | Extra trigger phrases, appended to `description`. Counts toward the same cap. |
| `disable-model-invocation` | `true` = only you can invoke it. Also excludes it from subagent preloading and scheduled tasks. Default `false`. |
| `user-invocable` | `false` = hidden from the `/` menu; only Claude invokes it. Default `true`. |
| `allowed-tools` | Tools pre-approved for the invoking turn. Space- or comma-separated, or a YAML list. |
| `disallowed-tools` | Tools removed from the pool while the skill is active. |
| `argument-hint` | Autocomplete hint, e.g. `[ticket-number]`. |
| `model` | Model override for the remainder of the turn. |

Booleans accept `true`/`false`, and also `yes`/`no`/`on`/`off`/`1`/`0` in any
case as of v2.1.218.

### Choosing an invocation mode

Default (no invocation fields) is right for most skills — a review checklist or
a naming convention should be available both ways.

Set `disable-model-invocation: true` when the skill has a side effect whose
timing you want to own. Opening a PR, pushing, deploying, or posting to Slack
all qualify: you don't want Claude deciding your branch looks ready to ship.

Set `user-invocable: false` when the skill is background knowledge rather than
an action — context about a legacy system, or a house style that should apply
whenever Claude writes code but isn't meaningful to type as a command.

## Writing the body

The body is the prompt. What has worked well in the existing skills:

- **Lead with the rule, then the rationale.** Tables for anything enumerable
  (commit types, branch prefixes) — they are scannable and hard to misread.
- **Include a Workflow section** with numbered steps for anything procedural.
  This is what makes a skill produce consistent output instead of a
  differently-shaped answer each time.
- **Show invalid examples alongside valid ones**, with the reason each fails.
  `branch` does this and it measurably tightened the output.
- **Say when to confirm with the user.** Skills that create branches, commits,
  or PRs should present the proposed artifact before acting.
- **Keep bundled files self-contained.** Anything shipped *with* the skill —
  `reference.md`, `scripts/` — must be referenced through
  `${CLAUDE_PLUGIN_ROOT}`, never via `../`, an absolute path, or `~`. Installs
  are copied into a cache, so those break.

  **`${CLAUDE_PLUGIN_ROOT}` is the plugin's installation directory, not the skill's.**
  A reference file sitting beside `SKILL.md` must therefore be written
  `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/reference/<file>.md` — the `skills/<skill>/`
  segment is not optional. `branch` shipped for several releases with
  `${CLAUDE_PLUGIN_ROOT}/reference/branching-models.md`, which resolved to nothing, so
  the branching-model profiles its first step depends on were never readable. Nothing
  surfaced it: the placeholder substitutes correctly (it resolves anywhere it appears
  in skill content), the resulting path simply doesn't exist, and the failure shows up
  only when a user invokes the skill. `scripts/validate_structure.py` now fails the
  build on it.

  A reference shared by two skills in one plugin is the exception worth knowing: put it
  at the plugin root, as `docs-workflow/reference/` does, and the short path is then
  correct.

  This constrains *bundled* files only. A skill may still read and write paths in
  the repository it's running in — that's exactly what the learnings file and the
  scratch files under `claude-git-workflow/` are, and both are resolved at runtime
  rather than shipped.

Supporting files (`reference.md`, `scripts/`) can live alongside `SKILL.md` in
the skill directory and are loaded only when the skill is used — long reference
material costs nothing until then.

**When to split material into a reference file.** Move it out of `SKILL.md` when it
is bulky, enumerable, and needed only after an earlier step selects which part
applies. `branch/reference/branching-models.md` is the example: one profile per
branching model, and a run reads exactly one of them. Keeping the procedure in
`SKILL.md` and the lookup tables beside it also keeps the body scannable, which is
what makes the numbered workflow work.

**Don't reach for a separate skill to share knowledge between skills.** Skills
don't compose — there is no `requires:` mechanism, so a `user-invocable: false`
background skill has to win its own trigger competition. When the user says
"create a branch", `branch` is what loads, and a companion skill holding the
branching-model tables would fire unreliably; described broadly enough to fire
reliably, it would start hijacking `commit` and `open-pr` requests instead. A
bundled reference file inside the skill that needs it has neither problem.

## The learnings pattern

Every skill in this marketplace follows the same two-tier split. It exists to
answer one question: how does a single skill, shipped to every repository,
respect conventions that differ per repository?

| Layer | Holds | Lives in | Changes |
| --- | --- | --- | --- |
| **The skill** | Static, universal conventions | `SKILL.md` | Rarely — a release |
| **Learnings** | Facts true of one repository | `<repo>/.claude/learnings/<plugin>/<skill>.md` | Often — on approval |

The dividing line is whether the rule would still be correct in a different
repository. "Use imperative mood in commit subjects" is universal — author it
into the skill. "Scope commits by Linear ticket ID" is one team's convention —
that's a learning.

**Learnings cannot live in the plugin.** Installing a plugin does not copy it
into the project — it writes an `enabledPlugins` flag into the project's
`.claude/settings.json` and points at one shared copy at
`<cache>/<marketplace>/<plugin>/<version>/`.

That breaks co-location twice over. The cached folder is shared by *every*
project that installs the plugin, so a `learnings.md` written beside `SKILL.md`
would leak one repository's conventions into all the others — per-project
learnings are structurally impossible there. And the `<version>` segment means
the whole folder is replaced on the next `/plugin update`, taking the file with
it.

The learnings file therefore lives in the consuming repository, which also means
it gets committed and shared with the team. See the README for the full
rationale.

### Required structure

Every skill gets a `Step 0: Load Project Learnings` section:

```md
Read `.claude/learnings/<plugin>/<skill>.md` from the repository root if it exists.

**If the file does not exist, proceed with defaults. Do not create it.**
```

The path is namespaced by plugin, not flat. A flat `.claude/learnings/<skill>.md`
collides with a project's own same-named skill — a repo with its own
`code-review` skill would have its learnings file silently taken over by a plugin
skill of that name — and with a second plugin from this marketplace shipping a
common name like `review`, `test`, or `lint`. The plugin folder also makes
provenance obvious: everything under `git-workflow/` came from the plugin,
anything beside it belongs to the project.

Nothing is scaffolded in advance. A repository with no learnings file simply
runs on the skill's built-in conventions — no setup, no empty files.

And a `## Capturing Learnings` section at the end, containing a table that
separates durable repository facts from one-off edits:

| Correction | Durable repo fact? |
| --- | --- |
| "Target `develop`, not `main`" | Yes — repository convention |
| "Make this summary shorter" | No — one-off edit |

This table is the important part. Without it, a skill will happily record "make
this shorter" as a permanent rule and degrade over time.

### Capture protocol

Propose, never assume. On a durable correction, the skill drafts the entry,
shows it, and appends **only on approval** — creating
`.claude/learnings/<plugin>/` and the file if needed, with this header:

```md
# Learnings — `/<plugin>:<skill>`

Repository-specific patterns for the `<skill>` skill. The skill reads this file
before <doing its thing>. Global conventions live in the skill itself; only
facts unique to this repository belong here.

---
```

Entries are a `##` title followed by `**Rule:**` and `**Why:**`, plus `**When:**`
when conditional. A new learning that contradicts an existing one updates that
entry rather than appending a duplicate — otherwise the file accumulates
contradictions and the skill's behavior becomes unpredictable.

### Scratch files

Skills that produce something for review before acting — a commit message, a PR
body — write it to `claude-git-workflow/` at the **root of the repository the
skill is running in**, resolved via `git rev-parse --show-toplevel` so invoking
from a subdirectory still lands at the root. The user can hand-edit the file, and
the skill consumes it with `git commit -F` or `gh pr create --body-file` so their
exact bytes are used.

The root location is deliberate: a path inside the repository the user is already
working in is far easier to find and open than one under the system temp
directory, which on Windows resolves somewhere under `AppData\Local\Temp` and
reads as tool-owned rather than theirs.

**Why a directory and not loose files at the root.** Two files named
`commit-message.md` and `pr-content.md` sitting at the root would be marginally
quicker to open, and it was considered. The directory wins on four counts:

1. **`.gitignore` glob semantics.** A bare `commit-message.md` entry matches that
   filename in *every* directory of the repo, so a consuming project with a
   legitimate `docs/commit-message.md` would have it silently ignored. Flat files
   would need anchored entries (`/commit-message.md`) and every skill would have
   to get that right in every repo. A directory entry has no such ambiguity.
2. **One entry, permanently.** `claude-git-workflow/` already covers every skill
   added later. Flat files need a line per file, so a fourth skill writing a
   scratch file means a fresh `.gitignore` edit — and a fresh approval prompt —
   in every repo that already installed the plugin.
3. **Collision risk.** These skills run in arbitrary repositories, and those
   filenames are generic enough that a project may already have one. The skill
   would overwrite it without warning. Namespacing removes the failure mode.
4. **Provenance.** `claude-git-workflow/` is self-evidently tool-owned. Two loose
   markdown files at the root read as project content, and someone seeing them in
   a file tree or a diff can't tell what wrote them.

The cost is one extra click, which doesn't touch the actual goal — the file being
in the repository the user is working in rather than under a temp path.

**The cost is a `.gitignore` entry, and skills must handle it.** A scratch file in
the working tree will otherwise be committed. Each skill that writes one checks
`git check-ignore -q claude-git-workflow`, and if the directory isn't ignored,
proposes adding `claude-git-workflow/` to the root `.gitignore` — **appending only
on approval**, like a learnings entry. One directory for the whole plugin means
one entry covers every skill, present and future.

The suggestion is a suggestion, not a gate. If the user declines, the skill says
plainly what follows — `commit` will stage the message file with `git add -A`, and
`open-pr` will leave an untracked file behind — and proceeds. No pathspec
exclusion papers over it; the user gets the information and makes the call.

An earlier version of this marketplace wrote scratch files under
`${TMPDIR:-/tmp}/claude-git-workflow/` specifically to avoid the `.gitignore`
entry. Navigability won: a file the user can't find can't be hand-edited, which
defeats the point of the review step.

## Evals

Skills are prompts. They fail silently and drift without warning, so the only
way to know a skill still works is to run it. Trigger evals live at
`<plugin>/skills/<skill>/evals/trigger.json` and answer one question: does the
description cause Claude to load the skill when it should, and leave it alone
when it shouldn't?

```json
[
  {"query": "commit my changes", "should_trigger": true},
  {"query": "git commit these fixes", "should_trigger": true},
  {"query": "create a branch for the login work", "should_trigger": false},
  {"query": "run the unit tests", "should_trigger": false}
]
```

**Include negatives, and make them the other skills in this plugin.** Over-
triggering is as damaging as under-triggering — a `commit` skill that fires on
"open a PR" is broken. Cross-skill negatives are the cheapest way to prove
routing works.

### Running them

Use the wrapper. It handles every precondition below, forces `--num-workers 1`, and
prints a table shaped for pasting into a pull request:

```bash
python3 scripts/run_trigger_eval.py                                  # every skill
python3 scripts/run_trigger_eval.py docs-workflow/skills/reference-doc
```

It needs the `claude` CLI and working credentials, which is why it lives in
`scripts/` and not under `.github/` — **it is a local developer tool and cannot run
in this repository's CI.** See [Why they don't run in CI](#why-they-dont-run-in-ci).

Calling the upstream runner directly still works, and is what the wrapper does under
the hood:

```bash
cd <a real git repo with a .claude/ directory>
PYTHONPATH=<skill-creator>/skills/skill-creator \
  python3 -m scripts.run_eval \
    --eval-set <skill>/evals/trigger.json \
    --skill-path <skill> \
    --runs-per-query 3 \
    --num-workers 1
```

Four things about that runner, each of which has already cost hours:

- **It is POSIX-only and fails silently on Windows.** `select()` on a pipe raises
  `WinError 10093`, and `SKILL.md` is read as cp1252. Either fault produces **0.00 on
  every positive with every negative "passing"** — indistinguishable from a
  description that triggers nothing. `docs-system` measured 0/10 that way, then 10/10
  with the description untouched. `scripts/run_trigger_eval.py` patches both in a
  throwaway copy and its docstring carries the detail. So: **don't call the upstream
  runner directly on Windows, and don't simplify the wrapper away** — it looks like a
  pointless indirection until you lose a morning to a clean 0/10.

- **Always use `--num-workers 1`.** Parallel workers each create an identically-
  described command file, all visible to every concurrent query, and detection
  only credits one specific name. A parallel run scored `commit` at 4/9; the
  same eval serially scored 8/9. Parallel results are noise.
- **Run from inside a real git repository.** The harness executes queries with
  `cwd` set to the nearest ancestor containing `.claude/`. If that isn't a git
  repo, every git-scoped skill under-triggers for the wrong reason —
  `"git commit these fixes"` scored 0.00 in a non-git directory and 1.00 in a
  repo with uncommitted changes.

- **Move aside any same-named skill in `~/.claude/skills/` first.** This is the
  easiest one to miss and the most misleading. If a user-scope skill shares the
  plugin skill's name, Claude sees both the real `/open-pr` and the harness stub
  `/open-pr-skill-<uuid>`, picks the real one, and detection credits neither.
  `open-pr` scored 0.00 on every positive until the personal copy was moved
  aside, then 1.00 on all four — the description was never the problem. Note
  `commit` and `branch` were immune only because they'd been renamed away from
  `conventional-*`.

### Why they don't run in CI

**Trigger evals are a local step, and that's a constraint rather than a preference.**
The runner spawns `claude -p` once per query per run, so a full sweep of five skills
at three runs each is roughly 150 API invocations. This repository has no Claude
credentials available to Actions, so there is nothing for the runner to authenticate
with.

Scores also move between runs — `commit` measured 9/9 while `branch` measured 6/8 on
the same harness — so even with credentials a strict threshold would be red on `main`
for reasons that aren't regressions. Any future CI eval should report a baseline
before it gates anything.

What CI covers instead is `scripts/validate_structure.py` — offline, deterministic, no
secrets — checking the structural rules the JSON schema can't express and the loader
accepts silently. Its docstring enumerates them; that list is not repeated here,
because a copy of it in prose is a copy that goes stale. Run it the way CI does:

```bash
python3 scripts/validate_structure.py
```

**Don't build CI tooling for the eval runner.** It needs an Anthropic API key in
repository secrets, this repository has none, and a workflow that can never run is
worse than no workflow — it reads as coverage that doesn't exist. `scripts/run_trigger_eval.py`
is deliberately outside `.github/` for the same reason.

### Writing descriptions that trigger

Measured, not theorized. `commit` scores 9/9 and `branch` scored 4/8 with nearly
identical structure; rewriting `branch` on `commit`'s pattern took it to 6/8.
What moved the number:

- **Lead with the action, not the standard.** "Create a git branch." beats
  "Create a git branch following the Conventional Branch naming convention
  (https://...)" — a URL early in the description dilutes the signal.
- **Pack in literal trigger phrases**, quoted, as early as possible. The exact
  wordings a user would type outperform abstract descriptions of when to apply.
- **State the prohibition explicitly** — "Never run `git checkout -b` directly;
  consult this skill first."

**Position within the phrase list measurably matters.** `reference-doc` listed eight
quoted phrases and scored 8/10: the three that fired were positions 1–3, and both
failures sat at 5–6. Moving the two failures to the front took it to 9/10 —
`"document this pattern in the docs"` went 0/3 to 2/3, and nothing that had been
passing dropped below threshold. Treat the list as ranked, not as a set, and put the
phrasings you most expect a user to type first.

Current scores: `docs-system` 10/10, `reference-doc` 9/10, `commit` 9/9,
`branch` 6/8.

### Known limits

Implicit triggers stay weak. "implement the retry logic" scores 0.00 for
`branch` even after tuning, because the primary intent is writing code and
branching is a secondary inference. Don't over-tune for these; the explicit
cases are what matter.

`open-pr` is trigger-tested like the others. The harness discards
`disable-model-invocation` — it writes only `description:` into a temp command
file — so the run measures the description as if auto-invocation were on. That's
a hypothetical for production, but the negatives still guard a real risk: if
someone forks this and drops the flag, an over-broad description would start
hijacking commit and branch requests.

Behavior evals — does the skill produce correct output — are a separate,
heavier flow needing git fixtures per scenario and grader subagents. Not built
yet.

### Future: `claude plugin eval`

Claude Code ships a first-party eval runner that looks like a better fit for
behavior evals than the skill-creator flow. As of v2.1.220 it is **early access
and undocumented** — invoking it prints "`plugin eval` is currently in early
access", and no page for it exists in the docs index.

Recorded here so the path isn't rediscovered later. **Treat everything below the
CLI flags as inferred** — those field names were read out of the CLI binary, not
a published spec, so their types, defaults, and required-ness are unverified and
may change before release.

Layout: `evals/**/case.yaml`, or `evals/**/prompt.md` plus `graders/*.md`.
`claude plugin eval init` runs an authoring interview; `--bare <name>` writes a
blank template.

Flags (verified from `--help`):

| Flag | Purpose |
| --- | --- |
| `--ablation with-without` | Runs a no-plugin baseline arm, reports the score delta |
| `--scaffold` | Runs each case's `scaffold_script` — author-supplied bash, off by default |
| `--runs <n>` | Per-case runs, default 3 |
| `--judge-model` | LLM-grader model, default haiku |
| `--threshold <0..1>` | Exit non-zero if any case scores below it |
| `--max-cost-usd` | Hard cost ceiling |
| `--report <path>` | Self-contained HTML report |
| `--tag` / `--case` | Filter which cases run |

Case fields (inferred): `schema_version`, `scaffold_script`, `execution.prompt`,
`context.history_file`, `max_turns`, `timeout_seconds`, `agent_timeout_seconds`,
`max_duration_minutes`, `fleet_size`, `precondition_errors`.

Grader types (inferred): `file_exists`, `regex`, `expected`, `tool_used`,
`tool_order`, `baseline`, `diff_files`, `diff_lines`, `max_diff_files`,
`max_diff_lines`.

It closes the two gaps that stopped behavior evals here:

- **`scaffold_script` builds the git fixture per case.** The blocker was that
  each case described a repository state — stale target branch, secrets in the
  diff, a subset deliberately staged — that had to exist before the run.
- **`tool_used` and `tool_order` are programmatic, not model judgments.** They
  would catch the stale-branch defect directly: assert `git fetch origin <target>`
  runs *before* `git log origin/<target>..HEAD`. No LLM grader gives that
  deterministically.
- **`--ablation with-without`** supplies the baseline arm, and `--max-cost-usd`
  bounds a run — both weak points of the skill-creator flow.

**Don't author against it until it leaves early access.** It can't be run to
validate even one case, so any suite written now is guesswork against a schema
that may change.

## Versioning

`version` in `plugin.json` is the update contract. If it is set, users only
receive updates when the string changes; if omitted entirely, Claude Code falls
back to the git commit SHA.

Semantics used here:

- **Patch** — wording changes to a skill body that don't change behavior.
- **Minor** — a new skill, or a materially changed rule.
- **Major** — removing or renaming a skill, or reversing a convention.

A new plugin starts at `0.1.0` when its first skill lands. Don't register a
plugin in `marketplace.json` before it has at least one skill — an empty plugin
validates fine and installs as a silent no-op, which is a worse experience than
not appearing in the catalog at all.

## Relationship to existing personal and project skills

These skills descend from two places:

- `~/.claude/skills/` — `conventional-commit`, `conventional-branch`, and
  `open-pr`, developed as personal skills and copied here.
- `mudflap-android/.claude/skills/` — `commit-generator` and
  `open-pull-request`, whose sequential workflow, review-file step, and
  learnings pattern this marketplace generalizes.

The versions here have been genericized: every Mudflap-specific fact became
runtime discovery or a learnings entry. Universal rules that were living in
Mudflap's `learnings.md` — using rich markdown, never citing internal plan
files — were promoted into the skill bodies, which is where static conventions
belong.

Both ancestor copies still exist. If the plugin is installed at user scope, the
`~/.claude/skills` copies load alongside it under their old names. Retire those
once the plugin versions are proven. Treat this repository as the source of
truth and don't edit the ancestors.
