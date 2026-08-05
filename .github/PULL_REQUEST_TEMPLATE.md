<!-- Delete any section that doesn't apply. Empty headings are worse than absent ones. -->

## What changed

<!-- Be specific. "Added a measured width gate to commit Step 4" beats "updated the
     skill" — a reviewer here is reading prose, not a diff they can compile. -->

## Why

<!-- What was wrong, missing, or unenforced. One or two sentences of intent saves the
     reviewer from reverse-engineering it. Link the issue: Closes #123 -->

## Type of change

- [ ] New skill in an existing plugin
- [ ] New plugin
- [ ] Changed rules or workflow in an existing skill
- [ ] Wording only
- [ ] Repo tooling, CI, or authoring docs

## How to try it

<!-- Nothing here compiles, so the only real review is running the skill. Give the
     reviewer steps they can follow verbatim. Delete if this PR touches no skill. -->

```
/plugin marketplace add .
/plugin install <plugin>@hjdealba-agentic-workflow
/reload-plugins
```

1. Invoke:
2. Expect:
3. Also check it does *not* trigger on:

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
