#!/usr/bin/env python3
"""Structural validation for this plugin marketplace.

Checks the things the plugin loader accepts silently but that break at runtime --
a `skills/` folder nested inside `.claude-plugin/`, a bundled reference path that
doesn't resolve, a plugin directory nobody registered in the catalog.

Deliberately dependency-light and offline: no Claude Code CLI, no API key, no
network. `claude plugin validate --strict` covers JSON-schema conformance and is
the documented local pre-push step; this covers the structural rules the schema
can't express.

    python3 scripts/validate_structure.py

Exits non-zero on the first category of failure found, after reporting all of them.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
IN_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"
PLUGIN_ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9._/-]+)")

failures: list[str] = []


def fail(message: str, file: Path | None = None) -> None:
    failures.append(message)
    if IN_ACTIONS:
        location = f" file={file.relative_to(ROOT).as_posix()}" if file else ""
        print(f"::error{location}::{message}")
    else:
        prefix = f"{file.relative_to(ROOT).as_posix()}: " if file else ""
        print(f"FAIL  {prefix}{message}")


def warn(message: str, file: Path | None = None) -> None:
    if IN_ACTIONS:
        location = f" file={file.relative_to(ROOT).as_posix()}" if file else ""
        print(f"::warning{location}::{message}")
    else:
        prefix = f"{file.relative_to(ROOT).as_posix()}: " if file else ""
        print(f"warn  {prefix}{message}")


def ok(message: str) -> None:
    print(f"ok    {message}")


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail("file not found", path)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON -- {exc}", path)
    return None


def frontmatter(path: Path) -> dict | None:
    """Parse the YAML frontmatter block from a SKILL.md."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        fail("no YAML frontmatter block", path)
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        fail("frontmatter block is not closed", path)
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        fail(f"frontmatter is not valid YAML -- {exc}", path)
        return None
    if not isinstance(data, dict):
        fail("frontmatter did not parse to a mapping", path)
        return None
    return data


