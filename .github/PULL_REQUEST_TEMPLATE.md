<!-- Delete any section that doesn't apply. -->

## What changed

## Why

## Type of change

- [ ] New skill in an existing plugin
- [ ] New plugin
- [ ] Changed rules or workflow in an existing skill
- [ ] Wording only
- [ ] Repo tooling, CI, or authoring docs

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
