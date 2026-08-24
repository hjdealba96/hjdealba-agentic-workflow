#!/usr/bin/env bash
# Survey a Kotlin/Android/KMP repository before setting up detekt.
#
# Read-only: writes nothing, changes nothing. Prints `key=value` lines for the
# skill to read. Run from anywhere inside the repository.
#
# Every count and pattern here was wrong at least once while this was written.
# The comments record why each form is what it is. Do not "simplify" them, and
# if you change one, re-run it against a large real repository first.
set -uo pipefail

root=$(git rev-parse --show-toplevel 2>/dev/null) || root="$PWD"
cd "$root" || exit 1
echo "repo_root=$root"

is_git=false
git rev-parse --is-inside-work-tree >/dev/null 2>&1 && is_git=true
echo "is_git=$is_git"

# --- Foreign code -------------------------------------------------------------
# Vendored third-party source must be excluded from every count and every
# discovered value, or a dependency's conventions get proposed as yours.
#
# Submodules are the obvious case. The non-obvious one is a vendored project
# checked in as ordinary tracked files: no .gitmodules, nothing to detect it by.
# The signal that covers both is a nested directory with its own Gradle settings
# file, i.e. an independent build living inside yours.
foreign=$(
  {
    if [ "$is_git" = true ]; then git submodule status 2>/dev/null | awk '{print $2}'; fi
    find . -mindepth 2 -maxdepth 4 -name 'settings.gradle*' -not -path '*/build/*' 2>/dev/null |
      sed -E 's|/settings\.gradle(\.kts)?$||; s|^\./||'
  } | sed '/^$/d' | sort -u
)
echo "vendored_dirs=$(echo "$foreign" | paste -sd, -)"

foreign_re=$(echo "$foreign" | paste -sd'|' -)
strip_foreign() {
  if [ -n "$foreign_re" ]; then grep -vE "^(\./)?($foreign_re)/"; else cat; fi
}

# grep -r cannot be filtered after the fact when using -q or -h, so exclude up
# front. --exclude-dir matches a directory NAME, not a path.
excl=(--exclude-dir=build --exclude-dir=.git --exclude-dir=.gradle --exclude-dir=.idea --exclude-dir=node_modules)
while IFS= read -r d; do
  if [ -n "$d" ]; then excl+=(--exclude-dir="$(basename "$d")"); fi
done <<<"$foreign"

# --- Scale --------------------------------------------------------------------
# `git ls-files` returns nothing in a repo with zero commits, which is exactly
# the greenfield case this skill serves. Fall back to the filesystem.
list_files() {
  local pat="$1"
  if [ "$is_git" = true ] && [ -n "$(git ls-files "$pat" 2>/dev/null | head -1)" ]; then
    git ls-files "$pat" 2>/dev/null
  else
    find . -name "$pat" -not -path '*/build/*' -not -path '*/.git/*' \
      -not -path '*/.gradle/*' 2>/dev/null | sed 's|^\./||'
  fi | strip_foreign
}

echo "kt_files=$(list_files '*.kt' | wc -l | tr -d ' ')"
echo "kts_files=$(list_files '*.kts' | wc -l | tr -d ' ')"
# `xargs wc -l | tail -1` undercounts: xargs batches, each batch prints its own
# total, and tail keeps only the last one. Concatenate instead.
echo "kt_loc=$(list_files '*.kt' | tr '\n' '\0' | xargs -0 cat 2>/dev/null | wc -l | tr -d ' ')"
# detekt cannot read XML at all: its includes are **/*.kt and **/*.kts. This
# count exists so the report can state what is NOT covered.
echo "xml_files=$(list_files '*.xml' | wc -l | tr -d ' ')"

# Groovy allows any number of modules on one `include` line, so counting lines
# reads a 5-module project as 1. Count the quoted `:name` tokens instead.
echo "gradle_modules=$(grep -hoE "['\"]:[A-Za-z0-9_.:-]+['\"]" settings.gradle settings.gradle.kts 2>/dev/null | sort -u | wc -l | tr -d ' ')"

# --- History and team ---------------------------------------------------------
if [ "$is_git" = true ]; then
  echo "commits=$(git rev-list --count HEAD 2>/dev/null || echo 0)"
  # A weak proxy: squashed history, contractors and monorepos all distort it.
  echo "authors_12mo=$(git log --since='12 months ago' --format='%ae' 2>/dev/null | sort -u | wc -l | tr -d ' ')"
  echo "first_commit=$(git log --reverse --format='%as' 2>/dev/null | head -1)"
  echo "default_branch=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||')"
else
  echo "commits=0"
  echo "authors_12mo=0"
fi

# --- Infrastructure -----------------------------------------------------------
echo "gh_workflows=$(ls .github/workflows/*.y*ml 2>/dev/null | wc -l | tr -d ' ')"
echo "precommit_config=$([ -f .pre-commit-config.yaml ] && echo yes || echo no)"
echo "convention_plugins=$({ [ -d buildSrc ] || [ -d build-logic ]; } && echo yes || echo no)"
echo "version_catalog=$([ -f gradle/libs.versions.toml ] && echo yes || echo no)"
echo "tracked_shell_scripts=$(list_files '*.sh' | wc -l | tr -d ' ')"
echo "editorconfig=$([ -f .editorconfig ] && echo yes || echo no)"
echo "blame_ignore_revs=$([ -f .git-blame-ignore-revs ] && echo yes || echo no)"
# Open PRs are the true cost of a repo-wide reformat: each one conflicts.
# Needs an authenticated gh. "unknown" is not zero.
if command -v gh >/dev/null 2>&1; then
  echo "open_prs=$(gh pr list --state open --limit 200 --json number 2>/dev/null | grep -o '"number"' | wc -l | tr -d ' ')"
