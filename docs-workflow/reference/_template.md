---
status: settled
applies_to:
  - <path or glob this governs>
---

# <Topic>

<!--
Copy this file to <reference-dir>/<topic>.md and fill it in.
Delete every section that would be empty — an empty heading is worse than no heading.
Delete these comments too.

status: exactly one of these three words. No qualifiers, no prose — this field gets
        grepped ("which references are still provisional?").
          settled      — decided; follow it.
          provisional  — a working assumption that may change. Say what would settle
                         it under Open questions.
          undefined    — a placeholder. Nothing here is authoritative; ask rather
                         than infer.
        Anything you want to add ("settled, but only for the module layout") belongs
        in Not covered, not appended to this field.

applies_to: the paths, modules, or globs this governs. A single item reading
        "whole repo" is fine.

Do NOT add Updated:, Owner:, or Version:. Git already knows when this file changed,
and a hand-maintained date eventually lies — which is worse than having none.

Do NOT add a table of contents. A reader already sees every heading, and a
hand-maintained list of them rots. If this file is long enough to want one, it is
long enough to split into two files.
-->

<One or two sentences: what this covers, and when someone should read it. Lead with the
trigger — "Read this before adding a dependency" beats "This document describes...".
This line is how a reader decides whether to open the file at all, so make it about the
moment of need, not the subject matter.>

**Not covered:** <What this file does *not* govern, and where that lives instead. Also
where to narrow an over-broad status — "settled for the module layout; application
layering is undecided". This is what stops a reader from acting on this file for a
decision it never made. Delete only if the title genuinely covers the whole topic.>

## Quick reference

<The compact lookup — a table, a decision tree, or a two-column when-to-use-what. At the
TOP, not the bottom: someone who came for one fact should not have to read the body to
find it.

If the topic is in progress and the progress is countable, put the *command that counts
it* here instead of a number that will rot:

    # Screens migrated to Compose
    rg -l '@Composable' app/src/main/java | wc -l

Delete if the topic genuinely has no compact form.>

## <Rule group>

<State the rule, then why it exists. A rule without a reason gets "fixed" by the next
person who finds it inconvenient — and that includes an agent doing a tidy-up pass.

Use a table when the content is a set of parallel facts (commands, tokens, module roles).
Use prose when the *why* carries the weight. Repeat this section once per rule group.>

## Anti-patterns

<The wrong version beside the right one, each labeled with the reason it is wrong. Not
just ✅/❌ — name *which* failure it is, so a reader can recognize a new instance that
doesn't look like the example:

    // ✅ collectAsStateWithLifecycle — stops collecting when the screen backgrounds
    // ❌ collectAsState — keeps collecting off-screen; drains battery, races on resume
    // ❌ LaunchedEffect(Unit) — re-runs on configuration change, so the call double-fires

Delete if the rules above have no recurring failure modes.>

## Gotchas

<Things that look like a bug but aren't, and mistakes that recur. In practice this is the
highest-value section in the file — it's where a wrong assumption gets corrected before
it costs an hour.

Restating a warning already made in the body is intentional: it earns its place both as a
skim target and as a search hit. If the two ever disagree, **the body is the source of
truth.** Delete if there are none.>

## Open questions

<What isn't decided, and what would settle it. Naming an unknown here stops it from being
silently invented later. Required if status is `provisional`. Delete if there are none.>

## Related

<Sibling reference files, the specs they derive from, other repositories. Delete if
there are none.>
