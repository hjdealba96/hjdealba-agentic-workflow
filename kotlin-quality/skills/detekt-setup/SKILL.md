---
name: detekt-setup
description: >
  Set up detekt static analysis in a Kotlin, Android, or Kotlin Multiplatform project. Use this
  skill whenever the user asks to "set up detekt", "add detekt", "add static analysis", "add a
  Kotlin linter", "set up code quality checks", "add ktlint", "add a detekt pre-commit hook",
  "run detekt in CI", "lint our Compose code", or asks how to adopt detekt in an existing
  codebase. Handles two cases only: a brand-new project, and staged adoption into a mature one
  (baseline plus ratchet). Wires the Android Studio plugin, a pre-commit hook, and a GitHub
  Actions gate to one shared config, and pins a compatible detekt / compose-rules / Kotlin
  version set. Never hand-write a `detekt.yml`, a Gradle `detekt {}` block, a detekt CI workflow,
  or a detekt git hook without consulting this skill first. Not for tuning an existing detekt
  setup or fixing violations at scale — for a repository that already has detekt it reports the
  gaps and stops.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch
---

# Set Up detekt

Stand up [detekt](https://detekt.dev) in a Kotlin, Android, or Kotlin Multiplatform repository:
one config, one set of baselines, and the same rules enforced in the IDE, in a pre-commit hook,
and in CI.

**Scope is deliberately narrow.** This skill does initial setup — a new project, or first-time
adoption into an existing codebase. It does not tune, migrate, or refactor an existing detekt
installation. When it finds one, it audits and stops (Step 1).

---

## Step 0: Load Project Learnings

Read `.claude/learnings/kotlin-quality/detekt-setup.md` from the repository root if it exists.

It holds facts unique to **this repository** — the delivery mode chosen, the pinned version set,
config and baseline paths, rule deviations, and how far adoption has progressed. On a resumed
adoption this is what tells you to continue rather than start over.

**If the file does not exist, proceed with defaults. Do not create it.** It is written only when
a learning is captured (see [Capturing Learnings](#capturing-learnings)).

---

## What detekt does and does not cover

State this early, because the boundary is not obvious and silence about it reads as coverage.

| Covered | Not covered |
| --- | --- |
| `**/*.kt` and `**/*.kts` — every Kotlin source set, build scripts included | XML: layouts, drawables, resources, `AndroidManifest.xml` |
| Legacy View-system Kotlin (Activities, Fragments, custom Views) | View-specific bug classes — binding leaks, `findViewById` nullability |
| Compose and Compose Multiplatform, via a rule plugin | Test coverage or test presence — no rule can assert "this class has a test" |

detekt's file includes are literally `**/*.kt` and `**/*.kts`. Nothing configures XML in. If the
survey reports a large `xml_files` count, say so in the report and name Android Lint as the tool
for it — then stay out of it.

---

## Workflow

### Step 1: Survey the repository, and classify

Run the bundled survey. It is read-only and offline:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/detekt-setup/scripts/survey.sh
```

One run feeds every later step: scale to the scenario, infrastructure to the delivery mode,
toolchain and project shape to the version set and the config.

**Do not hand-roll these counts.** The script exists because each of them was wrong on the first
attempt against a real repository — counting `include` lines read a 5-module project as 1,
`xargs wc -l | tail -1` read 215k lines as 13k, `git ls-files` returned nothing in a repo with no
commits, and a vendored dependency's `CompositionLocal`s were proposed as the project's own.

Classify from `detekt_config`, `detekt_baseline`, and `detekt_in_build`:

| State | Signal | Path |
| --- | --- | --- |
| **Greenfield** | no detekt anywhere, small or new codebase | Steps 2–8. **No baseline file, ever** |
| **Adopt** | no detekt, mature codebase | Steps 2–8 with the staged plan in Step 6 |
| **Already set up** | any detekt config, baseline, or build reference | **Step 1a, then stop** |

### Step 1a: Existing setup — audit and stop

Do not restructure, retune, or "improve" an existing installation. Report against the surface
matrix in `${CLAUDE_PLUGIN_ROOT}/skills/detekt-setup/reference/surfaces.md`, covering:

- which surfaces exist (IDE settings, hook, CI) and which don't
- whether CI invokes typed tasks or only the plain `detekt` task
- whether type resolution is actually on (see `reference/delivery-modes.md`)
- whether the baseline is guarded against silent regeneration
- source sets the config's excludes miss
- what the config covers that detekt cannot (XML)

Present it in chat first — that is usually all anyone wants. Offer to write it to a file, and on
approval put it in the working-notes tier (`docs/notes/detekt-audit-<YYYY-MM-DD>.md`) if the repo
has a docs tree, otherwise `DETEKT_AUDIT.md` at the root. Never overwrite an existing file at that
path without asking. This is a point-in-time audit, not a standing convention, so it does **not**
belong in `docs/reference/`.

Then stop. If the user wants the gaps filled, that is a new, explicit request.

### Step 2: Resolve the compatibility set

detekt versions are a coherent **set**, never latest-of-each: the detekt line fixes the plugin id,
the ktlint artifact name, the config schema, and the compose-rules version that will work with it.

Read `${CLAUDE_PLUGIN_ROOT}/skills/detekt-setup/reference/compatibility.md` and match the
survey's `catalog_kotlin`, `gradle_wrapper`, and `java_version`.

Refresh the numbers rather than trusting the table's age:

```bash
curl -s "https://api.github.com/repos/detekt/detekt/releases?per_page=8" | grep -E '"tag_name"|"prerelease"'
curl -s "https://api.github.com/repos/mrmans0n/compose-rules/releases?per_page=3" | grep '"tag_name"'
```

Prefer the newest **stable** line whose bundled Kotlin can parse the project's syntax. Where the
project's Kotlin is newer than any stable detekt bundles, say so plainly and present the
pre-release as a considered choice, not a default. Confirm the set with the user before writing
anything.

### Step 3: Choose the delivery mode

Read `${CLAUDE_PLUGIN_ROOT}/skills/detekt-setup/reference/delivery-modes.md` for the profiles.
Resolve with this ladder, stopping at the first match:

| # | Condition (from the survey) | Propose |
| --- | --- | --- |
| 1 | `precommit_config=yes` | **Hybrid** — the framework is already maintained; a hook is one entry |
| 2 | `gh_workflows=0` and `gradle_modules<=1` and `authors_12mo<=2` | **Gradle plugin only** — a hook isn't worth wiring yet |
| 3 | `gh_workflows>=1` and (`tracked_shell_scripts>=1` or `convention_plugins=yes` or `authors_12mo>=5`) | **Hybrid** — this repo demonstrably maintains tooling |
| 4 | `gh_workflows>=1`, otherwise | **Gradle plugin only**, CI as the single gate; offer the hook later |
| 5 | `commits=0` | **Gradle plugin only** for now; the hook is a Step 6 decision, not a day-one one |

Present the evidence, the recommendation, and the one assumption the survey cannot see:

> 13 modules, 348 Kotlin files (~43k LOC), 6 authors in the last year, 4 workflows, no pre-commit
> config. I'd go hybrid: Gradle plugin for CI and local runs, CLI jars for a pre-commit hook and
> the IDE plugin. That assumes someone will keep a ~40-line setup script alive — if not, say so
> and I'll do Gradle-only with CI as the single gate.

Gradle-only is never a dead end; the CLI half is additive later.

**Never infer that coverage doesn't matter.** CLI-only, which silently disables every
type-resolution rule, is only correct if the user says so out loud.

### Step 4: Present the plan, then write

This skill writes tracked files reviewable with `git diff` and revertible with `git checkout`, so
the plan **is** the review step — there are no scratch files. List every path you intend to create
or modify, and what each is for, before touching anything. Get approval.

Two items need their own approval because they change files you don't otherwise own:

- a `.gitignore` entry, if the CLI mode is chosen (the jars are large — see `reference/delivery-modes.md`)
- any edit to an existing `build.gradle.kts`, `.pre-commit-config.yaml`, or workflow

If the user declines the `.gitignore` entry, state the consequence — the jars become committable —
and continue. It is a suggestion, not a gate.

### Step 5: Write the config

Build it from `${CLAUDE_PLUGIN_ROOT}/skills/detekt-setup/reference/rule-layers.md`, plus
`${CLAUDE_PLUGIN_ROOT}/skills/detekt-setup/reference/compose-rules.md` when `compose=yes`.

Always `buildUponDefaultConfig: true`; **never** `allRules: true`. Write deltas from the default
config, not a copy of it.

Fill in the values the survey discovered rather than guessing them — `preview_aliases`,
`composition_locals`, `ticket_prefix`, `di_koin` / `di_hilt`, `generated_dirs`, `vendored_dirs`,
`source_sets`. Show each proposed value next to where it came from, since a wrong one here is
invisible later.

Two config-shape rules that are load-bearing:

- **Test paths go in one anchored list**, registered in `config.excludes`. A per-rule `excludes`
  list **replaces** the default rather than merging with it, so patching one rule with one path
  silently drops the other eight. `reference/rule-layers.md` has the verified form.
- **Split the config by tier** when the project is KMP: correctness on the typed tasks, formatting
  on a path-based pass. `reference/delivery-modes.md` explains why, and it needs separate baseline
  files so regenerating one can't disturb the other.

### Step 6: Wire the surfaces, in this order

Order matters more than any individual template. Details and copy-ready files are in
`${CLAUDE_PLUGIN_ROOT}/skills/detekt-setup/reference/surfaces.md`.

1. **A local run that works.** Nothing else is worth wiring until someone can run it by hand.
2. **Measure.** Run it and count findings by rule. This number decides Step 6a, and it replaces
   guessing from lines of code.
3. **CI, advisory.** One iteration non-blocking, so the first red build isn't a surprise.
4. **Baseline** — adopt path only. Generate it with the *full* intended rule set so the ledger is
   complete from the start. Greenfield: skip this entirely; an absent baseline is the feature.
5. **CI, blocking.** The ratchet is now live. Include the baseline guard.
6. **The pre-commit hook** — last. Before CI is green, every developer's first commit fails and
   the hook gets deleted permanently.
7. **The IDE.** Commit `.idea/detekt.xml` pointing at the same config, baselines, and rule jars,
   and **tell the user to install the plugin** — it is the only surface that needs a manual action:

   > Install the detekt plugin in Android Studio: Settings → Plugins → Marketplace → search
   > "detekt" → Install, then restart. The committed `.idea/detekt.xml` already points it at this
   > project's config, so there's nothing else to configure — you'll get warnings inline while
   > typing instead of waiting for CI. Anyone else who clones the repo only has to install the
   > plugin too.

### Step 6a: Stage the formatting tier by measurement

Formatting is the one tier where most findings are fixable by machine, so the decision is how to
land a wide diff — not whether to suppress it. Split the measured findings using the
non-auto-correctable list in `reference/rule-layers.md`, then:

| Condition | Approach |
| --- | --- |
| correctable ≲ 200 | one mechanical commit; no formatting baseline at all |
| correctable large, `open_prs` ≲ 5 | one coordinated repo-wide commit, plus `.git-blame-ignore-revs` |
| correctable large, `open_prs` high or continuous | stage by rule group, or enforce on changed files only |
| non-correctable > 0 | **baseline exactly those rules** — they need a human |

Auto-correct **first**, then regenerate the baseline. Reformatting shifts finding signatures, so
the reverse order produces a baseline that matches nothing.

These thresholds are defaults to show the user, not laws. Say which branch you picked and why.

### Step 7: Verify — run it, and prove it ran

Run this. Do not skip lines and do not assert results. Every line prints its own exit code, so a
missing line is a command that wasn't run.

Compose the block from what Step 1 found and Step 6 wired — the probe file goes in a source
directory that exists, the task name matches the project type, the hook command is whatever was
installed:

```bash
echo "head=$(git rev-parse --short HEAD) dirty=$(git status --porcelain | wc -l | tr -d ' ')"
<full-run command>;            echo "clean_run=$?"        # expect 0
echo "files_analyzed=<from the run's Project Statistics>"
echo "files_tracked=$(git ls-files '*.kt' '*.kts' | wc -l | tr -d ' ')"
probe=<an existing source dir>/DetektProbe.kt
printf 'package probe\n\nclass DetektProbe { fun f(s: String) = s?.length }\n' > "$probe"
<full-run command>;            echo "probe_caught=$?"     # MUST be non-zero
<hook command> "$probe";       echo "hook_caught=$?"      # MUST be non-zero
rm -f "$probe"
test -z "$(git status --porcelain)"; echo "tree_clean=$?" # expect 0
```

**The inverted assertions are the point.** `clean_run=0` on its own is also what you get from a
config that analyzes nothing — and that is not hypothetical:

- In a KMP module the plain `detekt` task's default source dirs (`src/main/kotlin`, `src/test/kotlin`)
  match nothing, because sources live in `src/commonMain/kotlin` and friends.
- `check` depends only on that plain task, so `./gradlew check` can pass having analyzed nothing.
- An over-broad `excludes` glob produces the same green.

`files_analyzed` must equal `files_tracked` minus what you deliberately excluded. Enable
`ProjectStatisticsReport` in `console-reports` to get the count — it is excluded by default.

Also verify, per surface:

- **Test source sets**: plant a violation in each one the survey listed and confirm the exemptions
  match what the config intends. A wrong exclude list doesn't error, it moves the boundary.
- **Both runners agree**, on the hybrid: run each over the same file and diff the finding IDs.
  Equal versions should give equal baseline signatures. Should is not does.
- **The IDE**: cannot be automated. Ask the user to open a file with a known violation and confirm
  the underline. Do not report the IDE as working on the strength of the committed XML.

Report the lines verbatim. Never paraphrase them as "verified".

### Step 8: Report and capture

State what was created, what the numbers were, which strategy branch was taken and why, what the
user must still do by hand (install the IDE plugin; run the mechanical format commit), and what is
**not** covered — XML, native-target type resolution, test presence.

Then offer to record the setup profile (see below).

---

## Capturing Learnings

The conventions above are global. **The learnings file is only for facts specific to one
repository.**

| Correction | Durable repo fact? |
| --- | --- |
| "We use the vendored CLI here, not the Gradle plugin" | Yes — part of `## Setup Profile` |
| "Pin detekt in `libs.versions.toml`, not the script" | Yes — part of `## Setup Profile` |
| "Our TODO prefix is `DRX`" | Yes — repository convention |
| "`**/legacy/**` is exempt from complexity rules" | Yes — repository convention |
| "We accept that CLI-only skips type-resolution rules" | Yes — record it, or someone will later believe those rules run |
| "Tier 3 is enabled through `style`, Compose is next" | Yes — adoption stage, so a resumed run continues |
| "Use 140 columns instead of 130" | Yes — repository convention |
| "Don't bother with the HTML report this time" | No — one-off |

**Keep the mode, versions, paths, and stage in a single `## Setup Profile` entry.** A pinned
version recorded separately from the delivery mode that implies it is how the file starts
contradicting itself.

Propose, never assume:

```
That looks repo-specific. Save it to .claude/learnings/kotlin-quality/detekt-setup.md?

  ## Setup Profile
  **Mode:** Hybrid — Gradle plugin for CI and local runs, vendored CLI jars for the
  pre-commit hook and the IDE plugin.
  **Versions:** detekt 1.23.8, compose-rules 0.4.28, pinned in gradle/libs.versions.toml
  and read by config/detekt/detekt-setup.sh.
  **Paths:** config/detekt/detekt.yml, baseline.xml, baseline-formatting.xml
  **Stage:** Tiers 1 and 2 blocking in CI; Tier 3 Compose rules not yet enabled.
  **Why:** 13 modules and an existing pre-commit framework; CI needs type resolution
  that the CLI cannot supply.

Save? (yes / no / edit)
```

**Append only on approval.** Create `.claude/learnings/kotlin-quality/` and the file if needed,
with this header:

```md
# Learnings — `/kotlin-quality:detekt-setup`

Repository-specific patterns for the `detekt-setup` skill. The skill reads this file before
proposing a setup. Universal detekt conventions live in the skill itself; only facts unique to
this repository belong here.

---
```

Entries are a `##` title then `**Rule:**` and `**Why:**`. A new learning that contradicts an
existing one updates that entry instead of appending a duplicate.

---

## Error Handling

| Failure | Action |
| --- | --- |
| Not a Kotlin project (`kt_files=0`) | Stop and say so. Nothing to analyze |
| `detekt_config` or `detekt_in_build` non-empty | Step 1a audit, then stop. Do not retune |
| Project's Kotlin is newer than any stable detekt bundles | Present both options with the tradeoff; never silently pick the pre-release |
| Jar checksum mismatch | Delete the jar and stop. Never proceed with an unverified jar — it executes on every machine and in CI |
| Config validation fails on an unknown key | detekt hard-fails, it does not warn. Fix the key; if it's a custom anchor, register it in `config.excludes` |
| A rule name from a newer plugin version doesn't exist | Same hard failure. Check the rule list in the actual jar, not the docs |
| Baseline has no effect after a detekt major upgrade | Expected — signature format changes between major versions. Regenerate in an isolated commit and compare entry counts |
| `clean_run=0` but `files_analyzed` is 0 or low | The config is analyzing nothing. Check KMP source dirs and the excludes globs before believing any green result |
| `probe_caught=0` | The analysis is not reaching your code. Every other green line was measuring nothing |
| Findings on `commonMain` appear N times | Expected on KMP if Compose or correctness rules run on every target task. Pick one canonical typed task |
| `open_prs=unknown` | `gh` is missing or unauthenticated. Ask the user for a rough count before choosing a formatting strategy |
| Auto-correct leaves files unstaged in the hook | Expected under the pre-commit framework — it fails and the user re-adds. With a raw hook you must `git add` them |
| No `sha256sum` on the machine | macOS ships only `shasum`. `templates/detekt-jars.sh` handles both; never skip verification |

---

## Platform notes

The scripts are bash and run on Linux, macOS, and Windows under Git Bash or WSL. A mixed
Windows/Linux team hits these first:

- **CRLF does not produce findings.** A CRLF file and an identical LF file yield the same
  results — no line-ending rule fires either way.
- **`--auto-correct` preserves the file's existing line endings.** A CRLF file with ten
  correctable violations was rewritten to zero findings and stayed CRLF on every line. So
  running the mechanical format pass from Windows will not generate a repo-wide
  line-ending diff.
- **`--plugins` has no portable form** — the separator depends on both the detekt line and the
  platform, measured across all four combinations. Never hardcode it; use the `DETEKT_PLUGINS`
  that `templates/detekt-jars.sh` assembles. Full matrix in `reference/compatibility.md`.
- **The survey is I/O-bound.** It reads the whole tree, so on a local disk it finishes in
  well under a second even on a few thousand files, while a network share or a translated
  filesystem — a Linux VM reading a mounted host drive, for instance — can stretch the same
  work into minutes. If it is slow, that is the filesystem rather than the script: say so,
  and offer to run it from the host instead.

**Pin the wrapper scripts to LF.** This is the one cross-platform hazard that actually bites, and
it bites in the direction people don't expect: Git Bash executes a script with a CRLF shebang
fine, but Linux does not — `/usr/bin/env: 'bash\r': No such file or directory`. So a hook script
committed with CRLF from a Windows machine works locally and breaks CI.

When you write any wrapper script, check for a `.gitattributes` entry covering it and propose one
if absent — same approval protocol as the `.gitignore` entry:

```gitattributes
*.sh            text eol=lf
detekt-format   text eol=lf
detekt-changed  text eol=lf
detekt-baseline text eol=lf
```

The extensionless wrappers need naming explicitly; `*.sh` does not cover them.

What else needs care:

| Concern | Handling |
| --- | --- |
| `sha256sum` vs `shasum` | `templates/detekt-jars.sh` tries both |
| `curl` vs `wget` | same template tries both |
| Repo paths containing spaces | every path in `survey.sh` is quoted; verified against a real path with a space in it |
| `wc` output padding | piped through `tr -d ' '` — unpadded on Linux, padded on some platforms |
| Git's own CRLF conversion | orthogonal to detekt, but if the repo pins LF via `.gitattributes`, pass `--ignore-cr-at-eol` to git commands so conversion churn isn't read as a real change |
