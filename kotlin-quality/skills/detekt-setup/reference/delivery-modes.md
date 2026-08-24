# Delivery modes

How detekt is obtained and executed. This is a separate axis from *where* checks run (IDE, hook,
CI) — every mode can feed every surface, which is why the two get confused.

## The deciding fact: type resolution

34% of detekt's rules need the compilation classpath. Measured on 1.23.8 by counting
`@RequiresTypeResolution` across the rule sources — 69 of 205 rule files:

| Rule set | Requires type resolution |
| --- | --- |
| `coroutines` | **6 of 7** |
| `potential-bugs` | **23 of 38** |
| `style` | 28 |
| `performance` | 2 of 6 |
| `exceptions` | 2 of 14 |
| `complexity`, `naming`, `libraries` | 7 combined |

Named examples: `InjectDispatcher`, `SleepInsteadOfDelay`, `SuspendFunSwallowedCancellation`,
`MissingWhenCase`, `ElseCaseInsteadOfExhaustiveWhen`, `UnsafeCallOnNullableType`,
`UnnecessarySafeCall`, `CanBeNonNullable`, `VarCouldBeVal`.

Without a classpath these rules are **skipped silently**. A config with `coroutines: active: true`
and no classpath reports success having run one of seven coroutines rules.

On 2.x the marker is the interface `RequiresAnalysisApi`, and the CLI additionally needs
`--analysis-mode full`. See `compatibility.md`.

---

## Profile A: Gradle plugin

```kotlin
plugins { id("io.gitlab.arturbosch.detekt") version "<v>" }   // 1.23.8
// plugins { id("dev.detekt") version "<v>" }                  // 2.x

detekt {
    buildUponDefaultConfig = true
    config.setFrom("$rootDir/config/detekt/detekt.yml")
    baseline = file("$rootDir/config/detekt/baseline.xml")
    parallel = true
    basePath = rootDir.path        // stable, readable paths in reports
}
dependencies {
    detektPlugins("io.gitlab.arturbosch.detekt:detekt-formatting:<v>")
    detektPlugins("io.nlopez.compose.rules:detekt:<v>")
}
```

Applied **per module** — use a convention plugin in anything non-trivial.

### Task names

| Project | Typed tasks (full analysis) | Untyped |
| --- | --- | --- |
| JVM | `detektMain`, `detektTest` | `detekt` |
| Android | `detekt<Variant>`, plus one per test variant — `detektDebugUnitTest`, `detektDebugAndroidTest` | `detekt` |
| KMP | `detekt<Target><Compilation>` — `detektJvmMain`, `detektAndroidDebug`, `detektIosArm64Main` | `detekt<SourceSet>SourceSet` |

Android registers tasks for **both** test variants — `testVariants = listOfNotNull(testVariant, unitTestVariant)`
— so instrumented test sources are analyzed with no emulator involved.

### Three traps, all verified

**1. `check` pulls only the weak task.** The plugin wires `check → detekt` (the plain, untyped
one) and nothing else. `detektMain`, `detekt<Variant>`, and the KMP tasks are never in `check`. So
`./gradlew check` runs light-mode analysis, and CI must name typed tasks explicitly.

**2. In a KMP module the plain task's source dirs don't exist.** The defaults are
`src/main/java`, `src/test/java`, `src/main/kotlin`, `src/test/kotlin`. KMP sources live in
`src/commonMain/kotlin`, `src/androidMain/kotlin`, `src/iosMain/kotlin`. Zero overlap.

Measured on a real CMP project — 2 modules, 15 Kotlin files:

| Input | Files analyzed | Findings |
| --- | --- | --- |
| Gradle default source dirs | **1 of 15** | 1 |
| Whole-tree file walk | **15 of 15** | 42 |

Combined with trap 1: `./gradlew check` on a KMP project can pass having analyzed 7% of it.

**3. `commonMain` is analyzed once per target.** Tasks are registered per target × compilation
with `compilation.kotlinSourceSets` as input, and `commonMain` belongs to every target's main
compilation. On android + jvm + three iOS targets, one `commonMain` finding is reported five
times. The baseline dedupes it; console output and PR annotations do not.

**Fix: designate one canonical typed task per module** for the type-resolution tiers —
`detektDebug` on Android, `detektJvmMain` on a KMP module. Any single JVM/Android compilation
covers `commonMain`.

### Whole-tree aggregate task

`Detekt` extends Gradle's `SourceTask` on both lines, so it accepts an arbitrary file tree. This is
how you cover every Kotlin file regardless of source-set naming:

