# Branching Models

Static reference for the `branch` skill. Every model described here behaves the same way in
every repository, which is why it ships with the plugin. **Which** model a repository uses
is a per-repository fact and belongs in that repository's learnings file.

Read this file only after the model has been resolved, then use the matching profile.

---

## Quick comparison

| | Trunk-Based | GitHub Flow | GitFlow |
| --- | --- | --- | --- |
| Long-lived branches | `main` only | `main` only | `main` **and** `develop` |
| Branch from | `main` | `main` | `develop`, `main` for hotfix |
| PR targets | `main` | `main` | `develop`, `main` for hotfix/release |
| Back-merge needed | No | No | **Yes**, after hotfix and release |
| Release branches | Optional, cut from trunk | None | Required, cut from `develop` |
| Expected branch life | Hours to 2 days | Days | Days to weeks |
| Vocabulary | `feat/`, `fix/`, `chore/` | `feat/`, `fix/`, `chore/` | `feature/`, `release/`, `hotfix/`, `bugfix/`, `support/` |

Trunk-Based and GitHub Flow are identical for base and target resolution. They differ in
branch lifetime, in whether release branches are legitimate, and in how work should be
sliced — see the planning notes in each profile.

---

## Trunk-Based Development

One shared trunk. Everything integrates into it continuously, and incomplete work ships
dark behind a feature flag rather than waiting on a branch.

| Branch type | Base | PR target | After merge |
| --- | --- | --- | --- |
| `feat/*`, `fix/*`, `chore/*` | `main` | `main` | — |
| `release/*` (optional) | `main` | No PR — stabilization only | Fixes land on `main` first, then cherry-pick onto the release branch |

**Never branch a release off a release.** Fixes always go to trunk first, then get picked
onto the release branch. Fixing on the release branch directly is how a fix gets lost from
the next release.

**Planning implications.** This is the model where plan shape matters most:

- Slice vertically, so every increment is independently mergeable and releasable.
- Anything that can't ship in one or two days goes behind a feature flag, not onto a
  long-lived branch.
- Wide refactors use a parallel-change sequence — add the new path, migrate callers, remove
  the old path — as separate merges, never one branch that lands them together.

If a plan produces a branch expected to live a week, the plan is wrong for this model, not
the model wrong for the plan. Say so before creating the branch.

**Common deviations.** Direct commits to `main` for trivial changes; no release branches at
all (which makes it GitHub Flow in practice).

---

## GitHub Flow

One `main` branch that is always deployable. One branch per change, reviewed by PR, merged,
deployed. No release branches and no `develop`.

| Branch type | Base | PR target | After merge |
| --- | --- | --- | --- |
| any | `main` | `main` | — |

**Planning implications.** Size each unit of work to one reviewable pull request. There is
no integration branch to stage partial work on, so a plan that needs three merges before
anything is usable should say so and sequence them explicitly.

**Common deviations.** A `staging` or `production` environment branch that `main` is
promoted into — that is GitLab Flow, and it changes the PR target for promotions only.
Record it as a deviation.

---

## GitFlow

Two permanent branches. `main` holds released code, `develop` holds the next release.
Everything else is temporary and has a prescribed base and target.

| Branch type | Base | PR target | After merge |
| --- | --- | --- | --- |
| `feature/*` | `develop` | `develop` | — |
| `bugfix/*` | `develop` | `develop` | — |
| `release/*` | `develop` | `main` | Tag `main`, then **back-merge `main` into `develop`** |
| `hotfix/*` | **`main`** | `main` | Tag `main`, then **back-merge `main` into `develop`** |
| `support/*` | a release tag | long-lived, no target | — |

**The back-merge is the load-bearing rule.** A hotfix based on `main` and merged to `main`
does not exist on `develop`. Without the back-merge the fix is silently absent from the next
release, and it reappears as the same bug weeks later. This is the most-forgotten step in
GitFlow, so state the obligation when creating a `hotfix/*` or `release/*` branch rather
than waiting until merge time.

**Hotfix branches are the only ones based on `main`.** Basing a hotfix on `develop` ships
unreleased work into production.

**Planning implications.** A feature branch may live for the duration of the feature, so a
plan can batch related work into one integration point. Two things a plan must decide up
front:

- **Which release the work targets** — the current `release/*` branch, or `develop` for the
  next one. Getting this wrong means rebasing across a release boundary later.
- **Whether this is a hotfix.** That's a separate lane with a different base, a different
  target, and the back-merge obligation.

**Common deviations**, all worth recording rather than fighting:

- No `release/*` branches — features merge to `develop`, which is released directly.
- `develop` renamed (`integration`, `dev`, `next`).
- `main` named `master` — still common in older repositories.
- Short prefixes (`feat/` instead of `feature/`) despite otherwise textbook GitFlow.

---

## Discovery signals

Resolve the model from the repository before asking the user. Strongest signal first.

| Signal | Command | Reading |
| --- | --- | --- |
| git-flow config | `git config --get-regexp '^gitflow\.'` | Near-conclusive. git-flow and git-flow AVH write `gitflow.branch.develop`, `gitflow.prefix.feature`, and friends |
| Long-lived branches | `git branch -a --sort=-committerdate` | A `develop` **with recent commits** plus any `release/*` or `hotfix/*` means GitFlow |
| CI triggers | `.github/workflows/*.yml` on `push: branches:` | A workflow keyed to `develop` or `release/*` proves those branches are real, not vestigial |
| Contributing guide | `CONTRIBUTING.md`, `docs/` | Teams often state the model outright |
| Branch protection | `gh api repos/{owner}/{repo}/branches/develop/protection` | A protected `develop` is a permanent integration branch |

**A stale `develop` is not GitFlow.** A branch last touched two years ago is an abandoned
experiment. Check recency before concluding, and weigh a CI trigger over mere existence.

**When signals conflict or none appear, ask.** One question, with what was found:

> I couldn't tell which branching model this repo uses. Trunk-based (branch from `main`,
> merge back to `main`), or GitFlow (`develop` for features, `main` for releases)?

Then offer to record the answer so it's asked once per repository, never again.

---

## Recording the result

The resolved model goes in the consuming repository's learnings file as a single entry:

```md
## Branching Model
**Model:** GitFlow
**Deviations:** No release branches; features merge to `develop`, which is released
directly. Integration branch is named `integration`.
**Why:** `gitflow.branch.develop` is set, and CI runs on `integration` and `main` only.
```

**`Model:` names one of the profiles above. `Deviations:` carries everything else.** Real
teams run "GitFlow without release branches" far more often than textbook GitFlow, so a
model name alone would force a wrong answer. Treat the profile as the default and the
deviations as overrides on top of it.

A model that can't be matched to a profile is recorded as the closest one plus deviations,
not as a new profile.
