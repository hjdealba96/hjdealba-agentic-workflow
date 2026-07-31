# henryd-workflow

A personal [Claude Code](https://code.claude.com/docs) **plugin marketplace** — a
curated set of skills that encode how I actually work, installable into any
repository across any GitHub organization.

The skills here are opinionated on purpose. They reflect one developer's
conventions rather than a neutral baseline, so the intended way to use this as
an outsider is to fork it and adapt the skill bodies. Everything is MIT
licensed.

## Install

Add the marketplace once — registration is per-user, so this carries into every
repository you open:

```bash
/plugin marketplace add hjdealba96/claude-code-skills
```

Then install the plugin. `git-workflow` is language-agnostic, so user scope
makes sense — the skills follow you into every repo:

```bash
/plugin install git-workflow@henryd-workflow
```

Skills are namespaced by plugin, so they're invoked as `/<plugin>:<skill>` — for
example `/git-workflow:open-pr`.

## Plugins

### `git-workflow` — `0.3.0`

| Skill | Invocation | What it does |
| --- | --- | --- |
| `commit` | `/git-workflow:commit`, or automatic | Reads the diff, writes a message to the [Conventional Commits 1.0.0](https://www.conventionalcommits.org) spec, and commits with your exact bytes after you approve. Infers scope from a ticket ID or the code area, and matches the type vocabulary already in the repo's history. |
| `branch` | `/git-workflow:branch`, or automatic | Names branches to the [Conventional Branch](https://conventional-branch.github.io/) standard, checking existing branches so the name matches local convention. Asks for a ticket ID when the repo tracks work that way, and proposes a branch before implementation work starts on a trunk branch. |
| `open-pr` | `/git-workflow:open-pr` only | Opens a GitHub PR through a gated sequential workflow. Discovers the target branch, PR template, and real label vocabulary from the repo; writes the body to a scratch file you can edit; scans for secrets; creates nothing without explicit approval. |

`open-pr` is manual-invocation only (`disable-model-invocation: true`) because it
publishes to a real remote. The other two can be invoked by Claude when relevant.

More plugins will be added as the skills exist to fill them — likely candidates
are Android native, Kotlin Multiplatform, API design, and Python. Nothing is
registered here until it ships real skills, so every entry in the catalog is
something you can actually install and use.

## How these skills adapt per project

Every skill here splits its knowledge in two.

**Static conventions are authored into the skill** — how to write a good PR
description, the Conventional Commits specification, branch naming rules,
security rules. These don't vary by repository, so they ship with the plugin.

**Repository-specific facts live in a learnings file** in the consuming project,
at `.claude/learnings/<plugin>/<skill>.md` — the target branch, a reviewer group,
a ticket-title prefix to strip, a required description section. When you correct
a skill on something durable, it drafts an entry, shows it to you, and appends it
only if you approve.

```
mudflap-android/.claude/learnings/git-workflow/open-pr.md

  ## Target Branch
  **Rule:** PRs target `develop`. Hotfix branches target `master`.
  **Why:** `main` is release-only in this repository.
```

Nothing is created up front. A repository with no learnings file runs on the
skill's built-in conventions — no setup required. The file appears the first time
you approve a learning there, and because it's committed, the whole team gets it.

Skills also discover what they can rather than assuming: the PR template from
`.github/`, real labels via `gh label list`, the default branch via
`gh repo view`. Learnings only cover what discovery can't reach.

### Why learnings live in the project, not beside the skill

The natural instinct is to keep `learnings.md` next to `SKILL.md`, the way a
project-local skill does:

```
.claude/skills/open-pull-request/
├── SKILL.md
└── learnings.md      ← works perfectly for a skill that lives in the repo
```

**That doesn't work for a distributed plugin, and the reason is worth
recording.** Installing a plugin does not copy it into your repository. It
writes a single flag into the project's `.claude/settings.json`:

```json
{ "enabledPlugins": { "git-workflow@henryd-workflow": true } }
```

and points at one shared copy on your machine:

```
~/.claude/plugins/cache/henryd-workflow/git-workflow/0.3.0/skills/open-pr/
                                                     ↑
                                              version segment
```

Two consequences follow, and both are fatal to co-location:

1. **One copy serves every project.** That folder is outside all of your
   repositories and has no idea which one invoked it. A `learnings.md` written
   there would be read by every project that installs the plugin — mudflap's
   `develop` target would apply in an unrelated repo. Per-project learnings are
   structurally impossible there.
2. **It is destroyed on every update.** The path contains the plugin version, so
   `0.3.0/` becomes `0.4.0/` on the next `/plugin update` and anything written
   inside is gone.

Keeping learnings in the consuming project fixes both, and adds a third benefit:
the file is committed, so the whole team inherits the conventions instead of
them living in one developer's home directory.

**Why the path is namespaced by plugin.** A flat `.claude/learnings/<skill>.md`
would be shorter, but it collides in two realistic ways:

1. **A plugin skill and a project's own skill sharing a name.** A repository with
   its own `code-review` skill writing to `.claude/learnings/code-review.md`
   would have that file silently taken over by a plugin skill of the same name.
   Two unrelated skills, one file, merged conventions.
2. **Two plugins from this same marketplace.** Names like `review`, `test`,
   `lint`, or `format` are plausible in more than one language or platform
   plugin.

Namespacing by plugin prevents both, and makes provenance visible at a glance —
you can see which learnings came from an installed plugin and which belong to the
project's own skills:

```
.claude/learnings/
├── code-review.md          ← this project's own skill
└── git-workflow/
    ├── open-pr.md          ← from the installed plugin
    ├── commit.md
    └── branch.md
```

Project-local skills keep whatever convention they already use; the plugin folder
sits alongside without disturbing them.

**The tradeoff being accepted.** Perfect co-location is achievable only by
abandoning marketplace distribution and copying skill folders into every
repository by hand — which means no central updates and manual re-syncing on
every edit. Central distribution is worth more than adjacency.

## Repository layout

```
claude-code-skills/
├── .claude-plugin/
│   └── marketplace.json          # the catalog
├── docs/
│   └── AUTHORING.md              # conventions for writing new skills
├── git-workflow/
│   ├── .claude-plugin/
│   │   └── plugin.json
│   └── skills/
│       ├── commit/
│       │   ├── SKILL.md
│       │   └── evals/trigger.json
│       ├── branch/
│       │   ├── SKILL.md
│       │   └── evals/trigger.json
│       └── open-pr/
│           ├── SKILL.md
│           └── evals/trigger.json
├── LICENSE
└── README.md
```

Two structural rules the plugin loader enforces:

- **Only `plugin.json` belongs in `.claude-plugin/`.** The `skills/` directory
  must sit at the plugin root. A `skills/` folder nested inside `.claude-plugin/`
  is silently ignored.
- **Plugin `source` values in `marketplace.json` are relative paths**
  (`./git-workflow`), which is valid because the plugins live inside the
  marketplace repo. Paths containing `..` are rejected.

## Conventions

Full detail in [`docs/AUTHORING.md`](./docs/AUTHORING.md). The short version:

**Bundled files must be self-contained.** Installs are copied into a cache
directory, so anything shipped with a skill must be referenced through
`${CLAUDE_PLUGIN_ROOT}` — never `..`, an absolute path, or `~`. This applies to
bundled files only; a skill may still read and write paths in the repository it
runs in, which is what the learnings file and the scratch files are.

**Version lives in `plugin.json`, never in the marketplace entry.** Setting it in
both means the validator warns on drift and users can silently receive a stale
version. Bump the `plugin.json` `version` on every substantive change or
installed copies will not update.

**Invocation mode is a deliberate choice per skill**, set in `SKILL.md`
frontmatter:

| Frontmatter | You invoke | Claude invokes | Use for |
| --- | --- | --- | --- |
| *(none — default)* | Yes | Yes | Most skills |
| `disable-model-invocation: true` | Yes | No | Side effects that must stay manual — pushing, deploying, opening a PR |
| `user-invocable: false` | No | Yes | Background knowledge that isn't a meaningful command |

## Local development

Validate before pushing — at the root for the catalog, and per plugin directory
to check skill frontmatter:

```bash
claude plugin validate . --strict
claude plugin validate ./git-workflow --strict
```

Test a change without publishing by adding the working copy as a local
marketplace:

```bash
/plugin marketplace add ./claude-code-skills
/plugin install git-workflow@henryd-workflow
/reload-plugins
```

## Notes

- **Marketplace names are unique per user.** Registering another marketplace
  named `henryd-workflow` replaces this one.
- **Team and Enterprise organizations can restrict marketplaces.** If an admin
  has set `strictKnownMarketplaces`, this marketplace needs allowlisting before
  it can be added. Personal accounts are unaffected.

## License

MIT — see [LICENSE](./LICENSE).
