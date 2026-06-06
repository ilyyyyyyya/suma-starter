# CLAUDE.md

This file lives at the root of the user's vault and tells any AI coding agent (Claude Code, Cursor, etc.) how to work inside it. The user should extend it over time with their own project list, preferences, and writing style.

## Purpose

This vault is the user's personal knowledge operating system. Everything in one place — thinking, building, AI context. It embraces chaos and laziness to create emergent structure, instead of forcing a rigid filing system.

## Path References

When the user says "vault" they mean this directory (`~/Desktop/vault/`).

When the user says "Suma" or "suma" they mean the personal dashboard. The markdown sources live at `Suma/` in the vault; the renderer and rendered HTML live in a sibling code folder at `~/Desktop/code/12-suma/`.

## Folder Structure (suggested — adapt to fit)

```
vault/
├── CLAUDE.md
├── Suma/           # Personal dashboard (see Suma section below)
├── Drafts/         # Where temp writing, notes, ideas live
├── Projects/       # Projects — some have subfolders, others are single .md files
├── Library/        # Collected content (read, listened, watched)
├── People/         # People you know with context and history
├── Recipes/        # Guides, how-tos, playbooks, process docs
└── Records/        # Personal tracking data (health, books, etc.)
```

Not every folder is mandatory. The only one Suma actually needs is `Suma/`.

## Suma

Suma is the personal dashboard. Markdown sources live in the vault at `Suma/`; the renderer and rendered HTML live at `~/Desktop/code/12-suma/`.

**In the vault (`vault/Suma/`):**
- `dashboard.md` — Now (project-grouped checkbox tasks) + Check-ins
- `projects.md` — Overview + Active + Idle / Resumable project state
- `ideas.md` — sketched, not built; promote into Active in `projects.md` when one earns the time
- `learning.md` — what you're learning, reading, watching, saving
- `subscriptions.md` — recurring subscriptions, renewal dates, and which card pays for each
- `changelog.md` — running log of moves, additions, status changes; newest date first
- `quotes.md` — optional starter quotes for the daily quote on the Dashboard; one shown per day, rotated by date
- `builds.md` — **auto-generated** by `build.py` from `~/Desktop/code/`; do not edit by hand
- `toolkit.md` — **auto-generated** by `build.py` from `~/.claude/` + `brew`/`npm` (your MCP servers, skills, plugins, commands, CLIs); do not edit by hand

**In the code folder (`~/Desktop/code/12-suma/`):**
- `build.py` — stdlib-only renderer; no `pip install` required
- `dashboard.html` — generated single-page view; open by double-click, no server needed

**Suma conventions:**

- **Now** (`dashboard.md`): project-grouped checkbox tasks. One `### Project` heading per active project + `### Personal` at the bottom for personal to-dos. Toggle by editing the markdown: `- [ ] thing` ↔ `- [x] thing`. Do not create a standalone Personal section anywhere else in Suma.
- **Projects** (`projects.md`): starts with `## Overview` — ~5 short portfolio-summary bullets (counts, primary bets, this week's push, things to watch). Then `## Active` with `### Building` and `### Advising / helping` sub-groups, then `## Idle / Resumable`. Each project is one short status sentence + a "Next:" clause. Scannable, not a project doc.
- **Check-ins** (`dashboard.md`): one `### Name` per person, agenda items as plain bullets (not checkboxes — check-ins recur, they don't complete).
- **Don't duplicate across files**: tasks go in Now, project state goes in Projects, people sync goes in Check-ins.

When the user says things like:

- "update Suma about it"
- "add this to Suma"
- "Suma — move X to idle"
- "log this in Suma"

→ edit `Suma/dashboard.md` (tasks / check-ins) or `Suma/projects.md` (project state) and/or append a one-line entry to today's section in `Suma/changelog.md`, then run `python3 ~/Desktop/code/12-suma/build.py` to regenerate the dashboard. If today's date heading doesn't exist yet in changelog, add it at the top.

Keep one-line discipline: each project gets one line on the dashboard. Detail goes in the project file, not the dashboard.

**Write Suma entries in plain language.** Suma is for the user to read back later, not for shipping documentation. Read like a teammate summary, not a commit log.

- Lead with what's true for the user or what changed in plain terms — not the code that moved.
- Avoid component names, file paths, env var names, framework jargon unless truly load-bearing.
- One clause per bullet. No nested parenthetical lists.
- Prefer "added X" / "renamed Y → Z" / "live at <url>" / "next: <thing>" over verbose breakdowns.
- Technical detail belongs inside project files or GitHub issues, not Suma.

**Suma is the single source of truth for current focus, task tracking, project status, and ongoing inputs (reading/learning/bookmarks).** Don't create dashboard-style files anywhere else in the vault — no `Things To Do.md`, no `overview.md`, no per-folder mirrors. If something is worth tracking at a focus level, it goes in Suma. Project-internal notes (plans, dated logs, drafts) still live inside `Projects/[project]/` as before.

## Philosophy

**Avoid folders for organisation.**
- Use very few folders.
- Many entries belong to more than one area of thought.
- System is oriented towards speed and laziness.
- No overhead of considering where something should go.

**Avoid non-standard Markdown.**
- Keep it simple and portable.

**Use YYYY-MM-DD dates everywhere.**
- Consistent, sortable, unambiguous.

**Use kebab-case for all file and folder names.**
- Example: `game-design.md`, `yoga-website/`.
- Exception: `README.md` and `CLAUDE.md` (standard conventions).
- No spaces, no underscores, no capitals (except special files).

## File Creation Rules

Before creating any new files in this vault:

1. Read this `CLAUDE.md` if you haven't already.
2. Check existing files in the target folder to see naming patterns.
3. Follow `YYYY-MM-DD_kebab-case` format for dated content in `Drafts/`.
4. When in doubt, look first, create second.

## Preferences

- Keep things simple.
- Files over apps.
- Practical over perfect.
- The user's name, role, and any other personal context go in `Records/[name].md` if they want a persistent profile.

## Writing Style

When helping with or editing writing in this vault:

- **Em dashes**: default to none. Rewrite with a comma, a period, or two sentences instead. Keep one only if removing it genuinely breaks the meaning, which should be rare.
- **Avoid AI-sounding phrases**: "But X made me hear it differently", "What strikes me now", "I've stopped finding that strange" — these read as generated. Keep language plain and direct.