else
  echo "open_prs=unknown"
fi

# --- Existing detekt ----------------------------------------------------------
# Any hit here means the audit path, not a setup path.
echo "detekt_config=$(list_files '*detekt*.yml' | tr '\n' ' ')"
echo "detekt_baseline=$(list_files '*baseline*.xml' | tr '\n' ' ')"
echo "detekt_in_build=$(grep -rlE 'detekt' --include=build.gradle --include=build.gradle.kts --include=libs.versions.toml "${excl[@]}" . 2>/dev/null | sed 's|^\./||' | strip_foreign | tr '\n' ' ')"
echo "idea_detekt=$([ -f .idea/detekt.xml ] && echo yes || echo no)"

# --- Project shape ------------------------------------------------------------
echo "kmp_targets=$(grep -rhoE '\b(androidTarget|jvm|iosArm64|iosX64|iosSimulatorArm64|macosArm64|linuxX64|js|wasmJs|mingwX64)[[:space:]]*\(' --include=build.gradle.kts --include=build.gradle "${excl[@]}" . 2>/dev/null | tr -d ' (' | sort -u | paste -sd, -)"
# Source-set names matter: detekt's default test excludes cover androidUnitTest
# but NOT androidHostTest, desktopTest or wasmJsTest.
echo "source_sets=$(find . -type d -path '*/src/*' -not -path '*/build/*' 2>/dev/null | sed 's|^\./||' | strip_foreign | sed -E 's|.*/src/([^/]+).*|\1|' | sort -u | paste -sd, -)"
echo "compose=$(grep -rqE 'androidx\.compose|org\.jetbrains\.compose|compose-multiplatform' --include=*.toml --include=build.gradle.kts --include=build.gradle "${excl[@]}" . 2>/dev/null && echo yes || echo no)"
echo "explicit_api=$(grep -rq 'explicitApi' --include=build.gradle.kts --include=build.gradle "${excl[@]}" . 2>/dev/null && echo yes || echo no)"
echo "legacy_views=$(grep -rlE 'findViewById|ViewBinding' --include=*.kt "${excl[@]}" . 2>/dev/null | wc -l | tr -d ' ')"

# --- Toolchain ----------------------------------------------------------------
# Feeds the compatibility set: detekt's bundled Kotlin must parse this syntax.
grep -hE '^[[:space:]]*(kotlin|agp|androidGradlePlugin|android-gradle-plugin)[[:space:]]*=' gradle/libs.versions.toml 2>/dev/null | tr -d ' "' | sed 's/^/catalog_/'
echo "gradle_wrapper=$(grep -oE 'gradle-[0-9.]+-' gradle/wrapper/gradle-wrapper.properties 2>/dev/null | head -1 | sed 's/gradle-//;s/-$//')"
echo "java_version=$(java -version 2>&1 | head -1 | grep -oE '[0-9]+(\.[0-9]+)*' | head -1)"

# --- Values to propose in the config ------------------------------------------
echo "di_koin=$(grep -rqE 'io\.insert-koin|org\.koin' --include=*.toml --include=*.kts --include=*.gradle "${excl[@]}" . 2>/dev/null && echo yes || echo no)"
echo "di_hilt=$(grep -rqE 'dagger\.hilt|com\.google\.dagger' --include=*.toml --include=*.kts --include=*.gradle "${excl[@]}" . 2>/dev/null && echo yes || echo no)"
# Custom @Preview aliases feed ignoreAnnotated / ignoreAnnotatedFunctions.
echo "preview_aliases=$(grep -rhB2 --include=*.kt "${excl[@]}" -E '^annotation class [A-Za-z]+' . 2>/dev/null | grep -A2 '@Preview' | grep -oE 'annotation class [A-Za-z]+' | awk '{print $3}' | sort -u | paste -sd, -)"
# NOTE the capital C in staticCompositionLocalOf. An earlier version matched
# `(static)?compositionLocalOf`, which silently found only the non-static form
# and reported a vendored dependency's locals instead of the project's own.
echo "composition_locals=$(grep -rhoE 'val (Local[A-Za-z0-9]+)[^=]*=[[:space:]]*(staticCompositionLocalOf|compositionLocalOf|compositionLocalWithComputedDefaultOf)' --include=*.kt "${excl[@]}" . 2>/dev/null | awk '{print $2}' | sort -u | paste -sd, -)"
echo "material2=$(grep -rqE 'androidx\.compose\.material\.[A-Z]' --include=*.kt "${excl[@]}" . 2>/dev/null && echo yes || echo no)"
echo "backtick_test_names=$(grep -rlE 'fun `[^`]+`\(' --include=*.kt "${excl[@]}" . 2>/dev/null | wc -l | tr -d ' ')"
if [ "$is_git" = true ]; then
  echo "ticket_prefix=$(git log --format='%s' -n 200 2>/dev/null | grep -oE '\b[A-Z][A-Z0-9]{1,9}-[0-9]+' | sed 's/-[0-9]*$//' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')"
fi
echo "generated_dirs=$(find . -type d \( -name generated -o -name composeResources -o -name schemas \) -not -path '*/build/*' 2>/dev/null | sed 's|^\./||' | strip_foreign | paste -sd, -)"
