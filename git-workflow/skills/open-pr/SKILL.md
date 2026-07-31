---
name: open-pr
description: >
  Open a GitHub pull request with a clear, stakeholder-readable description. Use this skill
  whenever the user asks to create, open, or submit a pull request (PR), merge request, or says
  things like "open a PR", "create a PR", "send this to main", "PR this", or any variation of
  requesting a pull request — even without the exact words "pull request". Do NOT use this skill
  for code-review requests such as "submit this for review", "review this code", or "take a look
  at my changes"; those ask for a review of the code, not for a pull request to be opened.
  Follows a strict sequential workflow: verify the branch, gather context, determine status,
  choose sections and labels, generate content for review, and submit only after confirmation.
  Discovers the target branch, PR template, and available labels from the repository rather than
  assuming them. Assumes all changes are already committed.
allowed-tools: Bash, Read, Write, Glob, Grep
disable-model-invocation: true
---

# Open Pull Request

Create a GitHub pull request whose description serves both the developer reviewing the
code and the non-technical stakeholder skimming it.

**This skill assumes all changes are already committed.** Uncommitted changes are
reported but not included.

**This skill opens a real pull request on a real remote.** It is manual-invocation only,
and it never creates the PR without explicit approval in the final step.

**Discover, never assume.** This skill runs in any repository, so every project-specific
fact — target branch, label vocabulary, description structure, reviewer group, ticket
system — is discovered at runtime or read from learnings, never hardcoded. When something
can't be discovered, ask the user, then offer to record the answer so the question isn't
repeated.

---

## Step 0: Load Project Learnings

Read `.claude/learnings/git-workflow/open-pr.md` from the repository root if it exists.

This file holds facts unique to **this repository** — target branch overrides, reviewer
groups, ticket-title normalization rules, required description sections. Apply anything
relevant throughout the remaining steps.

