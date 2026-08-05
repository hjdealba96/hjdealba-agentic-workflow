---
name: branch
description: >
  Create a git branch. Use this skill whenever the user asks to create a branch, make a branch,
  start a branch, cut a branch, switch to a new branch, or begin work on a feature, bug, or task —
  including "create a branch for...", "new branch for...", "switch to a branch...", "let's start
  working on...", "implement...", "build...". Also use it before executing any implementation plan
  that will need a branch. Never run `git checkout -b` or `git switch -c` directly; consult this
  skill first. Names branches to the Conventional Branch standard
  (https://conventional-branch.github.io/), reads the repository's existing branches so the name
  matches local convention, and asks for a ticket ID when the project tracks work that way.
allowed-tools: Bash, Read, Write
---

# Create Branch

Create git branches following the [Conventional Branch](https://conventional-branch.github.io/)
standard, so names stay consistent, scannable, and informative across a repository.

---

## Step 0: Load Project Learnings

Read `.claude/learnings/git-workflow/branch.md` from the repository root if it exists.

This file holds facts unique to **this repository** — the branching model, a required
ticket prefix, a non-standard type vocabulary, a separator convention, a base branch other
than the default. Apply anything relevant.

**If the file does not exist, proceed with defaults. Do not create it.** It is created
only when a learning is captured (see [Capturing Learnings](#capturing-learnings)).

The naming rules below are the global default. Learnings layer repository-specific facts on
top of them, and where a learning explicitly contradicts a default, **the learning wins** —
that's what makes one skill usable across repositories that disagree. A `## Branching Model`
entry is the clearest case: it replaces the default base branch and type vocabulary outright.

---

## Naming Rules

### Format

```
<type>/<description>
```

Trunk branches (`main`, `master`, `develop`) stand alone with no prefix.

### Types

| Type | Aliases | When |
| --- | --- | --- |
| `feature` | `feat` | New functionality |
| `bugfix` | `fix` | Bug corrections |
| `hotfix` | — | Urgent fixes needing immediate attention |
| `release` | — | Preparing a release version |
| `chore` | — | Non-code work: dependencies, docs, CI config |

Prefer the short aliases (`feat`, `fix`) when the repository doesn't already favor the
long forms — they're quicker to type and read in logs.

**The branching model can override this vocabulary.** GitFlow prescribes `feature/`,
`release/`, `hotfix/`, `bugfix/`, and `support/`, and those names carry base and target
rules the short aliases don't. Resolve the model in Step 1 before choosing a type.

### Description

- **Lowercase only** — `a-z`, `0-9`, hyphens between words
- **No underscores, spaces, or special characters**
- **No consecutive hyphens** (`--`), and no leading or trailing hyphen
- **Dots only in release branches**, for version numbers (`release/v1.2.0`). No
  consecutive dots, and no dot adjacent to a hyphen
- **Short but specific** — someone scanning `git branch` should know what it's for
- **Lead with the ticket number** when one exists — `feat/issue-42-add-login-page`

### Valid

```
feat/add-login-page
fix/header-alignment-bug
hotfix/security-patch
release/v1.2.0
chore/update-dependencies
feat/issue-123-new-login
```

### Invalid

```
Feature/Add-Login      # uppercase
feature/new--login     # consecutive hyphens
feature/-new-login     # leading hyphen
release/v1.-2.0        # hyphen adjacent to dot
fix/header_bug         # underscore
```

---

## Workflow

### Step 1: Resolve the Branching Model

The model decides what this branch is based on, which type names are legitimate, and whether
merging it later carries an obligation. Resolve it first — the later steps depend on it.

Resolve in this order, stopping at the first that answers:

1. **Project learnings** — a `## Branching Model` entry, read in Step 0.
2. **Discovery.** Strongest signal first:

   ```bash
   git config --get-regexp '^gitflow\.'
   git branch -a --sort=-committerdate | head -30
   ```

   `gitflow.*` keys are near-conclusive. Otherwise look for a `develop` **with recent
   commits**, alongside any `release/*` or `hotfix/*`. When the branch list is ambiguous,
   check whether CI treats those branches as real:

   ```bash
   grep -rl "develop\|release/" .github/workflows/ 2>/dev/null
   ```

   Keep this branch listing — Step 2 reads the same output.
3. **Ask the user.** Don't guess when the signals are thin or contradictory:

   > I couldn't tell which branching model this repo uses. Trunk-based (branch from `main`,
   > merge back to `main`), or GitFlow (`develop` for features, `main` for releases)?

Then read the matching profile from
`${CLAUDE_PLUGIN_ROOT}/skills/branch/reference/branching-models.md`. It carries the base branch, PR
target, vocabulary, and post-merge obligation for each model, plus the deviations worth
expecting.

**A stale `develop` is not GitFlow.** A branch untouched for a year is an abandoned
experiment — weigh recency and CI over mere existence.

**Confirm what you resolved** unless it came from learnings:

> This looks like GitFlow — `develop` is active and CI runs on `release/*`. I'll branch from
> `develop`. Correct?

When the model came from discovery or from the user, offer to record it (see
[Capturing Learnings](#capturing-learnings)) so the question is asked once per repository,
not once per branch.

### Step 2: Match the Repository's Existing Convention

Reusing the branch listing from Step 1, look at what the repository already does:

```bash
git branch -a --sort=-committerdate | head -30
```

If the history consistently uses a different type vocabulary, separator, or ticket
placement, **follow the repository over the defaults above** and offer to record it as a
learning.

Note two things from this output for Step 4:

- **Do branches carry ticket IDs?** A recurring `ABC-1234` or `issue-42` segment means
  this project tracks work by ticket.
- **Where does the ID sit** — immediately after the type (`feat/DRX-2360-add-search`) or
  somewhere else? Match the existing placement.

### Step 3: Determine the Type

Adding something new → `feat`. Fixing a bug → `fix`. Urgent production issue → `hotfix`.
Cutting a release → `release`. Maintenance, docs, or dependencies → `chore`.

Use the vocabulary the resolved model prescribes, in the casing and length the repository
already uses. Under GitFlow, `hotfix` and `release` are not stylistic choices — they change
the base branch and add a back-merge obligation, so pick them deliberately.

### Step 4: Resolve the Ticket ID

The ticket ID in a branch name is load-bearing: `commit` reads it to scope the commit, and
`open-pr` reads it to build the PR title and look up the ticket. Getting it in at branch
creation makes all three correct.

Resolve in this order:

1. **Learnings** — if the project requires a ticket ID, treat it as mandatory.
2. **The conversation** — a ticket ID the user already mentioned, or one visible in the
   task description.
3. **Ask, but only when the repository shows it uses tickets** (from Step 2) or learnings
   require it:

   > Does this work belong to a ticket? I'll include the ID in the branch name.
   > (Enter the ID, or say no.)

4. **Don't ask at all** when the repository's branches show no ticket IDs and learnings
   say nothing. Silence is the right default for projects that don't track that way.

**If the project requires an ID and the user doesn't have one,** say what it costs — the
commit scope and PR title will fall back to the code area — and let them proceed anyway.
Never block branch creation over a missing ticket, and never invent an ID.

When an ID is found, normalize it to the repository's casing convention and place it as
Step 2 observed, usually leading the description: `feat/DRX-2360-add-search-filters`.

### Step 5: Compose the Description

Distill the task into two to five hyphenated lowercase words, after the ticket ID if there
is one.

### Step 6: Validate

Check the proposed name against every rule above — no uppercase, no underscores, no
consecutive or edge hyphens, dots only in a release branch.

### Step 7: Confirm Before Creating

Present the name **and the base it will be cut from**, since the base is the part the user
can't see from the name alone:

> I'd like to create `feature/DRX-2360-add-user-search` from `develop` before we start. Does
> that look right?

### Step 8: Create It

Use the base the resolved model prescribes — **not** the repository's default branch, which
is wrong under GitFlow for everything except a hotfix. Refresh the base first so the branch
isn't cut from a stale local copy:

```bash
git fetch origin <base> --quiet
git checkout -b <branch-name> origin/<base>
```

If the base branch doesn't exist, stop and say so rather than silently falling back to the
default branch — a `hotfix/*` accidentally cut from `develop` ships unreleased work to
production.

If the working tree has uncommitted changes, point that out first — they will follow onto
the new branch.

**State any post-merge obligation now, not at merge time.** Under GitFlow, a `hotfix/*` or
`release/*` branch has to be back-merged into `develop` after it lands on `main`, or the
work is silently missing from the next release:

> Heads up: this is a hotfix, so after it merges to `main` it also needs to be back-merged
> into `develop`, or the fix won't be in the next release.

---

## Before Implementation Work

When the user asks you to implement something and code changes are imminent, check the
current branch:

```bash
git branch --show-current
```

If it's a long-lived branch for the resolved model (`main`, `master`, or `develop` under
GitFlow), suggest a conventional branch before starting. This keeps the integration branch
clean and makes the eventual PR reviewable.

**Always ask. Never switch branches silently.**

### Sizing the work to the model

The model constrains how the work should be sliced, and a mismatch is cheapest to catch
before the branch exists:

| Model | Expected shape |
| --- | --- |
| Trunk-Based | Independently mergeable increments of a day or two; anything longer ships dark behind a feature flag |
| GitHub Flow | One reviewable pull request per unit of work |
| GitFlow | May batch into a single integration point; decide up front whether it targets the current `release/*` or `develop` |

If the plan implies a branch that will live for weeks in a trunk-based repository, say so
before creating it and propose the first shippable slice instead. Per-model detail, including
the parallel-change sequence for wide refactors, is in
`${CLAUDE_PLUGIN_ROOT}/skills/branch/reference/branching-models.md`.

---

## Capturing Learnings

The naming rules above are global. **The learnings file is only for facts specific to one
repository.**

| Correction | Durable repo fact? |
| --- | --- |
| "We use GitFlow here" | Yes — record as `## Branching Model` |
| "Branch from `develop`, not `main`" | Yes — record as `## Branching Model`, not a standalone rule |
| "We don't cut release branches" | Yes — a deviation on the `## Branching Model` entry |
| "We use `bug/` not `fix/`" | Yes — repository convention |
| "Every branch needs the ticket ID" | Yes — repository convention |
| "We use `task/` for chores" | Yes — repository convention |
| "Call this one `search` instead" | No — one-off edit |

**Anything about bases, targets, or long-lived branches goes in the single
`## Branching Model` entry**, as a `Model:` plus `Deviations:`. Splitting it across separate
rules is how the file ends up with a base-branch rule that contradicts the model named two
entries above it.

For a durable fact, propose saving it:

```
That looks repo-specific. Save it to .claude/learnings/git-workflow/branch.md?

  ## Branching Model
  **Model:** GitFlow
  **Deviations:** No release branches; features merge to `develop`, which is
  released directly.
  **Why:** `gitflow.branch.develop` is set, and CI runs on `develop` and `main` only.

Save? (yes / no / edit)
```

**Append only on approval.** Create `.claude/learnings/git-workflow/` and the file if
needed, with this header:

```md
# Learnings — `/git-workflow:branch`

Repository-specific patterns for the `branch` skill. The skill reads this file before
proposing a branch name. The Conventional Branch rules live in the skill itself; only
facts unique to this repository belong here.

---
```

Entry format — a `##` title, then `**Rule:**` and `**Why:**`. Keep entries short. If a new
learning contradicts an existing one, update that entry rather than appending a duplicate.

---

## Error Handling

| Failure | Action |
| --- | --- |
| Branch name already exists | Report it; offer to switch to it or pick another name |
| Not a git repository | Stop and say so |
| Uncommitted changes present | Warn that they follow onto the new branch; continue on confirmation |
| Default branch can't be determined | Ask which branch to base from |
| Branching model can't be inferred | Ask the user; never assume trunk-based because `develop` is absent from the local clone |
| Model says `develop` but it doesn't exist | Stop; the model or the clone is wrong. Never fall back to the default branch silently |
| Discovery signals contradict learnings | Trust learnings, mention the discrepancy once, and offer to update the entry |
