# DESIGN.md

Visual and UX rules baked into Suma. The renderer (`build.py`) implements them — these notes are for any agent extending or rewriting it.

## Core principle: Suma stays visually calm

Quiet text and whitespace IS the design. Suma is for the user to read back, not to perform. Prefer invisible-by-default changes (auto-archive, hide empty headings, smarter sort) over dashboard furniture.

**Do not add:**

- Status strips ("All systems go", "On track", coloured banners)
- Coloured "Focus" blocks, KPI tiles, "today's highlight" cards
- Age chips ("3 days ago", "stale", "fresh")
- Progress bars on tasks
- Loud stats / counts as visual elements (the muted count badge on Now/Check-in cards and the Overview block on Projects are the only exceptions — both are quiet, not coloured)
- Emojis in source markdown
- Avatars, profile circles, anything social-feed-shaped

**Carved exceptions (Dashboard widgets):**

Two Dashboard widgets bend the "no charts" rule, deliberately and quietly:

- **Calendar** — a plain current-month grid, today marked with a single filled dot. No data, no trend line.
- **Activity heatmap** — a contribution-graph grid built from changelog dates. This is the one chart in Suma. It is allowed *only* because it stays inside the calm palette: a monochrome ink ramp (not GitHub blue), no axes, no numbers in the grid, just five shaded levels and a one-line text meta. If you add any other chart, sparkline, or graph anywhere else, you are breaking the rule — these two are the whole budget.

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

Unrecognised headings fall back to the neutral `MIST` dot (`SECTION_DOTS.get(title, "MIST")`). If you add a new section that deserves its own colour, add it to `SECTION_DOTS` deliberately rather than relying on the fallback.

## Tabs

Eight tabs, in this order:

1. **Dashboard** — daily quote, a calendar + activity-heatmap widget row, then Now, Check-ins, and Birthdays this month
2. **Projects** — Overview + Active + Idle / Resumable
3. **Ideas**
4. **Learning**
5. **Subscriptions**
6. **Builds** — auto-scanned
7. **Toolkit** — auto-scanned
8. **Changelog**

Don't reorder. Dashboard is where the user lands every time, so it must be tab one.

**Builds** and **Toolkit** have no markdown source. They scan the machine on each rebuild and render themselves. Both degrade quietly: Builds with no code folder shows a one-line note, and Toolkit on a machine with no coding-agent setup shows a quiet empty state rather than an error. Everything else is markdown-backed, one source file per tab.

## Now

- One `### Project Name` heading per active project, in roughly priority order.
- `### Personal` last.
- Bullets are GitHub-style checkboxes: `- [ ] thing` or `- [x] done thing`.
- The renderer draws each project as a quiet collapsible card with a muted count badge; tasks inside get a small round dot bullet (dimmed when done).
- Completed `[x]` tasks are archived into the changelog on the next build (see `archive_completed_tasks`), so the card shows what's still open.
- The card named `DEFAULT_OPEN_GROUP` (near the top of `build.py`) starts expanded; set it to "" to start them all closed.
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
- Renders as the same calm card style as Now (count badge + dotted bullets), under a small "Check-ins" label.
- Keep agenda short — 1-5 bullets per person. If it's growing past that, the user is hoarding agenda items.

## World clock

- A row of live clocks sits at the very top of the Dashboard, rendered in the browser and refreshed every 10s. Each card shows the city, UTC offset, time, and a day/night marker; one card is highlighted as primary.
- Cities are a small list in the world-clock `<script>` in `build.py` (default: San Francisco, New York, London). Edit that array — `{ name, tz, primary }` with an IANA timezone — to use your own. Optional; remove the `<nav class="worldclock">` and its script to drop it.

## Calendar + Activity widgets

- A two-column **widget row** sits between the quote and Now: calendar on the left (fixed width), activity heatmap on the right (flexible), stacking on narrow screens.
- **Calendar** is rendered live in the browser from the visitor's clock — current month, Monday-first, weekends muted, today a filled dot. No source file, no Python data.
- **Activity heatmap** is built in `build.py` from `changelog.md` dates (`scan_activity` / `render_activity_html`). One cell per day, five monochrome shade levels, hover title per cell, one-line meta. See the carved exception under "Do not add" above.

## Birthdays this month

- A quiet name/date list under Now/Check-ins, showing only people whose birthday is in the current month; hidden entirely when there are none.
- Source is People notes with a `**Birthday:** Month Day` line. The renderer looks in `vault/People/` (installed layout), then a `people/` folder next to `build.py`, then the kit's `sources/people/` staging copy.
- Today's birthday is highlighted and labelled "Today"; earlier days this month are dimmed.

