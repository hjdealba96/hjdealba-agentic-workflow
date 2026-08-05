#!/usr/bin/env python3
"""Run trigger evals for the skills in this marketplace.

Wraps the eval runner that ships inside the skill-creator plugin, because that
runner cannot run on Windows as shipped and its failure mode is silent:

  1. Its read loop calls select.select() on the `claude -p` subprocess pipe.
     Windows select() accepts only sockets and raises OSError [WinError 10093].
     The exception is swallowed per query, so every positive scores 0.00 and every
     negative "passes" -- identical to a description that triggers nothing.
     `docs-system` measured 0/10 that way and 10/10 unpatched-description once the
     transport was fixed.
  2. It reads SKILL.md with read_text() and no encoding, so Windows decodes as
     cp1252. A cross mark (byte 0x9d) raises UnicodeDecodeError; an em-dash decodes
     silently into mojibake, which is worse -- the eval then measures a description
     that isn't the one you wrote.

Both patches are applied to a throwaway copy; the plugin cache is never touched.
The detection logic is left exactly as upstream wrote it, so scores stay comparable
to the ones recorded in docs/AUTHORING.md. The patches assert their anchors, so an
upstream change fails loudly instead of silently reverting to a 0.00 sweep.

Usage:
    python3 scripts/run_trigger_eval.py
    python3 scripts/run_trigger_eval.py docs-workflow/skills/reference-doc
    python3 scripts/run_trigger_eval.py --runs 5

Set SKILL_CREATOR_PATH if the plugin lives somewhere this can't find it. Requires
the `claude` CLI on PATH and working credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RUNNER_CANDIDATES = [
    Path.home() / ".claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator",
    Path.home() / ".claude/plugins/cache/claude-plugins-official/skill-creator",
    Path.home() / ".claude/skills/skill-creator",
]


def find_runner() -> Path:
    override = os.environ.get("SKILL_CREATOR_PATH")
    candidates = [Path(override)] if override else []
    candidates += RUNNER_CANDIDATES

    for base in candidates:
        # Accept either the skill directory or the plugin directory above it.
        for probe in (base, base / "skills/skill-creator"):
            if (probe / "scripts/run_eval.py").is_file():
                return probe

    sys.exit(
        "Could not find the skill-creator eval runner.\n"
        "Install it with `/plugin install skill-creator@claude-plugins-official`, "
        "or set SKILL_CREATOR_PATH to the directory containing scripts/run_eval.py."
    )


def patch_runner(source: Path, workdir: Path) -> Path:
    """Copy scripts/ and apply the two Windows fixes. Fails loudly on drift."""
    dest = workdir / "runner"
    dest.mkdir(parents=True)
    shutil.copytree(source / "scripts", dest / "scripts")

    run_eval = dest / "scripts/run_eval.py"
    text = run_eval.read_text(encoding="utf-8")

    old_read = """                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                if not ready:
                    continue

                chunk = os.read(process.stdout.fileno(), 8192)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")"""
    new_read = """                chunk = process.stdout.readline()
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")"""

    old_anchor = """        triggered = False
        start_time = time.time()"""
    new_anchor = """        watchdog = threading.Timer(timeout, process.kill)
        watchdog.daemon = True
        watchdog.start()

        triggered = False
        start_time = time.time()"""

    old_finally = """        finally:
            # Clean up process on any exit path (return, exception, timeout)"""
    new_finally = """        finally:
            watchdog.cancel()
            # Clean up process on any exit path (return, exception, timeout)"""

    for old, new, label in (
        (old_read, new_read, "read loop"),
        (old_anchor, new_anchor, "watchdog anchor"),
        (old_finally, new_finally, "cleanup anchor"),
    ):
        if text.count(old) != 1:
            sys.exit(
                f"Upstream run_eval.py no longer matches the expected {label}.\n"
                f"Re-check the patch against the current version before trusting any score -- "
                f"an unpatched runner reports 0.00 on every query on Windows."
            )
        text = text.replace(old, new)

    text = text.replace("import sys\nimport time", "import sys\nimport threading\nimport time", 1)
    if "import threading" not in text:
        sys.exit("Could not add the threading import to run_eval.py.")

    run_eval.write_text(text, encoding="utf-8", newline="\n")

    # Windows defaults text IO to cp1252; every SKILL.md here is UTF-8.
    for name in ("utils.py", "run_eval.py"):
        path = dest / "scripts" / name
        body = path.read_text(encoding="utf-8")
        body = body.replace(".read_text()", '.read_text(encoding="utf-8")')
        body = re.sub(
            r"\.write_text\((?!.*encoding)([^\n]*?)\)$",
            r'.write_text(\1, encoding="utf-8")',
            body,
            flags=re.M,
        )
        path.write_text(body, encoding="utf-8", newline="\n")

    return dest


