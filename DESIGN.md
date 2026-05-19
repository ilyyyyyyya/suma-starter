# DESIGN.md

Visual and UX rules baked into Suma. The renderer (`build.py`) implements them — these notes are for any agent extending or rewriting it.

## Core principle: Suma stays visually calm

Quiet text and whitespace IS the design. Suma is for the user to read back, not to perform. Prefer invisible-by-default changes (auto-archive, hide empty headings, smarter sort) over dashboard furniture.

**Do not add:**

- Status strips ("All systems go", "On track", coloured banners)
- Coloured "Focus" blocks, KPI tiles, "today's highlight" cards
- Age chips ("3 days ago", "stale", "fresh")
- Progress bars on tasks
- Stats / counts as visual elements (apart from the Overview block on Projects, which is plain text bullets)
- Emojis in source markdown
- Avatars, profile circles, anything social-feed-shaped
- Sparklines, charts, graphs

**Do keep:**

- One tab bar at the top
- Plain heading hierarchy (H2 = section, H3 = subsection)
- A small coloured dot before each section heading (the only chrome the renderer adds — see Section dots below)
- Generous whitespace between sections
- Monospace-feeling, readable serif/sans body — not display fonts

## Section dots

Each H2 (and certain H3s) gets a small coloured gradient dot beside its heading. This is the one bit of visual identity in Suma. The mapping is in `build.py` (`SECTION_DOTS` and `GRADIENT_CLASSES`).

Default palette and intent:

| Class       | Used for                              |
|-------------|---------------------------------------|
| `VIBRANT`   | High-energy attention (Now, primary project) |
| `COOL`      | Forward momentum (Active, currently reading) |
| `SUNSET`    | Creative / generative (Ideas)         |
| `WARM`      | Human / domestic (Personal, Check-ins) |
| `FOREST`    | Text content (Books, Articles)        |
| `TWILIGHT`  | Video / passive (Watch, Leisure)      |
| `SAND`      | Quiet / dormant (Idle, To review, Other bookmarks) |
| `MIST`      | Utility / neutral (Tools, People, Overview) |

Unrecognised headings get no dot, not a default colour — that's intentional; new sections should be a deliberate choice.

## Tabs

Six tabs, in this order:

1. **Dashboard** — Now + Check-ins
2. **Projects** — Overview + Active + Idle / Resumable
3. **Ideas**
4. **Learning**
5. **Builds** — auto-generated
6. **Changelog**

Don't reorder. Dashboard is where the user lands every time, so it must be tab one.

## Now

- One `### Project Name` heading per active project, in roughly priority order.
- `### Personal` last.
- Bullets are GitHub-style checkboxes: `- [ ] thing` or `- [x] done thing`.
- The renderer hides completed items by default (or visually de-emphasises them — implementation choice).
- An empty project heading should not appear on the rendered page. Either the renderer hides it, or the user removes the heading manually.

## Projects

- `## Overview` first: ~5 plain-text bullets that summarise the portfolio at a glance.
- `## Active` second, split into `### Building` and `### Advising / helping`.
- `## Idle / Resumable` last.
- Each project is **one line**:
  - For Active: `- [Name](Projects/name/) — what it is. Current state. Next: thing.`
  - For Idle: `- [Name](Projects/name/) — what it is. Status (e.g. "Done", "Resume: thing").`
- Bold counts in Overview, italics for asides, but no other formatting tricks.

## Check-ins

- One `### Name` per person.
- Plain bullets, NOT checkboxes. Agenda items recur; they don't "complete".
- Keep agenda short — 1-5 bullets per person. If it's growing past that, the user is hoarding agenda items.

## Ideas

- Plain bulleted list. No subsections.
- Each idea is one line: `- [Name](Projects/name.md) — one sentence describing it.`
- Empty most of the time is fine.

## Learning

Sub-section order matters — it's a rough flow from "actively engaged" → "queued" → "passive consumption" → "reference".

1. Currently reading
2. Books
3. Watch
4. Leisure
5. Articles & longreads
6. Tools & apps
7. Design references
8. People & blogs
9. Other bookmarks
10. To review (raw inbox)
11. Twitter bookmarks
12. Project-specific (`### ProjectName` blocks — optional, at the bottom)

Each item is one line, link-first where possible: `- [Title](url) — one-sentence context.`

## Builds

Auto-generated. The renderer:

1. Walks `~/Desktop/code/*`
2. For each subfolder, reads `.git/config` for the GitHub remote
3. Looks in the folder's `README.md` for a deploy URL (`*.vercel.app`, `*.here.now`, etc.)
4. Groups results into **Live** / **On git, not deployed** / **Local only**
5. Writes the result to `Suma/builds.md` AND renders it into the dashboard

Don't edit `builds.md` by hand. To change what's listed, fix the underlying repo's `README.md` or git remote.

## Changelog

- Newest day at the top.
- One `## YYYY-MM-DD` heading per day.
- Bullets are plain: `- **Project** what changed in plain language.`
- No timestamps within a day — order within a date doesn't need to be precise.
- The rendered header on the Changelog tab auto-derives "last updated" from the most recent date heading.

## Plain language rule (this applies to every tab)

Suma is read back by the user, not by stakeholders. Bullets should read like a teammate update.

Good:
- `- **Pranasalt** site moved to a faster host — auto-deploys when I push`
- `- **MADS** dropped MADS 2x tasks from Now — still active as a project, just not in current focus`

Bad:
- `- **Pranasalt** `next.config.ts` dropped `output: "export"`, `/api/waitlist` now a same-origin Next route, here.now Action disabled`
- `- **MADS** Removed MADS_2x_TASKS_v2 from active focus per project review meeting outcome`

If a bullet needs commit-message specifics, those belong in the project's GitHub issues or internal notes — not in Suma.