**If the file does not exist, proceed with defaults. Do not create it.** It is created
only when a learning is actually captured (see [Capturing Learnings](#capturing-learnings)).

Global conventions — how to write a good PR description, security rules, formatting —
live in this skill and are always in force. Learnings only add repository-specific facts
on top.

---

## Security and Privacy

**Never include in any PR title, description, or comment:**

- Names or personal identifiers
- Email addresses
- Tokens, API keys, credentials, or passwords
- Private keys or certificates
- PII of any kind
- Internal URLs, IP addresses, or environment-specific endpoints
- Database connection strings

Before generating content, scan the diff for these. **If any appear, warn the user
immediately and stop.** Never echo a sensitive value into the PR, even when it is already
visible in the diff — describe it generically instead ("update API endpoint
configuration", never "update API key to sk-abc123...").

---

## Line Endings

All git operations must ignore CRLF/LF differences. Use `--ignore-cr-at-eol` on diff
commands. Only report a sync problem when actual content differs, not when line endings
alone do.

---

## Workflow

**Follow these steps in strict sequential order. Complete each fully before starting the
next. Do not skip, combine, or reorder them.**

```
0. Load learnings            4. Determine sections and labels
1. Verify repository/branch  5. Generate content for review
2. Gather context            6. Confirm and submit
3. Determine PR status
```

---

### Step 1: Verify Repository and Branch

**Working tree state**

```bash
git status --porcelain
git branch --show-current
```

If uncommitted changes exist, tell the user and ask whether to commit first. Do not
proceed with a PR that silently omits their work unless they say to ignore it.

**Remote tracking**

```bash
git rev-parse --abbrev-ref @{upstream} 2>/dev/null
```

- No upstream → the branch must be pushed in Step 6. Note it and continue.
- Upstream exists but is behind → note that a push is needed.
- Diverged with real content differences → stop and ask the user to reconcile.

**Detect the target branch.** Resolve in this order, stopping at the first that answers:

1. **Project learnings** — an explicit target-branch rule for this repository.
2. **Branch-prefix convention**, if learnings define one (for example `hotfix/*` → a
   production branch while everything else targets an integration branch).
3. **The repository default branch:**
   ```bash
   gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
   ```
4. **Ask the user** if all of the above fail.

Always present the result and confirm:

> Target branch will be `<detected>`. Is that correct?

If the user corrects it, apply the correction and offer to save it as a learning.

**Stop conditions.** Report the problem and halt if the target branch does not exist,
`gh` is not authenticated, or a git command fails outright.

---

### Step 2: Gather Context

Two sources matter, and they answer different questions.

**Conversation context — the "why."** If this session included planning, implementing, or
debugging the work, that history explains intent, decisions, and tradeoffs far better
than a diff can. Lean on it for the Summary.

**Git context — the "what."** First refresh the target ref, then compare against
the **remote** target. A stale local copy of the target branch produces a commit
list and diff that won't match what the PR actually shows:

```bash
git fetch origin <target> --quiet
```

These four are independent; run them in parallel:

```bash
git log origin/<target>..HEAD --format="%h - %s%n%n%b%n---"
git log origin/<target>..HEAD --stat --oneline
git diff origin/<target>...HEAD --stat --ignore-cr-at-eol
git diff --name-status origin/<target>...HEAD --ignore-cr-at-eol
```

If the remote isn't named `origin`, resolve it with `git remote` and substitute.

Read the full diff as well when the change is small enough to warrant it.

**When the two disagree, trust the diff for what changed and the conversation for why.**

**Discover the PR template**

```bash
ls .github/PULL_REQUEST_TEMPLATE.md .github/pull_request_template.md \
   docs/PULL_REQUEST_TEMPLATE.md .github/PULL_REQUEST_TEMPLATE/ 2>/dev/null
```

If a template exists, **its structure wins** over this skill's default structure. Fill
every section that applies. For sections that genuinely don't apply — a test plan on a
docs-only change — omit the section or note briefly why it isn't applicable, rather than
padding it with "N/A".

**Extract from the changes**

- **Ticket ID** — from the branch name or commit prefixes (`ABC-123`, `#456`)
- **Change type** — feature, fix, refactor, chore, from branch prefix and commits
- **Affected areas** — inferred from file paths
- **Business impact** — from commit bodies and the conversation

If a ticket ID is found and the project uses a tracker the environment can reach, fetch
the title so the PR title stays consistent with the ticket. Apply any title-normalization
rule from learnings. If the lookup fails, ask:

> I found ticket `ABC-123` but couldn't fetch its title. What is the exact ticket name?

**Never invent a ticket ID.** If none is present, don't fabricate one.

---

### Step 3: Determine PR Status

Ask:

> Should this be a draft, or ready for review?

This governs reviewers and labels downstream. Drafts get no reviewers.

---

### Step 4: Determine Sections and Labels

**Visual reference.** If the diff touches UI, ask whether to include a visual section.
When the change modifies existing UI, use a before/after table; when it is entirely new,
a single column is enough.

```md
| **Before** | **After** |
|---|---|
| 📸 *screenshot* | 📸 *screenshot* |
```

**Labels — never auto-apply.** Read the repository's actual label vocabulary:

```bash
gh label list --limit 100
```

Propose only labels that exist in the repo, each with a one-line rationale, then ask:

```
Suggested labels:
  [x] bug        — fixes incorrect tax calculation
  [x] backend    — changes confined to the API layer
  [ ] breaking   — not detected

Apply these, modify, or skip?
```

If learnings define labels that are always applied for a given PR status, apply those
automatically and say so.

**Reviewers.** Ask who should review unless learnings specify a default group. Never add
reviewers to a draft.

---

### Step 5: Generate Content for Review

Write the proposed PR to a scratch file **outside the repository**, so it never dirties
`git status` and needs no `.gitignore` entry:

```bash
mkdir -p "${TMPDIR:-/tmp}/claude-git-workflow"
```

Write to `${TMPDIR:-/tmp}/claude-git-workflow/pr-content.md`.

Show the user the path, display the content inline, and explain they can edit the file
directly before approving. **Do not create the PR in this step.**

#### Title

```
Type: Short description
```

Capitalize the type; keep the description under 60 characters, imperative mood
(`Add login flow`, not `Added login flow`). Types: `Feat`, `Fix`, `Docs`, `Refactor`,
`Style`, `Test`, `Chore`, `Perf`, `Ci`.

When a ticket ID exists and the project prefixes titles with it, use
`ABC-123: Exact ticket name` instead, applying any normalization rule from learnings.

Hard limit: 256 characters. If the ticket name would exceed it, shorten the description
while preserving the ID and the core meaning.

#### Description structure (when no template exists)

```md
## Summary

[1–3 sentences: what this does and why it matters]

## Changes

### Primary
- [The main change — what the PR is fundamentally about]

### Secondary
- [Supporting changes made alongside it]

### Technical Notes
- [Implementation details that help a reviewer, or carry consequences]

## Visual Reference
[Only if requested in Step 4]

## Test Plan
[Only when there is something behavioral to verify]
```

**Only Summary is mandatory.** Every other section must earn its place:

- **Secondary** — omit when there is one logical change.
- **Technical Notes** — omit for docs, config, or anything with no technical implication.
- **Test Plan** — omit entirely for changes with no behavioral impact. Never write filler
  like "N/A" or "visual inspection."

Add sections beyond this set when they genuinely help — `## Migration Guide`,
`## API Changes`, `## Breaking Changes`.

#### Writing principles

**Lead with significance.** The first thing read should be the most important change,
never boilerplate or a minor fix.

**Write for a mixed audience.** A product manager should follow the Summary. A developer
should find enough detail below it to review properly. This is neither a design doc nor a
commit log.

**Be specific, not verbose.** "Add pagination to search results" beats "Updated the search
functionality to include the ability to paginate through results." Say what changed, not
that something changed.

**Group by logical change, not by file.** Fifteen files that form three changes get
described as three changes.

**Document only what actually changed.** Base every claim on the diff, the commits, or the
conversation. Never describe work that isn't there.

**Use rich formatting where it earns its place** — tables for before/after or mapping
comparisons, links to tickets and docs, code snippets only for an API or config change,
lists for enumerated changes. Formatting is for clarity, not decoration.

**Human voice in the body.** Do not scatter AI-attribution phrases through the
description. Attribution belongs only in the footer below, once.

**Never reference internal planning artifacts.** Plan files, investigation notes, and
execution summaries are engineering-internal and frequently gitignored — a reviewer
following that path finds nothing. If the context matters, write it inline in the
description or link the ticket.

#### Footer

End the body with exactly this line, verbatim, separated by a blank line:

```md
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

### Step 6: Confirm and Submit

Ask:

> Review the content above (or edit `<path>` directly). Ready to open the PR?

Wait for an explicit answer. If changes are requested, revise and re-confirm.

**Once approved:**

1. Push if needed — `git push -u origin <branch>`
2. Re-read the scratch file so any manual edits are picked up
3. Create the PR:

```bash
gh pr create \
  --title "..." \
  --base "<target>" \
  --body-file "${TMPDIR:-/tmp}/claude-git-workflow/pr-content.md" \
  --assignee @me \
  [--draft] [--label "..."] [--reviewer "..."]
```

Use `--body-file`, never `--body` with inline text, so the user's edits are used exactly
as written.

4. Report the PR URL, base branch, draft status, and any labels and reviewers applied.

**The PR may only be created after explicit approval in this step.**

---

## Permitted and Prohibited Actions

**Permitted without asking:** reading git state, reading the PR template, listing labels,
generating the scratch file, suggesting titles and labels, verifying branch sync.

**Requires explicit approval:** creating the PR, pushing a branch, applying labels, adding
reviewers, writing a learnings entry.

**Never:** open a PR without confirmation, auto-apply labels, add reviewers to a draft,
modify or merge code, include sensitive values, proceed on a diverged branch.

---

## Capturing Learnings

Global conventions belong in this skill. **The learnings file is only for facts specific
to one repository.**

When the user corrects something, first decide which it is:

| Correction | Durable repo fact? |
| --- | --- |
| "Target `develop`, not `main`" | Yes — repository convention |
| "Always request the `platform-team` group" | Yes — repository convention |
| "Strip `Android:` from ticket titles" | Yes — repository convention |
| "This repo needs a Rollout Plan section" | Yes — repository convention |
| "Make this summary shorter" | No — one-off edit |
| "Drop the second bullet" | No — one-off edit |

Only for a durable fact, propose saving it:

```
That looks repo-specific. Save it to .claude/learnings/git-workflow/open-pr.md?

  ## Target Branch
  **Rule:** PRs target `develop`. Hotfix branches target `master`.
  **Why:** `main` is release-only in this repository.

Save? (yes / no / edit)
```

**Append only on approval.** Create `.claude/learnings/git-workflow/` and the file if
needed, using this header:

```md
# Learnings — `/git-workflow:open-pr`

Repository-specific patterns for the `open-pr` skill. The skill reads this file before
generating PR content. Global conventions live in the skill itself; only facts unique to
this repository belong here.

---
```

Entry format — a `##` title, then `**Rule:**` and `**Why:**`, plus `**When:**` if it is
conditional. Keep entries short and factual. If a new learning contradicts an existing
one, update that entry rather than appending a duplicate.

The file is committed, so it benefits the whole team.

---

## Error Handling

| Failure | Action |
| --- | --- |
| `gh` not authenticated | Tell the user to run `gh auth login`, then stop |
| Target branch missing | Ask for a valid target |
| Branch not pushed | Offer to push in Step 6 |
| Branch diverged | Stop; ask the user to reconcile |
| Ticket lookup failed | Ask for the ticket name |
| No labels in repo | Skip labeling; mention it |
| `gh pr create` failed | Report the error; check whether the PR was partly created |
| Sensitive data in diff | Stop immediately and warn |

For any blocking error, state plainly what failed and what the user needs to do.
