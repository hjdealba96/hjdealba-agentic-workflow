---
name: reference-doc
description: >
  Write a project reference document under `docs/reference/`. Use this skill whenever the user asks
  to "document this pattern", "write up how X works in this project", "write a reference doc",
  "document the architecture", "add a reference file", "document our testing conventions", "add this
  to the docs", or "document what we just decided" — any request to write durable project
  documentation rather than code. Reads the repository's own `_template.md` so the file matches local
  format, decides whether the topic belongs in the durable reference tier or in task-scoped working
  notes, keeps `status` honest, and adds the row to the docs index. Never create a file under `docs/`
  without consulting this skill first. Not for KDoc, docstrings, inline comments, or the project
  README — those are ordinary edits, not reference documents.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Write Reference Document

Write a durable, cross-cutting reference file — and first decide whether the topic actually
warrants one.

The triage in Step 1 is the point of this skill. A template can be copied by hand; deciding
*where a piece of knowledge belongs* is the part that gets done wrong, and a wrongly-placed
document is worse than a missing one because it accumulates trust it hasn't earned.

To set up the documentation system itself — the tiers, the index, the template — use
`docs-system`.

---

## Step 0: Load Project Learnings

Read `.claude/learnings/docs-workflow/reference-doc.md` from the repository root if it exists.

This file holds facts unique to **this repository** — a section order the team settled on, a
required field the template doesn't carry, topics that deliberately live elsewhere.

