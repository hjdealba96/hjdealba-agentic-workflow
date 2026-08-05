# Reference document slots

A reference document is made of **slots** — roles a piece of content plays for its reader.
Both skills in this plugin reason about slots rather than headings, for one reason: the
same slot goes by different names in different repositories. A file with `## Troubleshooting`
has not omitted `## Gotchas`; it has filled that slot under a local name.

**Always keep the repository's own name for a slot it already fills.** Renaming a heading
to match this plugin's vocabulary is churn with no reader benefit, and it makes every
existing link to that anchor break.

## The slots

| # | Slot | The reader question it answers | Names seen in the wild |
| --- | --- | --- | --- |
| 1 | **Trigger** | *Should I open this file at all?* | unnamed opening paragraph, `Overview`, `Purpose`, `Why this exists`, `Introduction` |
| 2 | **Status** | *Is it safe to act on this?* | `Status`, `State`, `Stability`, `Maturity` |
| 3 | **Scope** | *Does this govern the file I'm editing?* | `Applies to`, `Scope`, `Audience` |
| 4 | **Scope negation** | *What must I NOT conclude from this?* | `Not covered`, `Out of scope`, `Non-goals`, `What this isn't`, a bold caveat paragraph |
| 5 | **Compact lookup** | *Can I get my one fact without reading the body?* | `Quick reference`, `Quick Reference Summary`, `Summary`, `Cheat sheet`, `Decision Tree`, `TL;DR`, `Method Selection Guide` |
| 6 | **Rules + reasons** | *What am I supposed to do, and why?* | any topical heading |
| 7 | **Anti-patterns** | *What does the wrong version look like?* | `Anti-patterns`, `Anti-Patterns to Avoid`, `Common mistakes`, `What NOT to test`, `Don'ts` |
| 8 | **Traps** | *What will look like a bug but isn't?* | `Gotchas`, `Troubleshooting`, `Pitfalls`, `Known issues`, `Notes` |
| 9 | **Unknowns** | *What is undecided here?* | `Open questions`, `Open decisions`, `TBD` |
| 10 | **Links** | *Where do I go next?* | `Related`, `See also`, `References`, `Additional Resources` |

## Which are load-bearing

| Slot | Expectation | What happens when it's missing |
| --- | --- | --- |
| Trigger (1) | **Required** | A reader can't tell whether the file is relevant, so it gets opened always or never. `Overview` as the opener does not fill this slot — it describes the subject, not the moment of need. |
| Status (2) | **Required** | A stale file is indistinguishable from a current one, and decisions get built on it. |
| Scope (3) | **Required** | Rules get applied to modules they were never meant to govern. |
| Rules (6) | **Required** | There is no document. |
| Scope negation (4) | **Recommended** | The most common real failure: a reader treats a partial document as complete. Omit only when the title genuinely covers the whole topic. |
| Traps (8) | **Recommended** | The highest-value section in practice. Its absence usually means the knowledge is still only in someone's head. |
| Compact lookup (5) | Optional | Fine to omit on a short file. On a long one its absence forces a full read for a single fact. |
| Anti-patterns (7) | Optional | Omit when the rules have no recurring failure mode. If corrections keep recurring in review, this slot is missing. |
| Unknowns (9) | Optional, **required if status is `provisional`** | A provisional file with no open questions is either mislabeled or hiding the disagreement. |
| Links (10) | Optional | Cheap to add, rots quietly. Not worth flagging as a gap. |

## Two rules that come from the slots, not from any heading

**A table of contents is not a slot.** It answers no reader question that the headings
don't already answer, it duplicates them by hand, and it rots. Where one appears, treat it
as evidence the file grew too large — the fix is splitting the file, not maintaining the
list.

**Status carries no prose.** Slot 2 is the one field meant to be read mechanically, so
`status: settled` must be exactly one of `settled`, `provisional`, `undefined`. Every
qualifier a writer wants to append — "settled for the module layout only", "decided but
not wired up yet" — belongs in slot 4. Keeping the two separate is what makes
`grep -l 'status: provisional'` answer "what is still undecided in this project?" in one
command.

## Ordering

The default order is the funnel a reader actually follows: **scope → summary → detail →
traps → unknowns.**

```
frontmatter (2, 3) → trigger (1) → not covered (4) → quick reference (5)
  → rule groups (6) → anti-patterns (7) → gotchas (8) → open questions (9) → related (10)
```

The one placement worth insisting on is the compact lookup (5) going **near the top**.
Putting it last is the most common arrangement in the wild and the least useful one: in a
long file, the summary a reader came for is the last thing they reach.

A repository that has settled on a different order has settled on it — record the order as
a learning and follow it. Order is a convention; the slots are the substance.
