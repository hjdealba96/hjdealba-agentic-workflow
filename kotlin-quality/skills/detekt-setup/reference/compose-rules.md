# Compose rules

Compose checks come from a third-party plugin, [compose-rules](https://mrmans0n.github.io/compose-rules/),
plus a handful of adjustments to detekt's own rules so Compose code doesn't trip them.

**Both halves are required.** The plugin alone, without the built-in tweaks, is unusably noisy on
day one.

## Coordinates

| Use | Artifact |
| --- | --- |
| Gradle | `detektPlugins("io.nlopez.compose.rules:detekt:<v>")` |
| CLI and the **IDE plugin** | the `detekt-compose-<v>-all.jar` uber jar from the release page (~83 MB) |

Two different artifacts for the same rules. The IDE plugin needs the uber jar, so it is unavoidable
if you want Compose hints while typing.

The version is keyed to the **detekt** version, not to Kotlin — 0.4.x for detekt 1.23.8, 0.5.0+ for
the 2.x line. Check the matrix at <https://mrmans0n.github.io/compose-rules/detekt/> and see
`compatibility.md`.

## Enabling it: shorter than you'd expect

At 0.6.4 the plugin ships **39 rules and only 4 are off by default.** So activating the ruleset gets
you 35 rules with no enumeration:

```yaml
Compose:
  active: true
  CompositionLocalAllowlist:
    active: true
    allowedCompositionLocals: <from the survey's composition_locals>
  LambdaParameterInRestartableEffect: { active: true }   # opt-in, and it finds real bugs
  ComposableNestingDepth: { active: true, composableNestingDepthThreshold: 3 }
  UnstableCollections: { active: false }                 # noisiest rule in the set
  PreviewNaming: { active: false }
```

Off by default: `ComposableNestingDepth`, `LambdaParameterInRestartableEffect`, `PreviewNaming`,
`UnstableCollections`.

Enumerating all 39 (as hand-written configs tend to) mostly restates defaults and creates an upgrade
hazard — a rule removed upstream becomes an unknown key, and detekt **hard-fails** on those.
`Material2` was removed in 0.6.x, so a config carrying `Material2: active: false` breaks outright
after that upgrade.

Read the real rule list out of the jar rather than the docs:

```bash
unzip -p detekt-compose-<v>-all.jar config/config.yml | grep -E '^  [A-Za-z]+:'
```

## Type resolution: 6 of 39

Determined from the class hierarchy (the marker is the interface `RequiresAnalysisApi`):

```
ConditionHoist   InvalidReadOnlyComposable   MissingReadOnlyComposable
StaleRememberUpdatedStateInRemember   UnnecessaryComposable   VarsWithoutStateBacking
```

The other **33 are pure PSI** — every `Modifier*` rule, all naming rules, `ComposableParamOrder`,
`RememberMissing`, `MutableStateParam`, `ViewModelForwarding`, the preview rules. Those run
anywhere, with no classpath.

Note those 6 are essentially the newest rules in the set. The most semantic Compose checks are
exactly the ones needing a compiler classpath.

### What that means per source set

| Source set | Compose rules that can run |
| --- | --- |
| `androidMain` | **39** |
| `commonMain`, via an Android or JVM compilation task | **39** |
| `commonMain`, via a path-based pass with no classpath | 33 |
| `iosMain`, `nativeMain`, `wasmJsMain` | **33, permanently** — those targets have no classpath |

Two consequences to state in the report:

1. **Run Compose rules on the canonical typed task**, not the path-based pass — a file walk silently
   drops those 6. See `delivery-modes.md`.
2. **Keep Compose UI in `commonMain`.** UI that lives in `iosMain` loses those 6 rules forever. This
   is a quantified reason for advice that is usually given on style grounds.

Verified working on Compose Multiplatform: the rules recognize
`androidx.compose.ui.tooling.preview.Preview` as used in CMP common code.

## The built-in tweaks Compose needs

Without these, default detekt rules fire constantly on correct Compose code:

| Rule | Change | Why |
| --- | --- | --- |
| `naming:FunctionNaming` | `functionPattern: '[a-zA-Z][a-zA-Z0-9]*'` | `@Composable` functions are PascalCase |
| `naming:TopLevelPropertyNaming` | `constantPattern: '[A-Z][A-Za-z0-9]*'` | Compose constants aren't SCREAMING_SNAKE |
| `complexity:LongParameterList` | `ignoreDefaultParameters: true`, `ignoreAnnotated: ['Composable']` | Composables legitimately take many defaulted params |
| `complexity:LongMethod` | `threshold: 80` | Composable bodies are long by nature |
| `complexity:TooManyFunctions` | `ignoreAnnotatedFunctions: ['Preview', <aliases>]` | preview functions inflate the count |
| `style:MagicNumber` | `ignorePropertyDeclaration: true` | color and dimension declarations |
| `style:UnusedPrivateMember` | `ignoreAnnotated: ['Preview', <aliases>]` | previews are never called |

`<aliases>` comes from the survey's `preview_aliases` — custom annotations annotated `@Preview`
(e.g. `PreviewApp`, `PreviewAppTall`). Missing them is a common source of noise, and they are
discoverable, so discover them rather than asking.

`Material2` (where the version still has it) tracks the survey's `material2` flag: a project using
only Material 3 plus Material icons does not need the rule.

## Expected volume

| Project | Findings |
| --- | --- |
| 15-file greenfield CMP project | **2** (`PreviewPublic` ×2) |
| 2,635-file Android app already enforcing an older compose-rules version | **272**, dominated by `ParameterNaming` (166) |

So a greenfield project can enable the whole Compose tier from day one at near-zero cost, while a
mature codebase should expect a Tier 3 group of its own with its own baseline. Note the 272 was
measured **without** a classpath, so the 6 type-resolution rules contributed nothing — treat any
such number as a floor.
