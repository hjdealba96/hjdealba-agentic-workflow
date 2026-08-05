# Evaluating skills in this marketplace

Skills are prompts. They fail silently and drift without warning, so the only way
to know one still works is to run it.

Two kinds of eval, answering different questions:

| Kind | Question | State |
| --- | --- | --- |
| **Trigger** | Does the description load the skill at the right moment, and leave it alone otherwise? | Working, run manually |
| **Behavior** | Is what the skill produces correct? | Method established, no scripted suite |

Neither runs in CI, and that is a constraint rather than a preference -- see
[Why they don't run in CI](#why-they-dont-run-in-ci). Authoring conventions live in
[`AUTHORING.md`](./AUTHORING.md).

## Trigger evals

Trigger eval sets live at `<plugin>/skills/<skill>/evals/trigger.json` and answer one
question: does the description cause Claude to load the skill when it should, and
leave it alone when it shouldn't?

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

## Running them

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

## Why they don't run in CI

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

## Writing descriptions that trigger

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

## Known limits

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

## Behavior evals

**Trigger evals only measure whether a skill loads.** Nothing above says the output is
any good, and those are separate failure modes — a body can say "triage first" and the
model can still go straight to writing what was asked for.

There is no scripted suite yet, but the method is worked out and two of its constraints
are worth not rediscovering:

- **`claude plugin eval` is still gated.** `--help` is fully populated with real flags,
  which reads as shipped, but `plugin eval init --bare` and a real run both print
  ``plugin eval` is currently in early access` and do nothing.
- **Plugin skills do not execute under `claude -p`.** The `Skill` tool returns
  `<error>Execute skill: <plugin>:<name></error>`. Measured across three at once —
  `docs-workflow:docs-system`, `docs-workflow:reference-doc`, and the long-shipping
  `git-workflow:branch` — all failed identically, so this is the harness, not the
  plugin. They resolve by name and fail at invocation.

The workaround is the one the trigger-eval harness already relies on: **write the skill
body into the fixture's `.claude/commands/<name>.md`.** Project commands *do* execute
under `-p`. One adjustment is required — `${CLAUDE_PLUGIN_ROOT}` does not substitute for
a project command, so replace it with a real path first, and prefer copying the bundled
reference files into the fixture. A path outside the working directory is blocked by the
sandbox, which produces a confound that looks like a skill defect.

Then run with `--permission-mode acceptEdits` so writes actually land, and assert on the
filesystem afterwards.

**Prefer mechanically falsifiable assertions.** "Never reformats an existing file" is
checkable with `sha256sum` before and after; whether a gap report is *insightful* is not.
The checksum case caught nothing, which is the point — it can only be passed honestly.

This flow found one real defect on its first run. `docs-system` was told to copy the
bundled template "unmodified" and had no instruction for the case where the read fails,
so it authored a replacement: 69 lines against the real file's 97, a third of the guidance
silently gone, flagged only in prose that a reader may skip. Both skills now stop instead.
**Any instruction to copy a bundled file needs an explicit failure branch**, or the model
will helpfully invent the contents.

## Future: `claude plugin eval`

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
