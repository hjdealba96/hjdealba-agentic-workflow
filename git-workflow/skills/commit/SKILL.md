---
name: commit
description: >
  Generate a git commit message following the Conventional Commits 1.0.0 specification
  (https://www.conventionalcommits.org), then commit on approval. Use this skill whenever the user
  asks to commit changes, create a commit, save their work, or any variation of "commit this" —
  including /commit, "git commit", "commit my changes", "make a commit", "save my progress",
  "write a commit message", "draft a commit message". Analyzes the diff, infers scope from the
  ticket ID or code area, writes the message to a scratch file the user can edit, and commits with
  their exact bytes only after they approve. If the user mentions commits at all, consult this skill
  — including when the request is phrased as a direct git command such as "git commit these fixes".
  Never run `git commit` without consulting it.
allowed-tools: Bash, Read, Write
---

# Create Commit

Analyze the working tree, write a commit message to the **Conventional Commits 1.0.0**
specification, and commit it after the user approves.

The message is written to a scratch file outside the repository so the user can hand-edit
it before committing. The commit then uses that file's exact bytes.

---

## Step 0: Load Project Learnings

Read `.claude/learnings/git-workflow/commit.md` from the repository root if it exists.

This file holds facts unique to **this repository** — an established scope vocabulary, a
required trailer, a ticket-reference format. Apply anything relevant.

**If the file does not exist, proceed with defaults. Do not create it.** It is created
only when a learning is captured (see [Capturing Learnings](#capturing-learnings)).

The specification below is global and always in force. Learnings only add
repository-specific facts on top.

---

## Message Specification

### Structure

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

- **Header** — required, aim for 50 characters, hard limit 72
- **Body** — separated by a blank line, wrapped at 72 columns, explains the *why*
- **Footers** — separated by a blank line; `BREAKING CHANGE`, refs, trailers

### Type

| Type | When | SemVer |
| --- | --- | --- |
| `feat` | A new capability for the user | MINOR |
| `fix` | A bug fix | PATCH |
| `docs` | Documentation only | — |
| `style` | Formatting, whitespace — no logic change | — |
| `refactor` | Restructuring that neither fixes a bug nor adds a feature | — |
| `perf` | Performance improvement | — |
| `test` | Adding or updating tests | — |
| `build` | Build system or dependencies | — |
| `ci` | CI/CD configuration | — |
| `chore` | Maintenance that fits nothing above | — |

When a change spans types, pick the dominant intent. A commit that adds a feature and
fixes a bug along the way is `feat` if the feature is the point.

**Match the repository.** If `git log` shows the project uses `feature:` rather than
`feat:`, follow the project.

### Scope

Optional, lowercase, in parentheses, and ideally one word.

1. **Ticket ID, when one exists** and the project scopes by ticket —
   `fix(ABC-1234): align badge on payment cards`
2. **Otherwise the code area affected**, inferred from paths —
   `feat(checkout): add payment carousel`
3. **Omit** when the change is broad or the project doesn't use scopes.

Stay consistent with scopes already present in the history.

### Description

Imperative mood (`add`, `fix`, `remove` — never `added`, `fixes`). Lowercase after the
colon. No trailing period. State what changed, not how.

### Body

Include one when the *why* isn't obvious from the description. Wrap at 72 columns. Explain
motivation, contrast with previous behavior, note consequences. Backtick code references:
`TokenRefreshManager.refresh()`.

### Breaking changes

Signal with `!` after the type or scope, a `BREAKING CHANGE:` footer, or both:

```
feat(api)!: return paginated responses from /users

BREAKING CHANGE: clients must handle the new pagination wrapper
```

`!` alone is sufficient; the footer adds detail.

### Footers

`token: value`, with hyphens for multi-word tokens.

- `Refs: ABC-123` or `Closes #456` — link a ticket or issue
- `Co-Authored-By: Name <email>` — credit a co-author

If a ticket ID is inferable from the branch or conversation, add a `Refs:` footer. If none
is found and the project's history shows it normally carries one, ask once whether there's
a ticket to reference; don't block on the answer.

---

## Content Rules

1. **Describe only what the diff shows.** Never invent or assume a change.
2. **Imperative mood throughout.**
3. **Explain what and why, not how** — the code already shows how.
4. **Never reference plan or investigation files.** Extract the content instead.
5. **Human voice.** Write as the developer. Any attribution goes in a footer, not the prose.
6. **Never include secrets or PII** — no tokens, keys, credentials, emails, personal names,
   internal URLs, or connection strings. If the diff contains any, warn the user and stop
   before writing the message.

---

## Workflow

### Step 1: Read the Changes

Start compact and go deeper only when needed.

```bash
git status --porcelain
git diff --stat --ignore-cr-at-eol
git diff --ignore-all-space --ignore-blank-lines --ignore-cr-at-eol --stat=120 -U1 --no-color
```

`-U1` instead of the default `-U3` cuts diff tokens substantially with no real loss for
message-writing. Escalate to `-U2` on a specific file only when the change is genuinely
hard to read. Ignoring whitespace and `--ignore-cr-at-eol` keeps CRLF/LF churn from being
mistaken for real changes.

Also check what is already staged — if the user has staged a subset deliberately, commit
that subset rather than everything:

```bash
git diff --cached --stat --ignore-cr-at-eol
```

**Read recent history** to match the project's existing conventions:

```bash
git log --oneline -20
```

Scopes, type vocabulary, and trailer style already in use win over this skill's defaults.

**If there is nothing to commit,** say so plainly and stop — do not write a file.

### Step 2: Understand the Why

The diff shows *what* changed; it rarely shows *why*. Fill that in from the conversation:
if this session included planning, debugging, or implementing the work, extract the
motivation, the key decisions, and any constraint worth recording.

**Extract the substance, never the reference.** Do not cite plan files, investigation
notes, or ticket-tracker documents in the message ("as per plan.md", "see the
implementation plan"). Those paths are frequently gitignored and meaningless to anyone
reading `git log` later. Pull the two or three points that matter into the body in your own
words.

If the motivation genuinely isn't inferable, ask briefly rather than guessing.

### Step 3: Compose the Message

Apply the [Message Specification](#message-specification) and [Content Rules](#content-rules)
above.

### Step 4: Present for Review

Write the message to a scratch file outside the repository:

```bash
mkdir -p "${TMPDIR:-/tmp}/claude-git-workflow"
```

Write to `${TMPDIR:-/tmp}/claude-git-workflow/commit-message.md`.

Display the message inline, give the path, and ask:

> Ready to commit, or would you like changes? You can also edit the file directly.

Revise and re-present until approved.

### Step 5: Commit

Only after explicit approval.

1. Stage — `git add -A`, or leave staging alone if the user had deliberately staged a subset
2. Re-read the scratch file so manual edits are picked up
3. Commit with the file, never an inline message:

```bash
git commit -F "${TMPDIR:-/tmp}/claude-git-workflow/commit-message.md"
```

`-F` guarantees the commit uses exactly what the user approved or edited. Never use `-m`.

4. Confirm: report the short SHA and the branch.

**Do not push.** Pushing is a separate, explicit action.

---

## Examples

Simple:

```
fix: prevent duplicate API calls on retry
```

Scoped by code area:

```
feat(auth): add OAuth2 PKCE flow support
```

With body:

```
refactor(db): extract connection pooling into shared module

The pool configuration was duplicated across three services.
Centralizing it reduces drift and makes pool size tunable in
one place.
```

Scoped by ticket, with a ref:

```
fix(ABC-2888): align badge on saved payment cards

The badge used a fixed top offset, which drifted on cards with
two-line titles. Anchor it to the card header instead.

Refs: ABC-2888
```

Breaking:

```
feat(api)!: return paginated responses from /users

The endpoint now returns `{ data: [], meta: { page, totalPages } }`
instead of a flat array.

BREAKING CHANGE: clients must update to handle the pagination wrapper
```

---

## Capturing Learnings

The specification above is global. **The learnings file is only for facts specific to one
repository.**

| Correction | Durable repo fact? |
| --- | --- |
| "We use `feature:` not `feat:`" | Yes — repository convention |
| "Scope by ticket ID, always" | Yes — repository convention |
| "Every commit needs a `Refs:` trailer" | Yes — repository convention |
| "Our scopes are `app`, `domain`, `data`" | Yes — repository convention |
| "Make this body shorter" | No — one-off edit |
| "Call it `search` not `fuelsearch` here" | No — one-off edit |

For a durable fact, propose saving it:

```
That looks repo-specific. Save it to .claude/learnings/git-workflow/commit.md?

  ## Type Vocabulary
  **Rule:** Use `feature:` rather than `feat:`.
  **Why:** Matches the existing history in this repository.

Save? (yes / no / edit)
```

**Append only on approval.** Create `.claude/learnings/git-workflow/` and the file if
needed, with this header:

```md
# Learnings — `/git-workflow:commit`

Repository-specific patterns for the `commit` skill. The skill reads this file before
generating a commit message. The Conventional Commits specification lives in the skill
itself; only facts unique to this repository belong here.

---
```

Entry format — a `##` title, then `**Rule:**` and `**Why:**`. Keep entries short. If a new
learning contradicts an existing one, update that entry rather than appending a duplicate.

---

## Error Handling

| Failure | Action |
| --- | --- |
| Nothing to commit | Say so plainly and stop; write no file |
| Sensitive data in diff | Stop immediately and warn |
| Pre-commit hook rejects | Report the hook output; offer to fix and retry |
| Not a git repository | Stop and say so |
| Merge conflict markers in diff | Stop; ask the user to resolve first |
