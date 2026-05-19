# Suma Starter

A starter kit for a personal dashboard system called **Suma**. Hand this folder to an AI coding agent (Claude Code, Cursor, etc.) and ask it to set up Suma for you.

Suma is markdown-in, HTML-out. You edit a handful of `.md` files in a "vault" folder, run one script, and get a clean single-page dashboard you double-click to open. No server. No app. No database. No `pip install`.

It was originally built by Ilya as part of a wider personal knowledge vault. This starter strips it down to just the dashboard layer so anyone can adopt it.

---

## What's in this folder

```
suma-starter/
├── README.md          ← you are here
├── SETUP.md           ← step-by-step for the agent installing this
├── CLAUDE.md          ← rules the agent should follow while working in your vault
├── DESIGN.md          ← visual / UX conventions baked into the renderer
├── build.py           ← stdlib-only renderer (markdown → dashboard.html)
└── sources/           ← templates for the markdown files you'll edit day-to-day
    ├── dashboard.md
    ├── projects.md
    ├── ideas.md
    ├── learning.md
    └── changelog.md
```

`builds.md` is **auto-generated** by `build.py` from your `~/Desktop/code/` folder — don't write it by hand.

---

## What Suma actually is

Suma is one HTML page with six tabs:

1. **Dashboard** — "Now" (project-grouped checkbox to-dos) + "Check-ins" (one section per person you sync with, agenda bullets)
2. **Projects** — Overview (~5 portfolio bullets) + Active (Building / Advising) + Idle / Resumable. One line per project: status + "Next:" clause.
3. **Ideas** — Sketched, not built. Promote into Projects when one earns the time.
4. **Learning** — Currently reading / Books / Watch / Leisure / Articles / Tools / Design refs / People / Bookmarks. An inventory, not tasks.
5. **Builds** — Auto-scanned list of code projects on your machine, grouped by deploy status (live / on git / local only).
6. **Changelog** — A running log of what changed in the vault. Newest day first, one line per change.

Each tab maps to exactly one source file in `sources/`. The whole point is that you write plain markdown and the dashboard renders itself.

---

## How it works

1. You keep a folder of markdown files somewhere on disk (the "vault").
2. Inside the vault, a `Suma/` subfolder holds the six source files above.
3. A Python script in a sibling code folder (`~/Desktop/code/12-suma/build.py`) reads those `.md` files and writes a single `dashboard.html` next to itself.
4. You double-click `dashboard.html` to view it. No server needed.

The vault and the renderer must live as **siblings**:

```
~/Desktop/
├── vault/                ← your markdown lives here
│   └── Suma/
│       ├── dashboard.md
│       ├── projects.md
│       ├── ideas.md
│       ├── learning.md
│       └── changelog.md
└── code/
    └── 12-suma/
        ├── build.py
        └── dashboard.html   ← generated, you open this
```

The `12-` prefix is just Ilya's habit of numbering project folders alphabetically. The agent can rename it; just make sure to update the path inside `build.py`.

---

## Conventions worth keeping

These are load-bearing — break them and the dashboard reads worse over time, not better.

- **One source of truth.** Tasks go in `dashboard.md` (Now). Project state goes in `projects.md`. Don't duplicate.
- **One line per project on the dashboard.** Detail goes inside the actual project's notes, not Suma.
- **Now is project-grouped checkboxes.** `### Project Name` headers, then `- [ ] thing` bullets. Toggle by editing the file.
- **Check-ins are plural recurring agendas, not tasks.** Use plain bullets, not checkboxes — they don't "complete".
- **Plain language in Suma entries.** Write like a teammate summary, not a commit log. No file paths, env vars, component names in changelog bullets — that detail belongs inside project notes.
- **YYYY-MM-DD dates everywhere.** Sortable, unambiguous.
- **kebab-case filenames.** No spaces, no underscores, no capitals. `README.md` and `CLAUDE.md` are the only exceptions.
- **Newest entry first** in changelog. Each day gets one `## YYYY-MM-DD` heading at the top.
- **Suma stays visually calm.** No status strips, no coloured "Focus" blocks, no KPI tiles. Quiet text + whitespace IS the design.

---

## Next steps for your agent

Open `SETUP.md` and follow it. It walks through:

1. Picking where the vault lives
2. Setting up the folder structure
3. Copying `build.py` into place
4. Filling in your first real content
5. Running the build and opening the dashboard

After setup, `CLAUDE.md` and `DESIGN.md` are the rules the agent should follow on every future Suma edit.

---

## Credits

System designed and built by **Ilya** ([ilyyya.com](https://www.ilyyya.com/)). Shared as a starter for anyone who wants the same dashboard for their own work.
