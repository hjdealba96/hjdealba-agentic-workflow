#!/usr/bin/env bash
# Pin, download and verify the detekt CLI jars.
#
# Copy to <CONFIG_DIR>/detekt-jars.sh and replace every <PLACEHOLDER>. Sourced by
# ./detekt-format, ./detekt-changed and friends -- not executed directly.
#
# Runs on Linux, macOS and Windows (Git Bash / WSL). The portability details below
# are the whole reason this is a separate file rather than four copy-pasted blocks.
set -uo pipefail

# Single source of truth for versions: read the version catalog rather than
# duplicating the numbers here. Two pins that can drift is how the Gradle side and
# the CLI side end up disagreeing about the config schema and baseline signatures.
CATALOG="gradle/libs.versions.toml"
read_version() { # read_version <key>
  grep -E "^[[:space:]]*$1[[:space:]]*=" "$CATALOG" 2>/dev/null |
    head -1 | sed -E 's/.*=[[:space:]]*"?([^"]+)"?.*/\1/'
}

DETEKT_VERSION="$(read_version '<DETEKT_CATALOG_KEY>')"
COMPOSE_RULES_VERSION="$(read_version '<COMPOSE_CATALOG_KEY>')"
if [ -z "$DETEKT_VERSION" ]; then
  echo "ERROR: could not read the detekt version from $CATALOG" >&2
  exit 1
fi

DIR="<CONFIG_DIR>"
DETEKT_JAR="$DIR/detekt-cli-${DETEKT_VERSION}-all.jar"
KTLINT_JAR="$DIR/<KTLINT_ARTIFACT>-${DETEKT_VERSION}.jar"
COMPOSE_JAR="$DIR/detekt-compose-${COMPOSE_RULES_VERSION}-all.jar"

# Fill these in once, from the release page or from a first verified download.
# NEVER leave one empty: an unverified jar executes on every developer machine and
# in CI, which makes it the single highest-value supply-chain target here.
SHA256_DETEKT="<SHA256_DETEKT>"
SHA256_KTLINT="<SHA256_KTLINT>"
SHA256_COMPOSE="<SHA256_COMPOSE>"

BASE="https://github.com/detekt/detekt/releases/download/v${DETEKT_VERSION}"
COMPOSE_URL="https://github.com/mrmans0n/compose-rules/releases/download/v${COMPOSE_RULES_VERSION}/detekt-compose-${COMPOSE_RULES_VERSION}-all.jar"

# Linux ships sha256sum; macOS ships only shasum. Git Bash on Windows has both.
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "ERROR: no sha256sum or shasum available to verify $1" >&2
    exit 1
  fi
}

fetch() { # fetch <path> <url>
  echo "Downloading $(basename "$1")..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$1" "$2" || { rm -f "$1"; echo "ERROR: download failed: $2" >&2; exit 1; }
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$1" "$2" || { rm -f "$1"; echo "ERROR: download failed: $2" >&2; exit 1; }
  else
    echo "ERROR: neither curl nor wget is available" >&2
    exit 1
  fi
}

verify() { # verify <path> <expected>
  local actual
  actual="$(sha256_of "$1")"
  if [ "$actual" != "$2" ]; then
    echo "ERROR: checksum mismatch for $1" >&2
    echo "  expected: $2" >&2
    echo "  actual:   $actual" >&2
    # Delete it. A jar that failed verification must never be reachable by a
    # later run that happens to skip the download because the file exists.
    rm -f "$1"
    exit 1
  fi
}

ensure() { # ensure <path> <url> <sha256>
  [ -f "$1" ] || fetch "$1" "$2"
  verify "$1" "$3"
}

mkdir -p "$DIR"
ensure "$DETEKT_JAR" "${BASE}/detekt-cli-${DETEKT_VERSION}-all.jar" "$SHA256_DETEKT"
ensure "$KTLINT_JAR" "${BASE}/<KTLINT_ARTIFACT>-${DETEKT_VERSION}.jar" "$SHA256_KTLINT"
if [ -n "${COMPOSE_RULES_VERSION:-}" ]; then
  ensure "$COMPOSE_JAR" "$COMPOSE_URL" "$SHA256_COMPOSE"
fi

# --plugins separator. There is NO single form that works everywhere, so build the
# joined string once here rather than hardcoding a separator in four scripts.
#
#   detekt 1.23.x  accepts ','  or ';'          -- rejects ':' and a repeated flag
#   detekt 2.x     accepts ':' on *nix,
#                          ';' on Windows,
#                          or a repeated --plugins flag
#                                                -- rejects ','
#
# All four combinations were measured, on Windows and on Linux. The control for
# "did the jars really load" is omitting --plugins, which makes the ruleset key
# hard-fail. On Windows a colon fails as InvalidPathException (drive letters
# already contain one); on Linux 2.x a comma fails as "Path 'a.jar,b.jar' ...
# does not exist". Full matrix in reference/compatibility.md.
case "$DETEKT_VERSION" in
  1.*) PLUGIN_SEP=',' ;;                    # portable across platforms on 1.x
  *)
    case "$(uname -s)" in
      MINGW* | MSYS* | CYGWIN*) PLUGIN_SEP=';' ;;
      *) PLUGIN_SEP=':' ;;
    esac
    ;;
esac

DETEKT_PLUGINS="$KTLINT_JAR"
if [ -f "${COMPOSE_JAR:-}" ]; then
  DETEKT_PLUGINS="${DETEKT_PLUGINS}${PLUGIN_SEP}${COMPOSE_JAR}"
fi

export DETEKT_JAR KTLINT_JAR COMPOSE_JAR DETEKT_PLUGINS DETEKT_VERSION COMPOSE_RULES_VERSION
