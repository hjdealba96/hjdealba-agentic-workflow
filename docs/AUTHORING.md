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

  This constrains *bundled* files only. A skill may still read and write paths in
  the repository it's running in — that's exactly what the learnings file and the
  scratch files under `${TMPDIR}` are, and both are resolved at runtime rather
  than shipped.

Supporting files (`reference.md`, `scripts/`) can live alongside `SKILL.md` in
the skill directory and are loaded only when the skill is used — long reference
material costs nothing until then.

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
body — write it under `${TMPDIR:-/tmp}/claude-git-workflow/`, never into the
repository. The user can hand-edit the file, and the skill consumes it with
`git commit -F` or `gh pr create --body-file` so their exact bytes are used.
Keeping it out of the working tree means `git status` stays clean and no
`.gitignore` entry is needed in any consuming project.

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

```bash
cd <a real git repo with a .claude/ directory>
PYTHONPATH=<skill-creator>/skills/skill-creator \
  python3 -m scripts.run_eval \
    --eval-set <skill>/evals/trigger.json \
    --skill-path <skill> \
    --runs-per-query 3 \
    --num-workers 1
```

Two things about the runner that will otherwise cost you hours:

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
