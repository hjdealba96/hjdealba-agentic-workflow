<!-- Delete any section that doesn't apply. Empty headings are worse than absent ones.
     Sections through "Related Issues" mirror the default structure in the `open-pr`
     skill, so a PR reads the same shape whether or not this file is found. -->

## Description

<!-- What this does and why it matters, in 1–3 sentences. The "why" is the part a
     reviewer cannot reconstruct from the diff. -->

## Type of change

<!-- Repo-specific: this drives the version bump below. -->

- [ ] New skill in an existing plugin
- [ ] New plugin
- [ ] Changed rules or workflow in an existing skill
- [ ] Wording only
- [ ] Repo tooling, CI, or authoring docs

## Changes Made

<!-- Be specific. "Added a measured width gate to commit Step 4" beats "updated the
     skill". Everything here is prose, so a vague bullet can't be checked against a
     compiler — the specificity has to come from you. -->

-
-

## How to Test

<!-- Nothing here compiles, so the only real test is running the skill. Give steps a
     reviewer can follow verbatim. Delete if this PR touches no skill. -->

```
/plugin marketplace add .
/plugin install <plugin>@hjdealba-agentic-workflow
/reload-plugins
```

1. Invoke:
2. Expect:
3. Also check it does *not* trigger on:

## Related Issues

<!-- Closes #123 — or delete this section. -->

---

<!-- Below this line: repo-specific pre-merge gates. -->

## Version

- [ ] Bumped in `<plugin>/.claude-plugin/plugin.json`: `___` → `___`
- [ ] Not needed — no plugin content changed

Patch = wording · minor = new skill or changed rule · major = removed or renamed skill,
or reversed convention.

## Validation

- [ ] `python3 scripts/validate_structure.py`
- [ ] `claude plugin validate . --strict`
- [ ] `claude plugin validate ./<plugin> --strict`

## Trigger evals

Run locally and paste the scores:

```bash
python3 scripts/run_trigger_eval.py <skill>
```

| Skill | Positives | Negatives | Total |
| --- | --- | --- | --- |
|  |  |  |  |

- [ ] Run, scores above
- [ ] Not needed — no skill `description` changed

## Authoring checks

- [ ] Every new rule is universal; repo-specific facts belong in a learnings file
- [ ] Eval negatives include the other skills in this plugin
- [ ] Bundled files referenced through `${CLAUDE_PLUGIN_ROOT}`
- [ ] New plugin: `marketplace.json` entry added without `version`, ships at least one skill
- [ ] Removed or renamed a plugin: `renames` entry added