## Token usage

- A widget at the **bottom of the Dashboard** showing Claude Code token spend over time. Built entirely in `build.py` (`scan_token_usage` / `render_usage_html`) — it reads the JSONL session transcripts under `~/.claude/projects`, so there is no source `.md` file.
- A `7D / 30D / All` segmented control switches the window; the bar chart, y-axis, totals, and per-model breakdown all re-render client-side. A `% vs prev` delta compares the window to the one before it. Hover a bar for a day's exact tokens + estimated cost.
- Cost is **estimated** at API list rates (cache writes 1.25×, reads 0.1×); it is not your actual bill, which depends on your plan. Labelled as such in the footer.
- Stays calm: monochrome bars, quiet gridlines, no coloured KPI tiles. If `~/.claude/projects` is absent (e.g. you don't use Claude Code), it renders a quiet empty state.
- **Retention caveat:** Claude Code deletes session transcripts older than `cleanupPeriodDays` (default 30). "All" can only show data still on disk, so raise that setting in `~/.claude/settings.json` if you want the chart to accumulate real history. See SETUP.md.

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

## Subscriptions

- A plain markdown tab. `## Status`, `## Monthly estimate`, `## To check / cancel`, then an `## Active` list.
- Each row is one line: `- **Name** — monthly/yearly, amount; renews <date>; <card>.`
- The point is a single glanceable run-rate, not an accounting ledger. Keep it scannable.

## Builds

Auto-generated. The renderer:

1. Walks `~/Desktop/code/*`
2. For each subfolder, reads `.git/config` for the GitHub remote
3. Looks in the folder's `README.md` for a deploy URL (`*.vercel.app`, `*.netlify.app`, etc.)
4. Groups results into **Live** / **On git, not deployed** / **Local only**
5. Writes the result to `Suma/builds.md` AND renders it into the dashboard

Don't edit `builds.md` by hand. To change what's listed, fix the underlying repo's `README.md` or git remote.

## Toolkit

Auto-generated. Surfaces the otherwise-invisible coding-agent environment so the user can actually see what they have. The renderer:

1. Reads `~/.claude.json` for configured MCP servers (global + per-project)
2. Reads `~/.claude/skills/` and installed-plugin skills (name + description from each `SKILL.md`)
3. Reads installed plugins, personal slash-commands, and CLIs (`brew leaves`, `brew --cask`, global npm packages, `claude`)
4. Groups into **MCP servers / Skills / Plugins / Commands / CLIs**, hiding any section that's empty
5. Writes the result to `Suma/toolkit.md` AND renders it into the dashboard

Rows reuse the calm `build-tag` chip for scope/source (e.g. `global`, `personal`, `brew`) — muted, not coloured. Don't add coloured status chips here. If the whole toolkit is empty (no agent setup on this machine), the tab shows one quiet line instead of an error. Don't edit `toolkit.md` by hand; install or remove the actual tool instead.

## Changelog

- Newest day at the top.
- One `## YYYY-MM-DD` heading per day.
- Bullets are plain: `- **Project** what changed in plain language.`
- No timestamps within a day — order within a date doesn't need to be precise.
- The rendered header on the Changelog tab auto-derives "last updated" from the most recent date heading.

## Daily quote

- One quote sits at the top of the Dashboard as a calm card: a large decorative quote-mark in the left gutter, the quote text, the author below, and a small circular swap button top-right.
- Source is `Suma/quotes.md`: quote then `— Attribution`, blank line between entries. Headings (lines starting with `#`) and `---` rules are ignored, so the file can be grouped into categories.
- The renderer splits the author out of each chunk (`split_quote`) so the quote and attribution style separately.
- It picks one per day deterministically (rotates by date), so it's stable within a day and changes tomorrow. No randomness, no API for the daily pick.
- The swap button cycles to another quote instantly, client-side, from a JSON list of all quotes embedded in the page. No rebuild needed; the daily pick is unchanged on reload.
- Optional. No file means no quote, not an error. Keep it calm — the card is muted, not coloured.

## Plain language rule (this applies to every tab)

Suma is read back by the user, not by stakeholders. Bullets should read like a teammate update.

Good:
- `- **Project One** moved to a faster host — auto-deploys when I push`
- `- **Project Two** dropped the v2 tasks from Now — still active, just not in current focus`

Bad:
- `- **Project One** switched the build to static export and moved the signup route same-origin, old deploy action disabled`
- `- **Project Two** removed the v2 task list from active focus per the project review meeting`

If a bullet needs commit-message specifics, those belong in the project's GitHub issues or internal notes — not in Suma.
