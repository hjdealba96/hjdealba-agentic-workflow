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

The message is written to a scratch file at the repository root so the user can hand-edit
it before committing. The commit then uses that file's exact bytes.

---

## Execution Contract

**This procedure is not advisory. Every step runs, in order, on every invocation.**

The *output* is negotiable — wording, scope, how much body detail, whether a trailer
appears. The *procedure* is not. A commit produced by skipping steps is not this skill's
output, it's a guess wearing its name.

| Rule | |
| --- | --- |
| Steps 0–5 run **in order, every time** | Including for a one-line change, a typo fix, or work you just did yourself in this session |
| No step is skipped for being "obvious" | The size of the diff never justifies skipping a step. Small diffs are where invented scopes and stale trailers come from |
| Each gate produces **evidence** | Not a claim that it was done — the [preflight block](#preflight-block--required) prints what was measured |
| A failed gate stops the run | Fix and re-run the gate. Never proceed past it, and never report it as passed |

### The four gates

| Gate | Step | Cannot proceed until |
| --- | --- | --- |
| **Learnings read** | 0 | `.claude/learnings/git-workflow/commit.md` has been read, or confirmed absent |
| **Diff read** | 1 | The actual diff has been read this run — never write a message from memory of the session |
| **Widths measured** | 4 | The awk check has been *run* and printed, not estimated |
| **User approved** | 5 | The user has approved this exact message |

### What a user instruction can and cannot change

| The user can | The user cannot |
| --- | --- |
| Change any part of the message — type, scope, wording, body, footers | Skip the diff read, the width check, or the scratch file |
| Pre-approve: "commit it without showing me" counts as the Step 5 approval, and the preflight block is still reported | Get a `git commit -m`; the commit always comes from the file, via `-F` |
| Override conventions durably through [learnings](#capturing-learnings) | Have content committed that the diff doesn't support |
| Decline the `.gitignore` entry | — |

"Just commit it", "quick commit", and "don't overthink it" are instructions about
*verbosity*, not permission to drop steps. Run the procedure — it costs one diff read and
one awk call — and keep the presentation brief.

---

## Step 0: Load Project Learnings

Read `.claude/learnings/git-workflow/commit.md` from the repository root if it exists.

This file holds facts unique to **this repository** — an established scope vocabulary, a
required trailer, a ticket-reference format. Apply anything relevant.

**If the file does not exist, proceed with defaults. Do not create it.** It is created
only when a learning is captured (see [Capturing Learnings](#capturing-learnings)).

Attempt the read on every run — a file added since the last run is exactly the case this
step exists for. The outcome is reported on the `learnings` line of the
[preflight block](#preflight-block--required).

The specification below is the global default. Learnings layer repository-specific facts on
top of it, and where a learning explicitly contradicts a default, **the learning wins** —
that's what makes one skill usable across repositories that disagree. A learning can only
override what this skill presents as a convention, never the [Content Rules](#content-rules)
on accuracy and secrets.

---

## Message Specification

### Structure

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

- **Header** — required, one line, ≤ 50 characters (see [Line widths](#line-widths))
- **Body** — separated by a blank line, hard-wrapped at 72 columns, explains the *why*
- **Footers** — separated by a blank line; `BREAKING CHANGE`, refs, trailers

### Line widths

| Part | Limit | What to do when it doesn't fit |
| --- | --- | --- |
| Header | **50 characters**, including `type(scope): ` | Rewrite it. Shorten the description, or drop the scope if it isn't earning its width. |
| Header | **72 characters — absolute** | Never ship this. Tooling truncates past it, and 51–72 is a last resort, not a second budget. |
| Body line | **72 columns** | Hard-wrap it yourself. Git does not wrap for you, and terminals don't either. |
| Footer line | one line each | Do **not** wrap a footer. `Refs:`, `Closes:`, and `Co-Authored-By:` are single tokens; a wrapped trailer stops being a trailer. |

Two exemptions, and only these:

1. **Footer lines**, per the table above.
2. **A body line holding one unbreakable token** — a URL, a long path, a fully
   qualified identifier — with no whitespace to wrap at. Put it on its own line and let
   it overflow rather than breaking it.

Everything else fits. Detail that won't fit in the header belongs in the body, which is
what the body is for.

```
✗ feat(notifications): add retry with exponential backoff for failed webhooks  (75)
✓ feat(notifications): retry failed webhook sends                              (47)
```

The rejected header is over both limits and says nothing the body can't say better. When
the description is genuinely irreducible, the body carries the rest:

```
fix(auth): refresh tokens before expiry                                        (39)

Tokens were refreshed on the first 401, which surfaced as a
visible sign-out. Refresh at 90% of TTL instead.
```

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

Include one when the *why* isn't obvious from the description. Explain motivation, contrast
with previous behavior, note consequences. Backtick code references:
`TokenRefreshManager.refresh()`.

Hard-wrap every line at 72 columns as you write it — see [Line widths](#line-widths).
Reflowing a finished paragraph is harder than writing it wrapped.

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

#### Model attribution — required

Every message ends with a co-author trailer naming the model that wrote it, as the last
line of the footer block:

```
Co-Authored-By: <model display name> <noreply@anthropic.com>
```

**Name the model actually generating the commit**, taken from the current environment —
`Claude Opus 5`, `Claude Sonnet 5`, `Claude Haiku 4.5`, and so on. Include a qualifier when
the environment reports one, e.g. `Claude Opus 5 (1M context)`.

Never copy a name from the examples in this skill, carry one over from an earlier commit in
the history, or guess at a version. The point of the trailer is that `git log` records which
model did which work; a wrong name is worse than no record.

If the model identity genuinely isn't available, use `Claude <noreply@anthropic.com>`
rather than inventing a version number.

When the message has no other footer, the trailer still gets its own block separated by a
blank line. When there are other footers, it goes last.

**A repository can opt out.** Some teams don't credit models in their history. If learnings
record that, omit the trailer entirely and don't raise it again — see
[Capturing Learnings](#capturing-learnings).

---

## Content Rules

1. **Describe only what the diff shows.** Never invent or assume a change.
2. **Imperative mood throughout.**
3. **Explain what and why, not how** — the code already shows how.
4. **Never reference plan or investigation files.** Extract the content instead.
5. **Human voice.** Write as the developer. Attribution belongs in the required
   [model co-author trailer](#model-attribution--required) — never in the description or
   body, and never scattered through the prose.
6. **Never include secrets or PII** — no tokens, keys, credentials, emails, personal names,
   internal URLs, or connection strings. If the diff contains any, warn the user and stop
   before writing the message. The model co-author trailer is the sole exception:
   `noreply@anthropic.com` is a placeholder address, not anyone's personal one.

---

## Workflow

Every step is mandatory — see the [Execution Contract](#execution-contract).

### Step 1: Read the Changes

**Always run these, even if you made the changes yourself earlier in this session.** What
is in the working tree is the only source of truth for the message; your memory of the
session is not, and it silently omits whatever else the tree picked up.

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
above. Write the header to fit 50 and wrap the body at 72 from the start — Step 4 measures
both, and a message that fails there gets rewritten anyway.

Before moving on, check that the footer block ends with the model co-author trailer, naming
the model currently running rather than one copied from an example or from the history.

### Step 4: Present for Review

Write the message to a scratch file in `claude-git-workflow/` at the **repository root**,
where it sits beside the code and is easy to open and edit:

```bash
mkdir -p "$(git rev-parse --show-toplevel)/claude-git-workflow"
```

Write to `claude-git-workflow/commit-message.md`. Resolve the path from
`git rev-parse --show-toplevel` rather than the current directory — the skill may be
invoked from a subdirectory, and the file belongs at the root either way.

#### Keep the directory out of version control

`claude-git-workflow/` holds working files, never repository content. Check whether it is
already ignored:

```bash
git check-ignore -q claude-git-workflow && echo ignored
```

If it is not ignored, propose the entry once — typically the first time this skill runs in
a repository:

> `claude-git-workflow/` isn't in `.gitignore`. Add it so these working files never get
> committed? (yes / no)

**Add it only on approval**, appending `claude-git-workflow/` to the root `.gitignore` and
creating that file if it doesn't exist. Don't re-ask on later runs once the entry exists.

If the user declines, say plainly that `git add -A` in Step 5 will stage
`claude-git-workflow/commit-message.md` along with everything else, and let them decide
whether to proceed.

#### Measure the line widths — required

Never eyeball this. Once the file is written, measure it:

```bash
MSG="$(git rev-parse --show-toplevel)/claude-git-workflow/commit-message.md"
awk 'NR==1 { h = length }
     length > (NR==1 ? 50 : 72) { printf "OVER  L%-3d %3d chars: %s\n", NR, length, $0 }
     NR>1 && length > m { m = length }
     END { printf "header %d/50, longest line %d/72\n", h, m }' "$MSG"
```

Every `OVER` line is a defect unless it is one of the two
[exemptions](#line-widths). **Rewrite the message, overwrite the file, and re-run the
check.** Do not present a message that fails it, and do not present one you haven't
measured — the reason this limit gets ignored is that "aim for 50" is easy to skip and a
printed number is not.

#### Preflight block — required

Display the message inline, give the path, and print the preflight block. Four lines,
this order, every run — it is the evidence that each [gate](#the-four-gates) actually
ran, and it is what makes skipping a step visible instead of silent:

```
learnings   none            (or: 3 rules applied)
staging     all changes     (or: staged subset — 4 files)
widths      header 47/50, longest line 68/72
trailer     Claude Opus 5
```

Report what happened, never what should have happened. `learnings none` means the file
was looked for and absent — not that it wasn't checked. If a line can't be filled in
honestly, the step it reports on didn't finish; go finish it.

Then ask:

> Ready to commit, or would you like changes? You can also edit the file directly.

Revise and re-present until approved — re-running the width check and reprinting the
block after every revision, since a revision can break what the last one passed.

**Keep it brief when asked, but keep it.** If the user wants less ceremony, the block is
already four lines; drop the inline message display before dropping the block.

### Step 5: Commit

**Only after explicit approval of this exact message.** Approval of an earlier revision
is not approval of the current one. A blanket "commit it without showing me" given
earlier in the session counts — nothing else does, and silence never does.

1. Stage — `git add -A`, or leave staging alone if the user had deliberately staged a subset.
   If a `.gitignore` entry was added in Step 4, that edit will be staged too — mention it so
   the user isn't surprised to find it in the commit
2. Re-read the scratch file so manual edits are picked up. If the user's own edits push a
   line over the limits, mention it once and commit their bytes anyway — the width rule
   governs what this skill writes, not what the user decides to write
3. Commit with the file, never an inline message:

```bash
git commit -F "$(git rev-parse --show-toplevel)/claude-git-workflow/commit-message.md"
```

`-F` guarantees the commit uses exactly what the user approved or edited. Never use `-m`.

4. Confirm: report the short SHA and the branch.

**Do not push.** Pushing is a separate, explicit action.

---

## Examples

**The model name in these trailers is illustrative.** Always substitute the model actually
running, per [Model attribution](#model-attribution--required).

Simple — the trailer is still its own block:

```
fix: prevent duplicate API calls on retry

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

Scoped by code area:

```
feat(auth): add OAuth2 PKCE flow support

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

With body:

```
refactor(db): extract shared connection pool

The pool configuration was duplicated across three services.
Centralizing it reduces drift and makes pool size tunable in
one place.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

Scoped by ticket, with a ref — the trailer goes last:

```
fix(ABC-2888): align badge on saved payment cards

The badge used a fixed top offset, which drifted on cards with
two-line titles. Anchor it to the card header instead.

Refs: ABC-2888
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

Breaking:

```
feat(api)!: return paginated responses from /users

The endpoint now returns `{ data: [], meta: { page, totalPages } }`
instead of a flat array.

BREAKING CHANGE: clients must update to handle the pagination wrapper

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
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
| "Don't add the model co-author trailer" | Yes — repository convention |
| "Our scopes are `app`, `domain`, `data`" | Yes — repository convention |
| "Headers up to 72 are fine here" | Yes — repository convention |
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
| Header can't reach 50 without losing accuracy | It can. Move the detail to the body and shorten the header |
| Width check still reports `OVER` after a rewrite | Rewrite again. Do not present it, and do not annotate it as acceptable |
| `awk` unavailable | Count with any available tool and report the same numbers; never substitute an estimate |
| Asked to commit without a review step | Run Steps 0–4, print the preflight block, commit — treat the request as pre-approval, not as permission to skip |
| Asked to use `git commit -m` | Decline that one detail, say why in a sentence (`-F` preserves the user's exact bytes), and commit from the file |
