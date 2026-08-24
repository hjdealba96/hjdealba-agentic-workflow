# Compatibility sets

detekt versions come as a **set**, never latest-of-each. The detekt line fixes the plugin id, the
ktlint artifact name, the config schema, the CLI flags, the baseline signature format, and which
compose-rules version will load at all.

Measured 2026-08. **Re-check before using — this table ages.**

```bash
curl -s "https://api.github.com/repos/detekt/detekt/releases?per_page=8" | grep -E '"tag_name"|"prerelease"'
curl -s "https://api.github.com/repos/mrmans0n/compose-rules/releases?per_page=3" | grep '"tag_name"'
```

## The two lines

| | Stable | Pre-release |
| --- | --- | --- |
| detekt | **1.23.8** (Feb 2025) | **2.0.0-alpha.x** |
| Gradle plugin id | `io.gitlab.arturbosch.detekt` | `dev.detekt` |
| Bundled Kotlin (the parser) | 2.0.21 | 2.4.10 at alpha.6 |
| ktlint ruleset artifact | `detekt-formatting` | `detekt-rules-ktlint-wrapper` |
| ktlint ruleset **config key** | `formatting:` | `ktlint:` |
| Code style setting | `android: true` (boolean) | `code_style:` string |
| Floors | — | Gradle 9.5+, JDK 21+ |
| compose-rules | **0.4.x only** | 0.5.0+ |

**Trap: `detekt.dev/docs` serves the 2.x docs by default.** Read the intro page while setting up a
1.23.8 project and you get `dev.detekt`, `detektGenerateConfig`, and the renamed ktlint artifact —
none of which exist on the stable line. Use the version-pinned URLs (`/docs/1.23.8/...`).

## Picking the set

The binding constraint is the **parser**: detekt analyzes with its own bundled Kotlin, so a project
on Kotlin 2.4 analyzed by a detekt that bundles 2.0.21 is parsing newer syntax with an older
parser.

1. Prefer the newest **stable** line whose bundled Kotlin covers the project's `catalog_kotlin`.
2. If the project's Kotlin is newer than any stable detekt bundles, present both options with the
   tradeoff. Never silently pick a pre-release.
3. Check the floors: the pre-release line needs Gradle 9.5+ and JDK 21+.
4. Pick the compose-rules version from *its* matrix, which is keyed to the detekt version, not to
   Kotlin: <https://mrmans0n.github.io/compose-rules/detekt/>

**A greenfield project can take the pre-release far more cheaply than a mature one**, because the
expensive part of a major upgrade is the baseline (below), and greenfield has none.

## Schema deltas, 1.23.8 → 2.0.0-alpha

| 1.23.8 | 2.0.0-alpha |
| --- | --- |
| `formatting:` ruleset | `ktlint:` ruleset |
| `formatting.android: true` | `ktlint.code_style:` — `intellij_idea` \| `android_studio` \| `ktlint_official` \| `android` |
| `FindingsReport`, `FileBasedFindingsReport`, `LiteFindingsReport` | `IssuesReport`, `FileBasedIssuesReport`, `LiteIssuesReport` |
| `ProjectComplexityProcessor`, `DetektProgressListener` | `ProjectCyclomaticComplexityProcessor`; no progress listener |
| — | `config.checkExhaustiveness` |
| `@RequiresTypeResolution` (annotation) | `RequiresAnalysisApi` (marker interface) |

`ktlint_official` is only reachable on the 2.x line; 1.23.8's boolean toggles between
`android_studio` and `intellij_idea` only.

## `--plugins` has no portable form

The CLI's separator for plugin jars differs by **both** detekt line and platform. Every cell below
was run — two plugin jars, one probe file, 8 findings when the jars load. The control for "did they
really load" is omitting `--plugins` entirely, which makes the ruleset key hard-fail.