```kotlin
import io.gitlab.arturbosch.detekt.Detekt          // 1.23.8
// import dev.detekt.gradle.Detekt                  // 2.x

val detektFormatting by tasks.registering(Detekt::class) {
    description = "ktlint formatting over every Kotlin file in the repository"
    parallel = true
    buildUponDefaultConfig = true
    config.setFrom(files("$rootDir/config/detekt/detekt-formatting.yml"))
    baseline.set(file("$rootDir/config/detekt/baseline-formatting.xml"))
    setSource(files(rootDir))                       // a file walk, not a source set
    include("**/*.kt", "**/*.kts")
    exclude("**/build/**", "**/generated/**", "**/composeResources/**", "**/.gradle/**")
    autoCorrect = false                             // true in a sibling `...Fix` task
    reports { html.required.set(true); sarif.required.set(true) }
}
```

Reaches what per-target tasks miss: every KMP source set, every test source set, `buildSrc/` and
`build-logic/` (separate Gradle builds), root `*.gradle.kts`, and **modules that never applied the
plugin** — the row that matters most, since a module added later is otherwise silently uncovered.

---

## Profile B: Standalone CLI

```bash
java -jar "$DETEKT_JAR" \
  --input . \
  --build-upon-default-config \
  --config config/detekt/detekt-formatting.yml \
  --baseline config/detekt/baseline-formatting.xml \
  --plugins "$KTLINT_JAR,$COMPOSE_JAR" \
  --excludes "**/build/**,**/generated/**" \
  --parallel
```

Knows nothing about the build. Two things only it can do:

- **`--input file1.kt,file2.kt`** — per-file analysis, which is what makes a sub-second pre-commit
  hook possible.
- **One pass over the whole tree**, independent of Gradle, AGP, and module wiring.

What it costs: no classpath, so no type resolution unless you supply one — and computing a correct
classpath for a multi-module Android/KMP build in a shell script means asking Gradle for it anyway.
Treat the CLI as owning formatting and PSI-only rules.

Vendor the jars with checksum verification — they execute on every developer machine and in CI.
Sizes measured at detekt 2.0.0-alpha.6 / compose-rules 0.6.4:

| Jar | Size |
| --- | --- |
| `detekt-cli-<v>-all.jar` | ~85 MB |
| `detekt-rules-ktlint-wrapper-<v>.jar` | ~1.5 MB |
| `detekt-compose-<v>-all.jar` | ~83 MB |

~169 MB, gitignored. The compose uber jar is unavoidable if you want Compose hints in the IDE — the
IDE plugin needs it too, and it is a different artifact from the Gradle coordinate
`io.nlopez.compose.rules:detekt`.

---

## Profile C: Kotlin compiler plugin

```kotlin
plugins { id("io.github.detekt.gradle.compiler-plugin") version "<v>" }
```

Runs inside `compileKotlin`, so type resolution is free and it is the fastest option in principle.

**Off the table today:** upstream marks it experimental and **K1 only**, so any project on Kotlin
2.x with K2 cannot use it. Revisit when detekt 2.x is stable.

---

## Choosing

| | Gradle plugin | CLI | Compiler plugin |
| --- | --- | --- | --- |
| Type resolution | automatic per source set / variant / target | only if you supply a classpath | free |
| Per-file for hooks | no | **yes** | no |
| Version coupling | Gradle / AGP / Kotlin | Kotlin syntax level only | tight |
| Covers modules without the plugin applied | only via an aggregate task | yes | no |
| Startup cost | Gradle configuration | JVM start | none |
| Status | stable | stable | **experimental, K1 only** |

**The hybrid is the default recommendation**, because the two requirements pull apart: CI catching
real bugs needs type resolution (Gradle plugin), and a hook developers won't disable needs per-file
analysis (CLI). Its marginal cost over Gradle-only is one extra jar and a wrapper script, since the
IDE plugin already requires jars.

Its real cost is **two version pins that must stay equal.** Pin both from `libs.versions.toml`,
have the setup script read that file, and assert equality in CI. Divergence means the two runners
can disagree on config schema and baseline signatures, at which point the baseline stops shielding
one of them and the ratchet dies quietly.

For KMP, split by tier:

| Tier | Runner | Why |
| --- | --- | --- |
| Correctness | one canonical typed Gradle task | needs the classpath; only JVM/Android compilations have one |
| Formatting | one path-based pass | no classpath needed, and it avoids N× duplicate findings on `commonMain` |
| Compose | the canonical typed task | 6 of 39 rules need type resolution; a path-based pass silently drops them |
