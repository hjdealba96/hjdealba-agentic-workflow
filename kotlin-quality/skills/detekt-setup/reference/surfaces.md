# Surfaces

Where the checks run. All of them read **one config and one set of baselines** — divergence is the
top failure mode, and it shows up as "the IDE says clean, CI is red".

| Surface | Speed | Authority | Needs a manual step |
| --- | --- | --- | --- |
| Android Studio plugin | instant | none | **yes — install the plugin** |
| Pre-commit hook | seconds, changed files | advisory | no |
| CI on pull requests | minutes | **the gate** | no |
| Local full run | minutes | none | no |

Wire them in the order in the skill's Step 6. The ordering matters more than any template: a hook
added before CI is green fails on every developer's first commit and gets deleted permanently.

---

## 1. Local runs

Wrapper scripts named for what they actually do, since the CLI cannot do everything the Gradle side
can:

| Script | Does |
| --- | --- |
| `./detekt-format` | file walk, ktlint config, whole tree |
| `./detekt-format-fix` | same, with `--auto-correct` |
| `./detekt-changed` | staged or changed files only — the hook entry point |
| `./detekt-baseline` | regenerates a baseline, one tier at a time |

The setup script they all source is `templates/detekt-jars.sh`. It reads the pinned versions out
of `gradle/libs.versions.toml` rather than duplicating them, downloads missing jars, and **verifies
SHA-256** before use — those jars execute on every developer machine and in CI, which makes an
unverified one the highest-value supply-chain target in this setup. On a mismatch it deletes the
jar and stops, so a later run cannot skip the download because the file happens to exist.

It falls back between `sha256sum` and `shasum`, and between `curl` and `wget`, so it works on
Linux, macOS, and Windows under Git Bash or WSL. It also exports **`DETEKT_PLUGINS`** — the
joined plugin-jar path, whose separator depends on both the detekt line and the platform. Every
wrapper uses that variable; none of them hardcodes a separator. See `compatibility.md`.

The hook flow is verified end to end **on Linux** with the pre-commit framework: a staged file
with correctable violations is auto-corrected, pre-commit reports `files were modified by this
hook` and blocks the commit, `git status` shows `AM`, and re-adding then committing passes.

**Windows needs a first run to confirm.** `language: script` there depends on Git for Windows
resolving the `#!/usr/bin/env bash` shebang, which is a well-established pattern but not one to
assume. Check the `.gitattributes` LF pinning first: a CRLF hook script is the failure you would
hit.

Each script's `--help` should say what it does *not* cover: the CLI is light-mode, so
type-resolution rules do not run there. See `delivery-modes.md`.

---

## 2. Pre-commit hook

Prefer the pre-commit framework when `.pre-commit-config.yaml` exists, or the user agrees to adopt
it:

```yaml
- repo: local
  hooks:
    - id: detekt
      name: detekt (changed files)
      entry: ./detekt-changed
      files: '\.kts?$'
      language: script
```

The entry script is `templates/detekt-changed.sh`.

**Auto-correct rewrites files without staging them.** Handle it explicitly rather than inheriting
whichever behavior happens to occur:

| Mechanism | Behavior | What to do |
| --- | --- | --- |
| pre-commit framework | run fails with "files were modified by this hook" | correct — the user re-adds and commits again |
| raw `.git/hooks/pre-commit` | files silently modified but not staged | the script must `git add` them, or the commit lands unformatted |

Two things the hook must not pretend:

- it is **not** a preview of CI — type-resolution rules cannot run there, so the failure message
  should say so and stop anyone filing it as a bug
- it should not gate on rules a developer cannot fix in the moment; keep it to the correctable set
  plus PSI rules

---

## 3. GitHub Actions

Template: `templates/detekt-ci.yml`.

Two steps, because they have different capabilities:

```yaml
- name: Correctness (full analysis)
  run: ./gradlew detektDebug            # a typed task → --analysis-mode full automatically
- name: Formatting and PSI rules (whole tree)
  run: ./detekt-format
```

**Name typed tasks explicitly. Never `./gradlew check`.** `check` depends only on the plain
`detekt` task, which runs in light mode, and on a KMP project points at source dirs that don't
exist — measured at 1 of 15 files analyzed, passing. Details in `delivery-modes.md`.

The template also carries:

- **jar cache** keyed on the hash of the setup script, so a version bump invalidates it
- **SARIF upload** so findings annotate the PR diff (`security-events: write`)
- **`concurrency` with `cancel-in-progress`**
- **the baseline guard**, below
- **optional changed-files mode** (`fetch-depth: 0`) when the formatting strategy is the ratchet

### The baseline guard

A baseline is a debt ledger, and `--create-baseline` rewrites it and exits 0 with the violation
still in the source. Suppressing is not fixing, so CI has to notice.

Two diffs, deliberately — one commit-to-commit, one against the working tree, because the first is
blind to an uncommitted rewrite:

```bash
git diff --exit-code "origin/$BASE...HEAD" -- config/detekt/ >/dev/null &&
git diff --exit-code HEAD -- config/detekt/ >/dev/null
```

A legitimate baseline change (a repo-wide format, a newly enabled rule group) then needs an explicit
override in the PR, which is the point.

Counting entries is the cheaper companion check: if the count went up, findings were introduced, not
just re-signed.

---

## 4. Android Studio — and the plugin the user must install

The IDE plugin is the only surface with a manual step, and it is the one that gives feedback while
typing instead of after a push. **Always tell the user to install it**; never report the IDE as
working on the strength of the committed XML.

> Install it: Settings → Plugins → Marketplace → search "detekt" → Install → restart. The committed
> `.idea/detekt.xml` already points it at this project's config and baselines, so there is nothing
> else to configure. Anyone who clones the repo only has to install the plugin.

Then confirm it: ask them to open a file with a known violation and check the underline.

Template: `templates/idea-detekt.xml`. Commit it, with `$PROJECT_DIR$`-relative paths so it is
portable. Note that template uses `{{PLACEHOLDER}}` rather than the angle brackets every other
template uses — a literal `<` is illegal inside an XML attribute value, and the plugin silently
ignores settings it cannot parse:

```xml
<option name="baselinePath" value="$PROJECT_DIR$/config/detekt/baseline.xml" />
<option name="configurationFiles">
  <list><option value="$PROJECT_DIR$/config/detekt/detekt.yml" /></list>
</option>
<option name="enableDetekt" value="true" />
<option name="pluginJars">
  <list><option value="$PROJECT_DIR$/config/detekt/detekt-compose-0.6.4-all.jar" /></list>
</option>
```

Notes:

- The plugin **bundles its own detekt engine**, so it is not a delivery mode. What it needs from you
  is the config, the baseline, and any rule-plugin jars.
- Compose rules require the **uber jar** in `pluginJars` — a different artifact from the Gradle
  coordinate. Without it there are no Compose hints in the editor.
- It offers Refactor → *AutoCorrect by detekt rules*, which is worth mentioning.
- It does not do type resolution the way a typed Gradle task does, so like the hook it is a subset,
  not the gate.
- If `.idea/` is gitignored in this repo, say so and let the user decide: either commit an exception
  for `.idea/detekt.xml` or accept that every developer configures the plugin by hand.