| Form | 1.23.8 Windows | 1.23.8 Linux | 2.0.0-alpha.6 Windows | 2.0.0-alpha.6 Linux |
| --- | --- | --- | --- | --- |
| `a,b` | **8** | **8** | `does not exist` | `does not exist` |
| `a;b` | **8** | **8** | **8** | `does not exist` |
| `a:b` | `InvalidPathException` | `does not exist` | usage / parse error | **8** |
| `-p a -p b` | usage / parse error | usage / parse error | **8** | **8** |

So there is no form that works in all four cells:

- **1.23.x** takes `,` (or `;`) on both platforms — its help says *"separated by ',' or ';'"* with no
  platform qualifier, and both were measured.
- **2.x** takes the **platform path separator** — `;` on Windows, `:` elsewhere — or a repeated flag.
  `,` is read as a single path.

The reason the platform matters is Windows drive letters: `C:\jars\a.jar` already contains a colon,
so `:` can't separate paths there. On 1.23.8 Windows a colon fails with
`InvalidPathException: Illegal char <:>` rather than a friendly message, but it does exit 1 — loudly,
not silently.

Assemble the joined string once from the version and `uname`, and export it. That is what
`templates/detekt-jars.sh` does as `DETEKT_PLUGINS`; no wrapper hardcodes a separator.

## Two changes that break silently

### 1. Type resolution became opt-in on the CLI

detekt 2.x added `--analysis-mode`, defaulting to `light`. In light mode the rules that need
compiler information **do not run at all** — no warning, exit 0.

Verified on a synthetic file with three type-resolution rules:

| Invocation | Findings |
| --- | --- |
| `--classpath <jar>` alone | **0** |
| `--classpath <jar> --analysis-mode full --jvm-target 17` | **3** |

So a 1.x CLI invocation carried into 2.x unchanged keeps working and quietly loses every
type-resolution rule. On 1.23.8, supplying a classpath was sufficient.

`--jvm-target` defaults to **1.8** even in full mode — set it to the project's real target.

The **Gradle plugin handles this itself**: `ClasspathArgument` appends `--analysis-mode full`
whenever the classpath is non-empty. Typed tasks therefore get full analysis automatically, and
the plain `detekt` task (empty classpath) does not.

### 2. Baseline signatures change between major versions

```
1.23.8         ComposableParamOrder:AnimatedFill.kt$AnimatedFill
2.0.0-alpha.6  ComposableParamOrder:AnimatedFill.kt:@Composable fun AnimatedFill
```

The separator changed from `$` to `:` and the entity signature now carries annotations and the
`fun` keyword. Passing a 1,261-entry 1.23.8 baseline to a 2.x run had **zero effect** — every
finding reappeared.

So a major upgrade invalidates the whole baseline. Handle it deliberately:

1. Regenerate in a commit that changes **nothing else**.
2. Compare entry counts before and after. Higher means findings were introduced during the
   migration, not merely re-signed.
3. Expect newly-strict rules on top: rule sets broaden between versions, so some of the increase
   is real rather than a format artifact.

## Config validation is strict, which helps

detekt rejects unknown config keys as a **hard failure**, not a warning:

```
Property 'test_paths' is misspelled or does not exist. Allowed properties: [...]
Run failed with 1 invalid config property.
```

Consequences worth planning for:

- A typo'd rule name cannot silently do nothing. Good.
- A rule removed in a newer plugin version breaks the run until the key is deleted. `Material2`
  disappeared from compose-rules 0.6.x, so a config carrying `Material2: active: false` fails
  outright after that upgrade.
- A deliberate custom top-level key — a YAML anchor for shared lists — must be registered in
  `config.excludes` or the run fails.

## Verifying a set before committing to it

The jars are self-describing, and cheaper to consult than the docs:

```bash
java -jar detekt-cli-<v>-all.jar --version
java -jar detekt-cli-<v>-all.jar --generate-config out.yml   # takes the path POSITIONALLY;
                                                             # `--generate-config --config x.yml`
                                                             # writes a file named "--config"
unzip -p <plugin>.jar config/config.yml | head -40           # a rule plugin's real rule list
```
