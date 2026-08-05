---
name: docs-system
description: >
  Set up a documentation reference system in a repository. Use this skill whenever the user asks
  to "set up docs", "set up the documentation", "create a documentation system", "organize the docs
  folder", "set up the reference docs", "initialize documentation", "add a docs structure", or asks
  how this project's documentation should be organized. Surveys any existing `docs/` tree, reports
  which parts of the reference format are missing, and scaffolds the tiers, the index, and the
  reference template only where they are absent. Never renames, reformats, or restructures existing
  documentation files. To write one individual reference file, use the `reference-doc` skill instead.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Set Up Documentation System

Establish the structure that reference documentation lives in — the tiers, the index, and the
template new files follow — adapting to whatever the repository already does rather than
imposing a layout on it.

This skill sets up the **system**. Writing an individual reference file is `reference-doc`.

---

## Step 0: Load Project Learnings

Read `.claude/learnings/docs-workflow/docs-system.md` from the repository root if it exists.

This file holds facts unique to **this repository** that discovery can't reach — an index
that lives somewhere other than `docs/README.md`, a tier that is deliberately untracked, a
section order the team has settled on, documentation that lives in a separate repository.

**If the file does not exist, proceed with defaults. Do not create it.** It is created only
when a learning is captured (see [Capturing Learnings](#capturing-learnings)).

Where a learning contradicts a default below, **the learning wins.**

**Most of what varies between repositories is discoverable, not a learning.** The reference
directory's path, the filename casing, which tier is ignored — all of that comes from Step 1.
Don't ask for what `ls` will tell you.

---

## What the System Is

| Part | Holds | Tracked | Default path |
| --- | --- | --- | --- |
| **Reference tier** | Durable, cross-cutting rules — looked up when needed rather than read once | Yes | `docs/reference/` |
| **Working notes tier** | Task-, ticket-, or milestone-scoped notes; obsolete once the work ships | Either | `docs/local/` (ignored) or `docs/knowledge/<category>/` (tracked) |
| **Index** | One row per reference file, saying what each covers | Yes | `docs/README.md` |
| **Template** | The format new reference files follow | Yes | `docs/reference/_template.md` |

The dividing line between the two tiers is one question: **will this still be correct after
the current milestone ships?** If yes, it's reference. If it dies with the ticket, it's a
working note.

**When in doubt, working notes.** Promoting a note to a reference later is a `git mv`. Going
the other way doesn't un-publish anything already committed.

Both tiers are optional in a given repository. A repo may keep working notes untracked, keep
them tracked under categories, or not keep them at all — that's a local decision, and Step 1
finds out which.

---

## Workflow

### Step 1: Survey What Exists

Resolve the repository root first, since this skill may be invoked from a subdirectory:

```bash
git rev-parse --show-toplevel
```

Then look, without writing anything:

```bash
ls docs/ 2>/dev/null
ls docs/reference/ docs/local/ docs/knowledge/ 2>/dev/null
git check-ignore -v docs/local docs/tmp 2>/dev/null
```

Record five facts. Each has a discovery method — use it rather than asking:

| Fact | How to find it |
| --- | --- |
| Reference directory | A `reference/` (or `references/`) subdirectory, or reference files sitting directly in `docs/` |
| Filename convention | Read the names already there — `architecture.md` (kebab) vs `UI_COMPOSE_REFERENCE.md` (caps). **Match it; never impose one.** |
| Index location | `docs/README.md`, or a link list inside `CLAUDE.md` — check with `grep -n 'docs/' CLAUDE.md` |
| Template | A `_template.md`, `TEMPLATE.md`, or similar in the reference directory |
| Working-notes tier | Any tier-shaped sibling directory, plus whether `git check-ignore` reports it ignored |

If `docs/` doesn't exist, also check for `documentation/`, `doc/`, or a top-level `wiki/`
before concluding the repository has nothing.

### Step 2: Classify the Repository

| What Step 1 found | Go to |
| --- | --- |
| No documentation directory at all | Step 3 |
| Documentation files, but no template and no index | Step 4 |
| A template and an index already present | Step 4 — report and stop early if there are no gaps |

### Step 3: Greenfield — Propose, Then Create

Show the tree before creating any of it:

```
docs/
├── README.md                 index — one row per reference file
├── reference/
│   └── _template.md          the format new reference files follow
└── local/                    working notes, git-ignored
```

State the two decisions embedded in that proposal, because they're the ones worth objecting
to: reference files will be **kebab-case**, and `docs/local/` will be **untracked**. Offer
tracked working notes under `docs/knowledge/<category>/` as the alternative if the team wants
plans and investigations reviewed and shared.

On approval, write:

1. `docs/reference/_template.md` — copied from
   `${CLAUDE_PLUGIN_ROOT}/reference/_template.md`, unmodified.
2. `docs/README.md` — the index. See [The Index](#the-index) for what goes in it.
3. `docs/local/.gitkeep` only if the working-notes tier is tracked. An ignored directory
   needs no placeholder.

**If the bundled template can't be read, stop and say so.** Report the path and write
nothing. Do **not** author a replacement from the slot names in this skill: a plausible
but incomplete template is worse than no template, because it looks finished and nobody
re-checks it. Measured — one reconstruction attempt produced 69 lines against the real
file's 97, silently dropping a third of the guidance while reading as complete.

Then Step 7 for the `.gitignore` entry.

**There are no reference files yet, and that's fine.** Don't invent one to fill the index.
Say the index is empty and that `reference-doc` will add rows as files land.

### Step 4: Existing Documentation — Report the Gaps

Read `${CLAUDE_PLUGIN_ROOT}/reference/slots.md`, then check the reference files that exist
against the slots it lists.

Report by slot, **with the evidence**, not as a generic checklist:

> `docs/reference/` has three files. Two gaps:
>
> - **No scope negation slot.** `architecture.md:8` and `stack.md:8` both open with a bold
>   caveat paragraph doing that job. Two files inventing the same section independently means
>   the template is missing it.
> - **`status` carries prose.** Both files write `Settled — for structural architecture only`.
>   The qualifier is useful, but in that field it makes `grep -l 'status: settled'` unreliable.

A slot filled under a local name is **not** a gap. `## Troubleshooting` fills the traps slot;
report it as present and keep their heading.

If every slot is filled, say so and stop. Don't manufacture work.

### Step 5: The Template Decision

Only when the repository has a template that leaves slots unfilled. Present three options,
and recommend the middle one:

| Option | What happens |
| --- | --- |
| **Keep as-is** | Nothing changes. The gaps are now known. |
| **Merge** *(recommended)* | Add only the missing slots to *their* template, preserving their field names, wording, and section order. |
| **Replace** | Their template becomes the bundled one at `${CLAUDE_PLUGIN_ROOT}/reference/_template.md`. |

**Compare by slot, not by text diff.** A text diff flags `## Troubleshooting` as "missing
`## Gotchas`" and merging on that basis leaves the file with both.

**Whichever they pick, existing reference files are not touched.** Say this explicitly, since
it's the part that surprises people:

> Updating the template changes what *new* files look like. Your three existing files stay as
> they are — migrating them is a separate job, and I'd want to do it one file at a time.

If they decline entirely, that's an answer. State the consequence once — new files will keep
missing that slot, so readers may act on a partial document as if it were complete — and move
on. **The suggestion is not a gate.**

When the repository has no template at all, there's nothing to compare: offer to add the
bundled one, and describe the two or three slots that will newly be expected so the offer is
concrete.

### Step 6: The Index

If there's no index, offer to create `docs/README.md` with a row per existing reference file,
reading each file's trigger line for the "covers" column.

**If the index already lives somewhere else, leave it there.** A repository whose `CLAUDE.md`
carries the link list has an index; adding `docs/README.md` would create a second one, and two
indexes drift within a month. Record the location as a learning instead — this is exactly the
kind of fact discovery finds but can't infer.

### Step 7: The Working-Notes Tier and `.gitignore`

Only when the tier is meant to be private:

```bash
git check-ignore -q docs/local
```

If it isn't ignored, propose adding `docs/local/` to the root `.gitignore` — **appending only
on approval.** Use a directory entry, not a bare filename glob, so it can't match a
same-named path elsewhere in the tree.

If they decline, say what follows: notes in that directory get committed and shared, which
may be exactly what they want. Proceed either way.

---

## The Index

The index exists so a reader can find the right reference without opening all of them. It
holds one row per file, and the row says **what the file covers** — not a restatement of its
title.

```md
| File | Covers |
| --- | --- |
| [`architecture.md`](reference/architecture.md) | Module layout, `expect`/`actual`, iOS framework surface, build-config quirks |
| [`stack.md`](reference/stack.md) | Library decisions, open decisions, build order |
```

Two things belong alongside it: which tier is tracked and which isn't, and a pointer to
`_template.md` for anyone adding a file.

**Do not put the authoring rules in the index.** The template holds the format. An index that
also explains the format is a second source of truth for it, and the two drift — the template
is the one a writer actually opens.

---

## What This Skill Never Does

1. **Never reformats, renames, or restructures an existing documentation file.** Not to match
   the template, not to match a filename convention, not as a tidy-up. Migration is a separate
   explicit request, done one file at a time.
2. **Never overwrites a template the repository already has** without the user choosing
   Replace in Step 5.
3. **Never adds a table of contents**, and never suggests one. A file that wants one wants
   splitting.
4. **Never moves a file between tiers.** Promotion is the user's `git mv`.
5. **Never creates the learnings file** unless a learning is approved.
6. **Never imposes the kebab-case default on a repository that uses another convention.**
7. **Never reconstructs a bundled file it couldn't read.** Stop and report the path. This
   applies to `_template.md` and `slots.md` equally — a gap report written from a
   half-remembered slot list is a wrong answer delivered confidently.

**No scratch file.** Unlike the `git-workflow` skills, the artifacts here *are* repository
files under `docs/`, reviewable in place with `git diff` and revertible with `git checkout`.
Staging them through `claude-git-workflow/` first would add a copy step and no review value.
Present the plan before writing; that's the review step.

---

## Capturing Learnings

The structure above is the global default. **The learnings file is only for facts specific to
one repository that Step 1 can't discover.**

| Correction | Durable repo fact? |
| --- | --- |
| "Reference docs live in `docs/reference/`" | No — `ls` finds it |
| "Filenames are `SCREAMING_SNAKE_CASE` here" | No — the existing files show it |
| "`docs/local/` is ignored" | No — `git check-ignore` reports it |
| "The index is a section in `CLAUDE.md`, not `docs/README.md`" | Yes — discoverable but not inferable |
| "Design specs live in a separate repository, never in `docs/`" | Yes — nothing in this repo shows it |
| "We keep working notes tracked, by category, deliberately" | Yes — records the intent, not just the state |
| "We put Quick reference last, not first" | Yes — a settled order deviation |
| "Don't propose ignoring `docs/tmp/`, we've discussed it" | Yes — stops a recurring proposal |
| "Name this one `architecture-v2.md`" | No — one-off edit |

For a durable fact, propose saving it:

```
That looks repo-specific. Save it to .claude/learnings/docs-workflow/docs-system.md?

  ## Index Location
  **Rule:** The reference index is the link list at the bottom of `CLAUDE.md`.
  There is no `docs/README.md` and one should not be created.
  **Why:** Every session already loads `CLAUDE.md`, so the index is read without
  a second file. A `docs/README.md` would be a second index and would drift.

Save? (yes / no / edit)
```

**Append only on approval.** Create `.claude/learnings/docs-workflow/` and the file if
needed, with this header:

```md
# Learnings — `/docs-workflow:docs-system`

Repository-specific patterns for the `docs-system` skill. The skill reads this file before
surveying the documentation tree. The structural defaults live in the skill itself; only
facts unique to this repository belong here.

---
```

Entry format — a `##` title, then `**Rule:**` and `**Why:**`. If a new learning contradicts
an existing one, update that entry rather than appending a duplicate.

**Keep tier facts in one entry.** A path recorded separately from the intent behind it is how
a learnings file ends up saying `docs/local/` is ignored two entries above a rule that treats
it as shared.

---

## Error Handling

| Failure | Action |
| --- | --- |
| Not a git repository | Continue — nothing here requires git except the `.gitignore` and `check-ignore` steps. Skip those and say so. |
| `docs/` exists but is empty | Treat as greenfield; scaffold into it rather than creating a sibling directory |
| Both `docs/` and `documentation/` exist | Stop and ask which is authoritative. Never scaffold into one while the other holds real content |
| Reference files use two different filename conventions | Report the split, use the majority for new files, and don't rename anything |
| A `_template.md` exists but doesn't describe any file present | Report it — the template was likely adopted after those files were written. Offer migration as a separate job |
| The bundled `_template.md` or `slots.md` can't be read | **Stop.** Report the path and that it was unreadable. Never write a reconstructed version — an incomplete template that reads as complete is the worst available outcome |
| Index exists in two places already | Report both, ask which is authoritative, offer to record it as a learning. Don't create a third |
| Learnings say the index is in `CLAUDE.md` but it isn't there anymore | Trust the repository, mention the discrepancy once, offer to update the entry |
| The user asks to migrate existing files during setup | Finish the setup first, then handle migration as its own reviewed pass, one file at a time |
