# Rule layers

The starting rule set, in three tiers. Every key and default below was read from the shipped
default config — not from memory or from the docs.

Two invariants: `buildUponDefaultConfig: true`, and **never** `allRules: true`. Write deltas only.

The tier boundary is **auto-correctability and judgment**, not severity. That is deliberate: it is
also what makes the staged adoption plan fall out for free.

| Tier | Contents | Noise | Baseline? |
| --- | --- | --- | --- |
| 1 Correctness | `potential-bugs`, `coroutines`, `exceptions` | low — these are real bugs | small, if any |
| 2 Formatting | ktlint wrapper | none — mechanical | only the 16 non-correctable rules |
| 3 Conventions | complexity, style, naming, Compose | highest, needs tuning | yes |

---

## Test paths: one anchored list

**A per-rule `excludes` list replaces the default rather than merging with it.** Verified: patching
`MagicNumber` with `excludes: ['**/androidHostTest/**']` dropped the other eight default paths, so
`commonTest` and `iosTest` started reporting and `androidHostTest` went exempt — the opposite of the
intent, with no error.

Since every rule has to restate the whole list anyway, restate a **shared** one. YAML anchors work,
and the custom key must be registered in `config.excludes` or the run hard-fails.

```yaml
config:
  validation: true
  excludes: ['test_paths']        # required, or: "Property 'test_paths' ... does not exist"

test_paths: &test_paths
  - '**/test/**'
  - '**/androidTest/**'
  - '**/androidUnitTest/**'
  - '**/androidHostTest/**'        # NOT in detekt's defaults, on either line
  - '**/androidInstrumentedTest/**'
  - '**/commonTest/**'
  - '**/jvmTest/**'
  - '**/desktopTest/**'            # NOT in detekt's defaults
  - '**/jsTest/**'
  - '**/wasmJsTest/**'             # NOT in detekt's defaults
  - '**/iosTest/**'
```

detekt's stock list covers `androidUnitTest` but not `androidHostTest`, which is what current AGP
generates — so on a modern KMP project those rules fire on host tests while the iOS equivalents are
exempt. Inconsistent by accident.

Apply it only where there is a reason. Most rules **should** run on tests:

```yaml
style:
  MagicNumber:               { excludes: *test_paths }
  StringLiteralDuplication:  { excludes: *test_paths }
  MaxLineLength:             { excludes: *test_paths }
complexity:
  TooManyFunctions:          { excludes: *test_paths }
  LongMethod:                { excludes: *test_paths }
  LargeClass:                { excludes: *test_paths }
naming:
  FunctionNaming:            { excludes: *test_paths }
exceptions:
  TooGenericExceptionCaught: { excludes: *test_paths }
```

Backticked `` `GIVEN … WHEN … THEN` `` test names are why `MaxLineLength` is on that list —
`ignoreBackTickedIdentifiers` does not cover the surrounding `fun` line. The survey's
`backtick_test_names` count tells you whether this project writes them.

**Keep on in test code, deliberately:** the whole ktlint ruleset, `potential-bugs`, and especially
`empty-blocks` — `EmptyFunctionBlock` on a test body catches a test that passes by doing nothing,
which is the highest-value rule you can point at a test source set.

---

## Tier 1 — Correctness

The defaults miss the best rules here. All of these are `active: false` upstream:

```yaml
coroutines:
  GlobalCoroutineUsage:                 { active: true }   # no type resolution — fires in the hook too
  SuspendFunSwallowedCancellation:      { active: true }
  SuspendFunWithCoroutineScopeReceiver:  { active: true }

potential-bugs:
  ElseCaseInsteadOfExhaustiveWhen:      { active: true }   # best single rule for sealed state models
  CastNullableToNonNullableType:        { active: true }
  DontDowncastCollectionTypes:          { active: true }
  ImplicitUnitReturnType:               { active: true }
  NullCheckOnMutableProperty:           { active: true }
  NullableToStringCall:                 { active: true }
  PropertyUsedBeforeDeclaration:        { active: true }
  UnconditionalJumpStatementInLoop:     { active: true }
  UnnecessaryNotNullCheck:              { active: true }

style:
  CanBeNonNullable:  { active: true }
  NullableBooleanCheck: { active: true }
  VarCouldBeVal:     { active: true }
  UseCheckNotNull:   { active: true }
  UseRequireNotNull: { active: true }
  ForbiddenSuppress: { active: true, rules: ['ElseCaseInsteadOfExhaustiveWhen'] }
```