def check_catalog() -> list[tuple[str, Path]]:
    """Validate marketplace.json. Returns (plugin name, plugin dir) pairs."""
    path = ROOT / ".claude-plugin" / "marketplace.json"
    catalog = load_json(path)
    if not isinstance(catalog, dict):
        return []

    for field in ("name", "plugins"):
        if field not in catalog:
            fail(f"missing required field '{field}'", path)

    entries = catalog.get("plugins")
    if not isinstance(entries, list) or not entries:
        fail("'plugins' must be a non-empty array", path)
        return []

    registered: list[tuple[str, Path]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            fail("every plugin entry must be an object", path)
            continue

        name = entry.get("name", "<unnamed>")

        for field in ("name", "source", "description", "category", "tags"):
            if field not in entry:
                fail(f"entry '{name}' is missing '{field}'", path)

        # Version lives in plugin.json and nowhere else — declaring it in both
        # makes the validator warn on drift and can serve users a stale version.
        if "version" in entry:
            fail(f"entry '{name}' declares 'version'; it belongs only in plugin.json", path)

        source = entry.get("source", "")
        if not isinstance(source, str) or not source.startswith("./"):
            fail(f"entry '{name}' source must be a relative path starting './'", path)
            continue
        if ".." in source:
            fail(f"entry '{name}' source contains '..', which the loader rejects", path)
            continue

        plugin_dir = ROOT / source[2:]
        if not plugin_dir.is_dir():
            fail(f"entry '{name}' points at {source}, which does not exist", path)
            continue

        registered.append((name, plugin_dir))

    ok(f"catalog registers {len(registered)} plugin(s)")
    return registered


def check_unregistered(registered: list[tuple[str, Path]]) -> None:
    """A plugin directory nobody registered installs as nothing at all."""
    known = {d.resolve() for _, d in registered}
    for manifest in ROOT.glob("*/.claude-plugin/plugin.json"):
        plugin_dir = manifest.parent.parent
        if plugin_dir.resolve() not in known:
            fail(
                f"plugin directory '{plugin_dir.name}' has a manifest but no "
                f"marketplace.json entry -- it will not be installable",
                manifest,
            )


def check_plugin(name: str, plugin_dir: Path) -> None:
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        return

    if manifest.get("name") != name:
        fail(
            f"plugin.json name '{manifest.get('name')}' does not match the "
            f"catalog entry '{name}'",
            manifest_path,
        )
    if manifest.get("name") != plugin_dir.name:
        fail(
            f"plugin.json name '{manifest.get('name')}' does not match its "
            f"directory '{plugin_dir.name}'",
            manifest_path,
        )
    if not manifest.get("version"):
        fail("plugin.json has no 'version'; installs will pin to a commit SHA", manifest_path)

    # Only plugin.json belongs in .claude-plugin/. A skills/ folder nested there
    # is silently ignored by the loader — no error, the skills simply never load.
    for stray in (plugin_dir / ".claude-plugin").iterdir():
        if stray.name != "plugin.json":
            fail(
                f"unexpected '{stray.name}' inside .claude-plugin/ -- only "
                f"plugin.json belongs there, and skills/ nested here is silently ignored",
                manifest_path,
            )

    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        fail(
            f"no skills/ directory at the plugin root -- an empty plugin "
            f"validates and installs as a silent no-op",
            manifest_path,
        )
        return

    skills = sorted(d for d in skills_dir.iterdir() if d.is_dir())
    if not skills:
        fail("skills/ contains no skill directories", manifest_path)
        return

    for skill_dir in skills:
        check_skill(plugin_dir, skill_dir)

    ok(f"{name} {manifest.get('version')} -- {len(skills)} skill(s)")


def check_skill(plugin_dir: Path, skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        fail(f"no SKILL.md in skills/{skill_dir.name}/", plugin_dir / ".claude-plugin" / "plugin.json")
        return

    meta = frontmatter(skill_md)
    if meta is not None:
        if not meta.get("description"):
            fail("frontmatter has no 'description' -- Claude cannot decide relevance", skill_md)
        declared = meta.get("name")
        if declared and declared != skill_dir.name:
            fail(
                f"frontmatter name '{declared}' does not match directory "
                f"'{skill_dir.name}', which is what sets the invocation name",
                skill_md,
            )

    # Bundled files are reached through ${CLAUDE_PLUGIN_ROOT} because installs are
    # copied into a cache. The variable is "the absolute path to the plugin's
    # installation directory" -- the plugin root, NOT the skill directory -- and it
    # substitutes anywhere it appears in skill content. So the path must resolve
    # relative to the plugin root, and a path that doesn't is a file the skill cannot
    # read at runtime with nothing reporting it until someone invokes the skill.
    #
    # git-workflow:branch shipped for several releases with a skill-relative path
    # here, unable to read the branching-model profiles its first step depends on.
    for body_file in sorted({skill_md, *skill_dir.rglob("*.md")}):
        text = body_file.read_text(encoding="utf-8")
        for rel in sorted(set(PLUGIN_ROOT_REF.findall(text))):
            if (plugin_dir / rel).exists():
                continue
            hint = ""
            if (skill_dir / rel).exists():
                correct = (skill_dir / rel).relative_to(plugin_dir).as_posix()
                hint = f". It resolves from the skill directory -- write ${{CLAUDE_PLUGIN_ROOT}}/{correct}"
            fail(
                f"${{CLAUDE_PLUGIN_ROOT}}/{rel} does not resolve from the plugin root "
                f"({(plugin_dir / rel).relative_to(ROOT).as_posix()}){hint}",
                body_file,
            )

    check_evals(skill_dir)


def check_evals(skill_dir: Path) -> None:
    path = skill_dir / "evals" / "trigger.json"
    if not path.is_file():
        fail(f"no evals/trigger.json -- the description has never been measured", skill_dir / "SKILL.md")
        return

    cases = load_json(path)
    if cases is None:
        return
    if not isinstance(cases, list) or not cases:
        fail("expected a non-empty array of cases", path)
        return

    for i, case in enumerate(cases):
        if not isinstance(case, dict) or set(case) != {"query", "should_trigger"}:
            fail(f"case {i} must have exactly 'query' and 'should_trigger'", path)
        elif not isinstance(case["should_trigger"], bool):
            fail(f"case {i} 'should_trigger' must be a boolean", path)
        elif not str(case["query"]).strip():
            fail(f"case {i} has an empty query", path)

    # Over-triggering is as damaging as under-triggering, and the cheapest
    # negatives are the other skills in the same plugin.
    if not any(c.get("should_trigger") is False for c in cases if isinstance(c, dict)):
        fail("no negative cases -- over-triggering would go unmeasured", path)


def main() -> int:
    registered = check_catalog()
    check_unregistered(registered)
    for name, plugin_dir in registered:
        check_plugin(name, plugin_dir)

    print()
    if failures:
        print(f"{len(failures)} problem(s) found.")
        return 1
    print("All structural checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
