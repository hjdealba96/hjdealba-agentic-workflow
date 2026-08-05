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

## Execution Contract

**This procedure is not advisory. Every step runs, in order, on every invocation.**

The *content* is negotiable — title wording, which sections appear, how much detail,
labels, reviewers. The *procedure* is not.

| Rule | |
| --- | --- |
| Steps 0–6 run **in order, every time** | Including for a one-commit branch or a docs-only change |
| No step is skipped for being "obvious" | A small PR is where an unmeasured title and a missing footer slip through |
| Each gate produces **evidence** | Not a claim that it was done — the [preflight block](#preflight-block--required) prints what was found |
| A failed gate stops the run | Fix it and re-check. Never proceed past it, and never report it as passed |

### The six gates

| Gate | Step | Cannot proceed until |
| --- | --- | --- |
| **Learnings read** | 0 | `.claude/learnings/git-workflow/open-pr.md` has been read, or confirmed absent |
| **Target resolved** | 1 | The target branch was *discovered* — from learnings, `gh repo view`, or the user — never assumed to be `main` |
| **Diff read** | 2 | `origin/<target>` was fetched and the diff read against it, this run |
| **Secrets scanned** | 2 | The diff has been scanned for the values listed under [Security and Privacy](#security-and-privacy) |
| **Title measured** | 5 | The title's character count has been *counted*, not estimated. The 72-character target is soft; taking and reporting the measurement is not |
| **Footer present** | 5 | The scratch file's last line has been checked for the [footer](#footer) |
| **User approved** | 6 | The user has approved this exact title and body |

### What a user instruction can and cannot change

| The user can | The user cannot |
| --- | --- |
| Change the title, any section, the labels, the reviewers, draft status | Skip the diff read, the secrets scan, the title measurement, or the scratch file |
| Pre-approve: "open it without showing me" counts as the Step 6 approval, and the preflight block is still reported | Get a `--body` with inline text; the body always comes from the file, via `--body-file` |
| Override conventions durably through [learnings](#capturing-learnings) | Have a PR opened against an unverified target branch |
| Decline the `.gitignore` entry | Have content described that the diff doesn't support |

**Why this skill in particular.** It writes to a real remote, where a mistake is public and
often notification-generating. A commit can be amended in silence; a PR cannot.

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

Six of these steps carry a gate that must produce evidence before the next step begins —
see the [Execution Contract](#execution-contract).

---

### Step 1: Verify Repository and Branch

**Working tree state**

```bash
git status --porcelain
git branch --show-current
```

If uncommitted changes exist, tell the user and ask whether to commit first. Do not
proceed with a PR that silently omits their work unless they say to ignore it.

A leftover `claude-git-workflow/` from an earlier run is a working file, not work to
commit — if it appears here, the repository is missing the `.gitignore` entry proposed in
Step 5. Say so and move on; don't offer to commit it.

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
than a diff can. Lean on it for the Description.

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

**Discover the title convention.** Read what this repository's PR titles actually look
like before composing one:

```bash
gh pr list --state all --limit 20 --json title --jq '.[].title'
```

The existing titles win over this skill's default format. If they are Conventional-Commits
style (`fix(scope): lowercase description`), match that; if they lead with a ticket ID,
match that. A skill-shaped title in a repository that uses a different shape is noise in
the PR list, and the PR list is the one place titles are read side by side.

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

**Visual reference.** If the diff touches UI, ask whether to include a
`## Visual Reference` section. When the change modifies existing UI, use a before/after
table; when it is entirely new, a single column is enough.

The name is deliberately broader than "Screenshots": a screen recording of an interaction,
a short clip of an animation, or a before/after of a generated artifact are often the only
honest way to show the change. A still frame can't show a transition.

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

Write the proposed PR to a scratch file in `claude-git-workflow/` at the **repository
root**, where it sits beside the code and is easy to open and edit:

```bash
mkdir -p "$(git rev-parse --show-toplevel)/claude-git-workflow"
```

Write to `claude-git-workflow/pr-content.md`. Resolve the path from
`git rev-parse --show-toplevel` rather than the current directory — the skill may be
invoked from a subdirectory, and the file belongs at the root either way.

#### Keep the directory out of version control

`claude-git-workflow/` holds working files, never repository content. Check whether it is
already ignored:

```bash
git check-ignore -q claude-git-workflow && echo ignored
```

If it is not ignored, propose the entry once — typically the first time a `git-workflow`
skill runs in a repository:

> `claude-git-workflow/` isn't in `.gitignore`. Add it so these working files never get
> committed? (yes / no)

**Add it only on approval**, appending `claude-git-workflow/` to the root `.gitignore` and
creating that file if it doesn't exist. Don't re-ask on later runs once the entry exists.

If the user declines, say plainly that the file will show as an untracked change until they
remove it, and let them decide whether to proceed.

Show the user the path, display the content inline, and explain they can edit the file
directly before approving. **Do not create the PR in this step.**

#### Title

Use the shape the repository already uses, discovered in Step 2. Absent any history to
match, default to Conventional-Commits style, so the PR title and the commits under it
read the same way:

```
type(scope): short description
```

Imperative mood (`add login flow`, not `added login flow`). Types: `feat`, `fix`, `docs`,
`refactor`, `style`, `test`, `chore`, `perf`, `ci`.

When a ticket ID exists and the project prefixes titles with it, use
`ABC-123: Exact ticket name` instead, applying any normalization rule from learnings.

##### Length — measured, not estimated

| Limit | Value | Firmness | Why |
| --- | --- | --- | --- |
| Target | **72 characters**, whole title including any prefix | Soft | Matches the commit header's absolute limit, so a PR and its commit can share a line. Past this, GitHub truncates in the PR list, notification emails, and the merge-commit subject |
| Hard cap | **256 characters** | Hard | GitHub's own limit; a title this long has already failed |

**Taking the measurement is mandatory. The 72 is not a wall.**

```bash
TITLE="feat(commit): enforce line widths and step gates"
printf '%s' "$TITLE" | awk '{ printf "title %d/72\n", length }'
```

Over 72, try to shorten first — the detail belongs in the body, which has no such limit.
Preserve the type, scope, and any ticket ID while trimming; those are what make the title
scannable.

If it still doesn't fit, **an over-length title may ship**, on one condition: report the
count and say in a line why it stands. A ticket name reproduced verbatim is a reason. A
scope that is genuinely long is a reason. "It reads better" is not — that's the case where
the body should be carrying the words.

This is the one soft limit in the skill, and deliberately so: unlike a commit header, a PR
title sometimes has to mirror an external system exactly. What is never optional is
knowing the number before deciding.

```
✗ fix(docs-workflow): stop instead of reconstructing an unreadable bundled file  (77)
✓ fix(docs-workflow): stop on an unreadable bundled file                         (54)
```

The rejected title is not wrong, only unread — the part explaining the behavior change
gets truncated in exactly the views where someone is scanning for it.

#### Description structure (when no template exists)

```md
## Description

[1–3 sentences: what this does and why it matters]

## Changes Made

- [Specific change, named concretely]
- [Specific change, named concretely]

## How to Test

1. [Step a reviewer can actually follow]
2. [What they should see]

## Related Issues

[Closes #123 — or omit]
```

**Only Description is mandatory.** Every other section must earn its place:

- **Changes Made** — omit when the change is a single thing the Description already
  states. Two sections saying the same thing is worse than one.
- **How to Test** — omit only when there is genuinely nothing to run or look at. This is
  the most-skipped and most-valuable section in a PR: it is the difference between a
  reviewer verifying behavior and a reviewer guessing at it. Never pad it with "visual
  inspection" or "N/A" — no section beats a hollow one.
- **Related Issues** — omit when there is no ticket. Never invent one.

**Be specific in Changes Made.** "Added rate limiting middleware to the `/api/auth`
endpoint" is a review aid; "updated files" and "improved the code" are not. If a bullet
would read the same on any other PR, it isn't saying anything.

##### Sections to add by change type

The base structure is a floor, not a ceiling. What a reviewer needs varies by what kind of
change this is:

| Change type | Add |
| --- | --- |
| Bug fix | `## Root Cause` — what actually caused it, not just what was changed — and `## Regression Risk` |
| Hotfix | `## Severity`, `## Incident` link, `## Rollback Plan`. Keep everything else minimal; urgency is the point |
| New feature | `## Visual Reference` when there is UI — screenshot, recording, or clip — and a `## Feature Flag` note when it ships dark |
| Breaking change | `## Breaking Changes` and `## Migration Guide`, stating what consumers must do |
| API change | A request/response table showing before and after |
| Performance | The measurement — before and after numbers, and how they were taken |

**No generic checklist in a generated body.** "Self-reviewed the code", "tests pass",
"follows style guidelines" — a checkbox you tick about your own work carries no
information, and this skill's [gates](#the-six-gates) already cover that ground.
A checklist earns its place in a repository's *template*, where a human ticks it; not in
a description this skill writes.

**Keep it short enough that it doesn't read as homework.** A description nobody finishes
is worth less than three honest sentences.

#### Writing principles

**Lead with significance.** The first thing read should be the most important change,
never boilerplate or a minor fix.

**Write for a mixed audience.** A product manager should follow the Description. A
developer should find enough detail below it to review properly. This is neither a design
doc nor a commit log.

**Give the reviewer the intent.** Without it they reverse-engineer the diff line by line
to work out why the change exists, which takes far longer and still guesses. One sentence
of intent replaces that entirely.

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

**Check it rather than trusting it** — this is the single easiest line in the procedure to
drop, and a missing footer is invisible until someone audits the PR list:

```bash
PR="$(git rev-parse --show-toplevel)/claude-git-workflow/pr-content.md"
tail -1 "$PR" | grep -q 'Generated with \[Claude Code\]' \
  && echo "footer present" || echo "FOOTER MISSING"
```

#### Preflight block — required

Display the title and body inline, give the path, and print the preflight block. Six
lines, this order, every run — it is the evidence that each [gate](#the-six-gates)
actually ran, and it is what makes a skipped step visible instead of silent:

```
learnings   none            (or: 2 rules applied)
target      main            (gh repo view · 1 commit ahead · push needed)
template    none found      (or: .github/PULL_REQUEST_TEMPLATE.md — 6 sections)
title       48/72          (over target: "84/72 — ticket name verbatim")
secrets     scanned, none found
footer      present
```

Report what happened, never what should have happened. `learnings none` means the file
was looked for and absent — not that it wasn't checked. If a line can't be filled in
honestly, the step it reports on didn't finish; go finish it.

---

### Step 6: Confirm and Submit

Ask:

> Review the content above (or edit `<path>` directly). Ready to open the PR?

Wait for an explicit answer. **Silence is not approval, and approval of an earlier
revision is not approval of the current one.** If changes are requested, revise, re-run
the title and footer checks, reprint the preflight block, and re-confirm.

**Once approved:**

1. Push if needed — `git push -u origin <branch>`
2. Re-read the scratch file so any manual edits are picked up
3. Create the PR:

```bash
gh pr create \
  --title "..." \
  --base "<target>" \
  --body-file "$(git rev-parse --show-toplevel)/claude-git-workflow/pr-content.md" \
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
reviewers, writing a learnings entry, adding the `.gitignore` entry.

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
| Title over 72 | Try shortening into the Description first. If it stands, report the count and one line of why — never let it pass unremarked |
| Title over 256 | Hard failure. Shorten it; `gh` will reject it anyway |
| Footer check prints `FOOTER MISSING` | Append it and re-check. Never report the gate as passed |
| Asked to open the PR without a review step | Run Steps 0–5, print the preflight block, open it — treat the request as pre-approval, not as permission to skip |
| Asked to pass the body with `--body` | Decline that one detail, say why in a sentence (`--body-file` preserves the user's exact bytes), and use the file |
| Repository template exists but a section doesn't apply | Omit the section or say briefly why it doesn't apply. Never leave a heading with "N/A" under it |

For any blocking error, state plainly what failed and what the user needs to do.
