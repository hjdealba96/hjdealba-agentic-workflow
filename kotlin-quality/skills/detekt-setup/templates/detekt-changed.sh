#!/usr/bin/env bash
# Pre-commit entry point: run detekt over the changed files only.
#
# Copy to the repository root as ./detekt-changed and replace every
# <PLACEHOLDER>. Invoked by pre-commit with the staged file paths as arguments,
# or manually with a comma-separated list.
#
# Per-file analysis is the one thing only the CLI can do, which is why the hook
# uses the CLI rather than a Gradle task -- see reference/delivery-modes.md.
set -uo pipefail

if [ $# -eq 0 ]; then
  exit 0
fi

cd "$(git rev-parse --show-toplevel)" || exit 1
source <SETUP_SCRIPT> # pins versions, downloads jars, verifies SHA-256

# pre-commit passes paths as separate arguments; --input wants them comma-separated.
input=$(IFS=,; echo "$*")

# --auto-correct rewrites files but does NOT stage them.
#   - Under the pre-commit framework that is correct: the run fails with
#     "files were modified by this hook" and the developer re-adds.
#   - Under a raw .git/hooks/pre-commit you must stage them yourself, or the
#     commit lands unformatted. Uncomment the `git add` below in that case.
# $DETEKT_PLUGINS is assembled by the setup script, because the --plugins separator
# depends on BOTH the detekt line and the platform (',' on 1.23.x; ':' on *nix and
# ';' on Windows for 2.x). Never hardcode it here.
#
# If the project has no baseline for this tier, delete the --baseline line ENTIRELY,
# including its trailing backslash. Leaving a bare backslash-less line in the middle
# severs the continuation and bash runs `--plugins` as a command.
java -jar "$DETEKT_JAR" \
  --input "$input" \
  --build-upon-default-config \
  --config <FORMATTING_CONFIG> \
  --baseline <FORMATTING_BASELINE> \
  --plugins "$DETEKT_PLUGINS" \
  --auto-correct \
  --parallel
status=$?

# git add $@

if [ $status -ne 0 ]; then
  cat >&2 <<'MSG'

detekt found issues in the staged files.

This hook is a fast SUBSET of CI, not a preview of it: the CLI runs in light
analysis mode, so every rule that needs compiler type information -- most of
the coroutines and potential-bugs rules -- cannot run here. CI is the gate.

If files were rewritten by --auto-correct, re-add them and commit again.
MSG
fi

exit $status
