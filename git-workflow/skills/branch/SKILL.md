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

This file holds facts unique to **this repository** — a required ticket prefix, a
non-standard type vocabulary, a separator convention, a base branch other than the
default. Apply anything relevant.

**If the file does not exist, proceed with defaults. Do not create it.** It is created
only when a learning is captured (see [Capturing Learnings](#capturing-learnings)).

The naming rules below are global and always in force. Learnings only add
repository-specific facts on top.

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

### Step 1: Match the Repository's Existing Convention

Before proposing anything, look at what the repository already does:

```bash
git branch -a --sort=-committerdate | head -30
```

If the history consistently uses a different type vocabulary, separator, or ticket
placement, **follow the repository over the defaults above** and offer to record it as a
learning.

Note two things from this output for Step 3:

- **Do branches carry ticket IDs?** A recurring `ABC-1234` or `issue-42` segment means
  this project tracks work by ticket.
- **Where does the ID sit** — immediately after the type (`feat/DRX-2360-add-search`) or
  somewhere else? Match the existing placement.

### Step 2: Determine the Type

Adding something new → `feat`. Fixing a bug → `fix`. Urgent production issue → `hotfix`.
Cutting a release → `release`. Maintenance, docs, or dependencies → `chore`.

### Step 3: Resolve the Ticket ID

The ticket ID in a branch name is load-bearing: `commit` reads it to scope the commit, and
`open-pr` reads it to build the PR title and look up the ticket. Getting it in at branch
creation makes all three correct.

Resolve in this order:

1. **Learnings** — if the project requires a ticket ID, treat it as mandatory.
2. **The conversation** — a ticket ID the user already mentioned, or one visible in the
   task description.
3. **Ask, but only when the repository shows it uses tickets** (from Step 1) or learnings
   require it:

   > Does this work belong to a ticket? I'll include the ID in the branch name.
   > (Enter the ID, or say no.)

4. **Don't ask at all** when the repository's branches show no ticket IDs and learnings
   say nothing. Silence is the right default for projects that don't track that way.

**If the project requires an ID and the user doesn't have one,** say what it costs — the
commit scope and PR title will fall back to the code area — and let them proceed anyway.
Never block branch creation over a missing ticket, and never invent an ID.

When an ID is found, normalize it to the repository's casing convention and place it as
Step 1 observed, usually leading the description: `feat/DRX-2360-add-search-filters`.

### Step 4: Compose the Description

Distill the task into two to five hyphenated lowercase words, after the ticket ID if there
is one.

### Step 5: Validate

Check the proposed name against every rule above — no uppercase, no underscores, no
consecutive or edge hyphens, dots only in a release branch.

### Step 6: Confirm Before Creating

Present the name and wait:

> I'd like to create `feat/DRX-2360-add-user-search` before we start. Does that look right?

### Step 7: Create It

```bash
git checkout -b <branch-name>
```

Branch from the repository's default branch unless learnings or the user say otherwise. If
the working tree has uncommitted changes, point that out first — they will follow onto the
new branch.

---

## Before Implementation Work

When the user asks you to implement something and code changes are imminent, check the
current branch:

```bash
git branch --show-current
```

If it's a trunk branch (`main`, `master`, `develop`), suggest a conventional branch before
starting. This keeps trunk clean and makes the eventual PR reviewable.

**Always ask. Never switch branches silently.**

---

## Capturing Learnings

The naming rules above are global. **The learnings file is only for facts specific to one
repository.**

| Correction | Durable repo fact? |
| --- | --- |
| "We use `bug/` not `fix/`" | Yes — repository convention |
| "Every branch needs the ticket ID" | Yes — repository convention |
| "Branch from `develop`, not `main`" | Yes — repository convention |
| "We use `task/` for chores" | Yes — repository convention |
| "Call this one `search` instead" | No — one-off edit |

For a durable fact, propose saving it:

```
That looks repo-specific. Save it to .claude/learnings/git-workflow/branch.md?

  ## Branch Types
  **Rule:** Use `bug/` rather than `fix/`, and `task/` rather than `chore/`.
  **Why:** Matches the existing branches and the CI target-branch rules.

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