def preflight() -> None:
    """The harness preconditions, checked rather than assumed."""
    if not (REPO / ".git").exists():
        sys.exit("Not a git repository. The harness needs one to score git-scoped skills.")

    # The runner walks up from cwd for a .claude/ directory and treats that as the
    # project root, writing its probe command file into .claude/commands/. Without
    # one here it walks out of the repository entirely.
    (REPO / ".claude/commands").mkdir(parents=True, exist_ok=True)

    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    if not dirty:
        print(
            "warning: the working tree is clean. Git-scoped skills under-trigger in a\n"
            "         clean repo -- 'git commit these fixes' scored 0.00 clean and 1.00\n"
            "         dirty. Make a throwaway edit if you are evaluating one.\n"
        )

    user_skills = Path.home() / ".claude/skills"
    if user_skills.is_dir():
        local = {p.name for p in (REPO).glob("*/skills/*") if p.is_dir()}
        clash = sorted(local & {p.name for p in user_skills.iterdir() if p.is_dir()})
        if clash:
            print(
                f"warning: {', '.join(clash)} also exist in ~/.claude/skills/.\n"
                f"         Claude picks the real skill over the harness probe and detection\n"
                f"         credits neither, scoring 0.00 on every positive. Move them aside.\n"
            )


def discover_skills(explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(s.rstrip("/\\")) for s in explicit]
    return sorted(p.parent for p in REPO.glob("*/skills/*/evals/trigger.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("skills", nargs="*", help="Skill directories. Default: all with an eval set.")
    parser.add_argument("--runs", type=int, default=3, help="Runs per query (default 3)")
    parser.add_argument("--timeout", type=int, default=90, help="Seconds per query (default 90)")
    parser.add_argument("--model", default=None, help="Model for `claude -p`")
    args = parser.parse_args()

    if not shutil.which("claude"):
        sys.exit("The `claude` CLI is not on PATH.")

    preflight()
    source = find_runner()
    print(f"runner: {source}")

    workdir = Path(tempfile.mkdtemp(prefix="trigger-eval-"))
    rows, failed = [], False
    try:
        runner = patch_runner(source, workdir)
        env = {**os.environ, "PYTHONPATH": str(runner)}
        env.pop("CLAUDECODE", None)

        for skill in discover_skills(args.skills):
            skill_rel = skill.relative_to(REPO) if skill.is_absolute() else skill
            eval_set = Path(skill_rel) / "evals/trigger.json"
            if not (REPO / eval_set).is_file():
                print(f"skip {skill_rel}: no evals/trigger.json")
                continue

            # --num-workers 1 is mandatory. Parallel workers each write an
            # identically-described command file, all visible to every concurrent
            # query, and detection credits only one specific name. The same eval
            # scored 4/9 parallel and 8/9 serially.
            cmd = [
                sys.executable, "-m", "scripts.run_eval",
                "--eval-set", str(eval_set),
                "--skill-path", str(skill_rel),
                "--runs-per-query", str(args.runs),
                "--num-workers", "1",
                "--timeout", str(args.timeout),
            ]
            if args.model:
                cmd += ["--model", args.model]

            print(f"\n=== {Path(skill_rel).name} ({args.runs} runs/query) ===")
            proc = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
            if proc.returncode != 0 or not proc.stdout.strip():
                print(proc.stderr.strip()[-2000:] or "(no output)")
                print(f"FAILED to run {skill_rel}")
                failed = True
                continue

            data = json.loads(proc.stdout)
            pos = [r for r in data["results"] if r["should_trigger"]]
            neg = [r for r in data["results"] if not r["should_trigger"]]
            for r in data["results"]:
                kind = "pos" if r["should_trigger"] else "neg"
                mark = "PASS" if r["pass"] else "FAIL"
                print(f"  {mark} {kind} {r['triggers']}/{r['runs']}  {r['query']}")
                # A negative that fires at all is cross-skill leakage worth watching
                # even when it stays under the pass threshold.
                if kind == "neg" and r["triggers"] and r["pass"]:
                    print(f"       ^ leaked {r['triggers']}/{r['runs']} -- watch this one")

            summary = data["summary"]
            rows.append((
                Path(skill_rel).name,
                f"{sum(r['pass'] for r in pos)}/{len(pos)}",
                f"{sum(r['pass'] for r in neg)}/{len(neg)}",
                f"{summary['passed']}/{summary['total']}",
            ))
            if summary["failed"]:
                failed = True
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        for stub in (REPO / ".claude/commands").glob("*-skill-*.md"):
            stub.unlink(missing_ok=True)

    if rows:
        width = max(len(r[0]) for r in rows)
        print(f"\n{'skill'.ljust(width)}  positives  negatives  total")
        for name, p, n, t in rows:
            print(f"{name.ljust(width)}  {p.ljust(9)}  {n.ljust(9)}  {t}")
        print("\nPaste this table into the pull request.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