**If the file does not exist, proceed with defaults. Do not create it.** It is created only
when a learning is captured (see [Capturing Learnings](#capturing-learnings)).

Where a learning contradicts a default below, **the learning wins.**

---

## Step 1: Triage — Does This Belong in a Reference File?

Decide the destination before writing anything.

| The knowledge is… | Destination |
| --- | --- |
| Still correct after the current milestone ships, and **looked up** when needed rather than read once | **Reference tier** — continue with this skill |
| Scoped to one ticket, feature, or investigation; obsolete when that work ships | **Working notes tier** — write it there, don't use the template |
| An explanation of one function, class, or file, useful at the definition | **A code comment** — not a document |
| How to install, build, or run the project, for someone arriving new | **The project README** — an ordinary edit |
| A decision and the alternatives weighed, as a point-in-time record | **An ADR or working note** — a reference file states what *is*, not the deliberation |

Two tests that resolve most ambiguity:

- **Would this still be correct in six months if the current work ships as planned?** No means
  working notes.
- **Would a reader arrive here with a question, or be handed it to read start to finish?**
  Start-to-finish means it's a guide or a note, not a reference.

**When in doubt, working notes.** Promoting a note later is a `git mv`; a reference file that
was never durable quietly misleads until someone notices.

**Say which one you chose and why, in a sentence**, before drafting:

> This is a reference — the module layout outlives the MVP and gets consulted per-task rather
> than read through. Writing it to `docs/reference/architecture.md`.

If the answer is one of the other four rows, say so and do that instead. Redirecting is a
successful outcome for this skill, not a failure.

---

## Step 2: Load the Format

Find the repository's template and read it:

```bash
git rev-parse --show-toplevel
ls docs/reference/_template.md docs/reference/TEMPLATE.md 2>/dev/null
```

**The repository's template is the authority.** Follow its fields, its section names, and its
order — even where they differ from the bundled default. The team edits that file to change
what their docs look like, and this skill following it is what makes that work.

If there is no template in the repository, read
`${CLAUDE_PLUGIN_ROOT}/reference/_template.md` and use it for this file. Mention once that
`docs-system` can install it so the next file doesn't have to rediscover the format — but
don't stop to set up the system. Write the file they asked for.

For what each section is *for* — and how to recognize the same slot under a different heading
name — read `${CLAUDE_PLUGIN_ROOT}/reference/slots.md`.

Also settle the filename from what's already there:

```bash
ls docs/reference/
```

Match the existing convention exactly — `architecture.md` in a kebab-case repo,
`ARCHITECTURE_REFERENCE.md` in a caps one. **Never introduce a second convention**, and never
rename existing files to match the one you're adding.

---

## Step 3: Check for an Existing Home

A new file is the wrong answer if the topic already has one. Check before creating:

```bash
rg -il '<two or three distinctive terms from the topic>' docs/ --ignore-cr-at-eol
```

| What you find | Do |
| --- | --- |
| An existing file whose scope covers this | **Add a section to it.** Two files on one topic drift, and readers can't tell which is current |
| An existing file that mentions it in passing | Create the new file, and add a `Related` link both ways |
| An existing file whose scope *nearly* covers it | Ask. The choice between one broad file and two narrow ones is the team's, and it's cheap to ask now and expensive to undo later |
| Nothing | Create it |

---

## Step 4: Size It, and Split Instead of Sprawling

Before drafting, sanity-check the scope you're about to take on:

- **More than about eight top-level sections, or past roughly 400 lines**, check whether it's
  actually two topics. That is where files in the wild start growing tables of contents.
- **If you ever want a table of contents, split the file.** That impulse is the reliable
  signal, more than any line count — a reader who needs a map of one file is telling you it
  should have been two.

A 2,000-line reference covering structure, concurrency, state, DI, and error handling is four
references welded together, and its sections will contradict a sibling file within a release.

**Propose the split rather than performing it.** Say which two files you'd write and what the
boundary is, and let the user choose one file or two.

---

## Step 5: Draft It

Fill the template's slots. Three rules carry most of the quality:

**Lead with the trigger, not the subject.** "Read this before adding a dependency" beats "This
document describes the technology stack." The opening line's job is to let a reader decide
whether to keep reading.

**Every rule gets its reason.** An unexplained rule gets "fixed" by the next person who finds
it inconvenient — including an agent doing a tidy-up pass. If you can't state the reason, that's
a finding worth surfacing rather than papering over:

> I can't tell why dependencies must go in `libs.versions.toml` rather than the build file.
> I'll write the rule, but flag the reason as unknown — do you know it?

**Show the wrong version with the reason it's wrong.** Not just a ❌ — name which failure it
is, so a reader recognizes a new instance that doesn't look like the example:

```kotlin
// ✅ collectAsStateWithLifecycle — stops collecting when the screen backgrounds
// ❌ collectAsState — keeps collecting off-screen; drains battery, races on resume
// ❌ LaunchedEffect(Unit) — re-runs on configuration change, so the call double-fires
```

**Fill the compact lookup, and put it where the template puts it.** If the topic is in progress
and progress is countable, write the *command that counts it* rather than a number that will be
wrong next week.

**Delete every section that would be empty.** An empty heading is a promise the file doesn't
keep.

---

## Step 6: Get the Status Right

`status` is the field a reader uses to decide whether to act. It is the one most likely to be
wrong, because "settled" is the flattering choice.

| Value | Means | Requires |
| --- | --- | --- |
| `settled` | Decided; follow it | Nothing outstanding that would change the rules |
| `provisional` | A working assumption that may change | An **Open questions** section saying what would settle it |
| `undefined` | Placeholder; nothing here is authoritative | Say what to do instead — usually "ask" |

Three checks before writing it:

1. **Does the code actually do this yet?** A library chosen but not yet in the dependency file
   is `provisional`, not `settled`. Verify rather than assuming.
2. **Is it settled for the whole topic, or part of it?** Partial goes in the scope-negation
   section, never appended to `status` as prose — that field gets grepped.
3. **Would the team argue about any of it?** Then it's `provisional`, and the disagreement goes
   in Open questions.

**Default to `provisional` when unsure.** An over-confident `settled` invites decisions built
on sand, and it's the one error in this file nobody catches by reading it.

---

## Step 7: Confirm Before Writing

Present the destination, the status, and the outline — not the full body:

> `docs/reference/architecture.md` · `status: provisional` · applies to `shared/**`
>
> Sections: Not covered (application layering is undecided) · Quick reference (module table) ·
> Modules · Platform-specific code · Gotchas · Open questions
>
> Write it?

The status and the scope-negation line are the two worth confirming explicitly. They're what a
future reader will trust, and they're the ones you're most likely to have judged wrong from
outside the team.

---

## Step 8: Write It, Then Update the Index

Write the file, then add its row to the index — `docs/README.md`, or wherever `docs-system`
recorded that this repository keeps it.

The row says **what the file covers**, not a restatement of its title:

```md
| [`architecture.md`](reference/architecture.md) | Module layout, `expect`/`actual`, iOS framework surface, build-config quirks |
```

**An unindexed reference file is close to invisible.** Don't treat the row as optional cleanup;
it's part of writing the file.

If the index lives in `CLAUDE.md`, add the row there. If there's no index anywhere, say so and
mention `docs-system` — but don't create one as a side effect of writing a document.

Finally, add `Related` links **both ways** if Step 3 found a sibling. A one-directional link is
half a connection, and the missing half is on the file nobody's editing.

---

## Capturing Learnings

The rules above are global. **The learnings file is only for facts specific to one repository.**

| Correction | Durable repo fact? |
| --- | --- |
| "Reference files go in `docs/reference/`" | No — `ls` finds it |
| "Use `SCREAMING_SNAKE_CASE` for filenames" | No — the existing files show it |
| "We put Quick reference at the end, not the top" | Yes — a settled order deviation |
| "Every reference needs an `owner:` field" | Yes — a local template requirement |
| "Never document the design system here, it lives in the design repo" | Yes — a scope boundary |
| "Anything Plaid-related goes in the existing Plaid file, never a new one" | Yes — a repository convention |
| "Default new files to `provisional`, we've been over-claiming" | Yes — a team calibration |
| "Make this section shorter" | No — one-off edit |
| "Call it `stack.md` not `dependencies.md`" | No — one-off edit |

For a durable fact, propose saving it:

```
That looks repo-specific. Save it to .claude/learnings/docs-workflow/reference-doc.md?

  ## Design System Scope
  **Rule:** Never document tokens, components, or visual guidelines in a reference
  file. They live in the separate design repository.
  **Why:** The design repo versions each definition as a deployed page; a copy here
  would drift and there'd be no way to tell which one a screen was built against.

Save? (yes / no / edit)
```

**Append only on approval.** Create `.claude/learnings/docs-workflow/` and the file if needed,
with this header:

```md
# Learnings — `/docs-workflow:reference-doc`

Repository-specific patterns for the `reference-doc` skill. The skill reads this file before
drafting a reference document. The general authoring rules live in the skill itself, and the
document format lives in `docs/reference/_template.md`; only facts unique to this repository
belong here.

---
```

Entry format — a `##` title, then `**Rule:**` and `**Why:**`. If a new learning contradicts an
existing one, update that entry rather than appending a duplicate.

**Never record the document format as a learning.** The template file is where format lives. A
learning that says "include a Gotchas section" is a second source of truth for something the
template already states, and the two will disagree.

---

## Error Handling

| Failure | Action |
| --- | --- |
| No `docs/` directory at all | Say so, mention `docs-system`, and offer to write the single file at a sensible default path rather than stopping |
| No template in the repository | Use the bundled default, mention `docs-system` once, continue |
| The repository's template is malformed or unreadable | Report what's wrong, fall back to the bundled default for this file, don't rewrite theirs |
| Topic is already covered by an existing file | Propose editing that file instead; create a second one only if the user chooses to |
| The user asks for a reference file on task-scoped work | Say which tier it belongs in and why, offer to write it there instead. If they still want a reference file, write it — state the assumption and move on |
| Can't determine the reason behind a rule | Write the rule, flag the missing reason explicitly, ask. Never invent a rationale |
| Draft is heading past 400 lines or wants a table of contents | Propose the split before writing, with the boundary named |
| Filenames in the reference directory use two conventions | Use the majority, mention the split once, rename nothing |
| Index can't be found | Write the file, report that the row couldn't be added and where you looked |