Already correct by default — leave them: `SwallowedException`, `TooGenericExceptionCaught`,
`InjectDispatcher`, `SleepInsteadOfDelay`, `SuspendFunWithFlowReturnType`,
`RedundantSuspendModifier`, all of `empty-blocks`.

Leave `Deprecation` off. During any dependency migration it buries everything else; enable it later
with its own baseline.

**Every rule in this tier except `GlobalCoroutineUsage` needs type resolution**, so this tier is
invisible to a CLI pre-commit hook by construction. Say so rather than letting anyone believe the
hook previews CI.

---

## Tier 2 — Formatting (ktlint)

```yaml
# 1.23.8
formatting:
  active: true
  android: true                     # or false — one choice for the whole repo
  MaximumLineLength: { active: true, maxLineLength: 130, ignoreBackTickedIdentifiers: true }
  TrailingCommaOnCallSite:        { active: true, useTrailingCommaOnCallSite: true }
  TrailingCommaOnDeclarationSite: { active: true, useTrailingCommaOnDeclarationSite: true }
  NoWildcardImports: { active: true }

style:
  MaxLineLength: { active: false }   # duplicate of formatting:MaximumLineLength — both on by default
  UnusedImports: { active: false }   # ktlint's NoUnusedImports already covers it
```

On 2.x the ruleset is `ktlint:` and the style toggle is `code_style:`. See `compatibility.md`.

### Code style is a scale-dependent decision — measure it

The same codebase, three styles:

| | 15-file CMP project | 2,635-file Android project |
| --- | --- | --- |
| `intellij_idea` | 42 | **8,873** |
| `ktlint_official` | 42 | 10,032 |
| `android_studio` | 45 | **33,300** |

On a small project it is noise. On a mature one it is a 24,000-finding decision, and it moves the
part needing human work 6× (900 vs 5,325 non-correctable). `android_studio` is stricter mainly
through a 100-column limit and required trailing commas.

**So do not default to `android_studio` because there's an Android target.** Run all three and show
the user the counts — the tool is already installed at that point. One style for the whole repo:
`formatting.android` / `ktlint.code_style` is ruleset-level and cannot vary by path without a second
config file, and code moving *into* `commonMain` is the normal direction of travel.

### The 16 rules that cannot auto-correct

Everything else in the ktlint ruleset (87 of 103 rules at 0.6.4) is fixed by `--auto-correct`.
These are not, so these are the ones that belong in a baseline:

```
BackingPropertyNaming   ClassName             Filename            FunctionName
Kdoc                    MaximumLineLength     MixedConditionOperators
NoConsecutiveComments   NoEmptyFile           NoWildcardImports   PackageName
PropertyName            TypeArgumentComment   TypeParameterComment
ValueArgumentComment    ValueParameterComment
```

Three independent confirmations of that split: a 42-finding project auto-corrected to 1, and the
survivor was `NoWildcardImports`; a mature codebase's hand-written baseline holds 64
`MaximumLineLength` entries; and detekt's docs warn that auto-formatting and a baseline don't mix
because signatures shift.

**Ordering is mandatory, not stylistic: auto-correct first, then regenerate the baseline.**

### Sequencing a large mechanical change

Land it in this order — the first group is nearly invisible in review, the last is the largest diff:

1. whitespace and imports — `FinalNewline`, `NoTrailingSpaces`, `ImportOrdering`
2. signature reflow — `FunctionSignature`, `ClassSignature`
3. wrapping and trailing commas — `ArgumentListWrapping`, `TrailingCommaOnCallSite`

On a mature codebase the third group alone was 8,760 + 8,444 findings under `android_studio`.

`.editorconfig` is **not** authoritative for detekt: it supplies `indent_size`, `max_line_length`,
`insert_final_newline`, `kotlin_imports_layout` from `detekt.yml` and sets the code style and indent
style itself. Reconcile the two by hand and verify which won.

---

## Tier 3 — Conventions

```yaml
complexity:
  LongMethod:         { threshold: 80 }        # default 60 is tight for Composables
  LongParameterList:  { ignoreDefaultParameters: true, ignoreAnnotated: ['Composable'] }
  TooManyFunctions:   { thresholdInFiles: 20, thresholdInClasses: 15,
                        ignoreAnnotatedFunctions: ['Preview'] }
  CognitiveComplexMethod: { active: true, threshold: 20 }

naming:
  FunctionNaming:         { functionPattern: '[a-zA-Z][a-zA-Z0-9]*' }   # PascalCase @Composable
  TopLevelPropertyNaming: { constantPattern: '[A-Z][A-Za-z0-9]*' }      # Compose convention

style:
  MagicNumber:         { ignorePropertyDeclaration: true, ignoreAnnotated: ['Composable'] }
  ReturnCount:         { max: 3, excludeGuardClauses: true }
  UnusedPrivateMember: { ignoreAnnotated: ['Preview'] }   # + discovered preview_aliases
  ForbiddenComment:
    allowedPatterns: 'TODO\((<PREFIX>-\d+|@\w+)\):'       # <PREFIX> from the survey
```

Note `UnusedPrivateMember` and `UnusedPrivateProperty` are **separate rules** — exempting previews
on only the first leaves the second at default.

`comments` needs nothing: all ten rules are already `active: false`. You would only *enable* some,
for a published module.

Relax deliberately: `ExpressionBodySyntax` off, `WildcardImport` off if the codebase already uses
them, `libraries` ruleset only for shared/published modules.

### Architecture and DI conventions, config-only

`ForbiddenImport` needs no type resolution, so it works everywhere including the hook:

```yaml
style:
  ForbiddenImport:
    active: true
    imports:
      - value: 'org.koin.java.KoinJavaComponent'
        reason: 'Service locator. Inject through the constructor instead.'
      - value: 'org.koin.core.context.GlobalContext'
        reason: 'Reaching into the global Koin context bypasses the module graph.'
      - value: 'dagger.hilt.android.EntryPointAccessors'
        reason: 'Entry points belong at the framework boundary, not in feature code.'
```

`ForbiddenImport` **plus a baseline is a ratchet** — existing violations shielded, new ones blocked
— with no custom script.

| Rule | Type resolution | Works in the hook |
| --- | --- | --- |
| `ForbiddenImport`, `ForbiddenSuppress`, `ForbiddenClassName` | no | **yes** |
| `ForbiddenMethodCall`, `ForbiddenAnnotation` | yes | no |

Framework-specific noise relaxations, from the survey's `di_koin` / `di_hilt`:

| Framework | Add |
| --- | --- |
| Hilt / Dagger | `LongParameterList.ignoreAnnotated: ['Inject']`, `TooManyFunctions.ignoreAnnotated: ['Module']`, generated-code excludes |
| Koin | path exclude on `**/di/**` — the module DSL isn't annotated, so `ignoreAnnotated` can't reach it |

---

## Per-project deltas

| Context | Change |
| --- | --- |
| KMP | Defaults already exempt `commonTest`, `jvmTest`, `iosTest`, `androidUnitTest` on five rules. Newly enabled rules need the anchor added |
| Shared / published module | Enable the `libraries` ruleset and selected `comments` rules; pairs with `explicitApi()` |
| App module | `comments` off (already default), `libraries` off |
| Vendored code | Exclude every path the survey reported in `vendored_dirs` |

## Five ways this config silently does nothing

1. `ignoreAnnotated` is **universal** (any rule), but `LongParameterList` also has
   `ignoreAnnotatedParameter` and `TooManyFunctions` has `ignoreAnnotatedFunctions` — three keys,
   three meanings. Validation catches a key that doesn't exist; it cannot catch a valid key that
   doesn't mean what you assumed.
2. `MaxLineLength` (style) and `MaximumLineLength` (formatting) are both on by default — every long
   line is reported twice until one is disabled.
3. `UnusedPrivateMember` / `UnusedPrivateProperty` are separate rules.
4. ktlint rules can only be suppressed at **file** level (`@file:Suppress`), unlike their
   first-party counterparts.
5. Type-resolution rules don't fire in the hook. Tier 1 is invisible there by construction.
