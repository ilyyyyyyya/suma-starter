# Setup — for the agent

This is a step-by-step install guide for the AI coding agent setting up Suma for the user. Read it end-to-end before doing anything.

## 1. Ask the user two questions before you touch the filesystem

1. **Where should the vault live?** Default suggestion: `~/Desktop/vault/`. The vault is where the user keeps notes, project files, etc. Suma is one folder inside it.
2. **Do they already have a folder of notes they want to keep?** If yes, Suma goes inside it. Plan around it instead of creating a new vault.

If they say "just pick sensible defaults", use `~/Desktop/vault/`. Everything Suma needs lives in one folder inside it, `vault/Suma/`. There's no separate code folder to place or configure.

## 2. Create the folder

```
mkdir -p ~/Desktop/vault/Suma
```

That's the only folder Suma needs. The renderer and the generated dashboard both live inside it, next to the sources. If the user picked a different vault path, substitute it. There are no constants to edit: `build.py` works out where it is from its own location.

## 3. Drop the markdown templates into `vault/Suma/`

Copy every file from this kit's `sources/` folder into `~/Desktop/vault/Suma/`:

- `dashboard.md`
- `projects.md`
- `ideas.md`
- `learning.md`
- `subscriptions.md`
- `changelog.md`
- `quotes.md` — starter quotes for the daily quote on the Dashboard; optional, but it ships filled so the feature works out of the box

The kit's `sources/` also contains a `people/` folder with a few example People notes. These are **not** Suma sources — they drive the "Birthdays this month" list on the Dashboard and live one level up, at the vault root:

```
cp -R sources/people/. ~/Desktop/vault/People/
```

Each note just needs a `**Birthday:** Month Day` line; the person's name comes from the filename. People notes are optional — skip this and the birthdays list stays hidden, no error. (For a quick local demo before installing, the renderer also reads `people/` next to `build.py` and the kit's `sources/people/`.)

`builds.md` and `toolkit.md` are **auto-generated** by `build.py` on each run (from your code folder and your coding-agent setup). There's nothing to copy for them, and you should never write them by hand.

## 4. Drop `build.py` into `vault/Suma/`

Copy this kit's `build.py` into `~/Desktop/vault/Suma/build.py`, right next to the markdown sources.

The script is stdlib-only — no `pip install` required. It works on macOS/Linux with system Python 3. There are no paths to configure: it reads the `.md` files in its own folder and writes `dashboard.html` there too.

One optional knob: the **Builds** tab scans `~/Desktop/code/` by default. If the user keeps code projects somewhere else (or nowhere), change the `CODE_ROOT` line near the top of `build.py`, or just leave it. An empty Builds tab is harmless.

## 5. Drop `CLAUDE.md` into the vault root

Copy this kit's `CLAUDE.md` into `~/Desktop/vault/CLAUDE.md`.

This is the file that tells any future agent (Claude Code, Cursor, etc.) how the user's vault is organised and how Suma works. The user can extend it over time with their own project lists, preferences, and writing style.

## 6. Fill in real content (with the user)

Run through these together — don't dump example content. Ask the user:

1. **What projects are you working on right now?** Get 2–8 names. Put them as `### Project Name` headers in `dashboard.md` under `## Now`, with one or two tasks under each.
2. **What's the one-line status of each?** Fill `projects.md` → `## Active` → `### Building`. Format: `- [Name] — what it is, current state. Next: thing.`
3. **Are any projects idle / dormant / done?** Move them into `## Idle / Resumable`.
4. **Anyone they sync with regularly?** Add `### Name` under `## Check-ins` in `dashboard.md` with a bullet or two of what to raise next time. Each person renders as a calm card.
   - Optional: if they keep People notes in `vault/People/`, add a `**Birthday:** Month Day` line to each so "Birthdays this month" populates on the Dashboard.
5. **What are they reading / watching / learning?** Seed the relevant sections of `learning.md`. It's fine to leave most sub-sections empty — they'll fill over time.
6. **Any recurring subscriptions worth tracking?** Optional. Seed `subscriptions.md` with a few real rows (name, amount, renewal date, which card). Fine to leave the template structure and fill later.
7. **What's a recent change worth logging?** Add today's date as `## YYYY-MM-DD` at the top of `changelog.md` with one or two bullets. This proves the round-trip works.

The **Builds** and **Toolkit** tabs need no content from you — they scan the machine on each rebuild. Toolkit reads the user's `~/.claude.json`, `~/.claude/` and `brew`/`npm`; if the user doesn't use a coding agent it just shows a quiet empty state. Nothing to set up.

## 7. Run the build

```
python3 ~/Desktop/vault/Suma/build.py
```

It should print a confirmation and write `~/Desktop/vault/Suma/dashboard.html`.

## 8. Open the dashboard

Double-click `dashboard.html` in Finder. It opens in the default browser. No server.

Bookmark it. Add it to the dock if you want. Some users put a shell alias like:

```
alias suma="python3 ~/Desktop/vault/Suma/build.py && open ~/Desktop/vault/Suma/dashboard.html"
```

## 9. Teach the user the loop

Every day, the loop is:

1. Edit one of the `.md` files in `~/Desktop/vault/Suma/`.
2. Run `python3 ~/Desktop/vault/Suma/build.py`.
3. Refresh the dashboard.

That's it. No app, no sync, no account.

When they say things like "update Suma about X" — that means: edit the right `.md` file, append a one-liner to today's section in `changelog.md`, then rebuild. See `CLAUDE.md` for the exact mapping.

## 10. Sanity-check before handoff

- [ ] `dashboard.html` opens and shows all eight tabs
- [ ] The Dashboard shows the daily quote (with a working swap button), the calendar (today marked), the activity heatmap, the Now and Check-in cards, and — if People notes have birthdays this month — the birthdays list
- [ ] Each tab has at least placeholder content (so the user can see what goes where)
- [ ] Changelog has today's date with one real entry
- [ ] The user knows the single command to rebuild
- [ ] `CLAUDE.md` is in the vault root, not just inside `Suma/`

## Common pitfalls

- **Moved `build.py`**: it must stay inside the `Suma/` folder, next to the sources — it locates everything relative to its own position. Don't move it off into a separate code folder.
- **Wrong filenames**: the script reads specific filenames (`dashboard.md`, `projects.md`, etc.). Don't rename them. Don't add `.txt`. Don't capitalise them.
- **Empty `## Now` section**: the renderer is fine with it but the dashboard reads dead. Seed it.
- **Auto-generated `builds.md`**: don't edit by hand. If the user wants a build listed differently, fix the underlying repo's `README.md` or git remote.
- **`quotes.md`**: the renderer shows one quote a day on the Dashboard, pulled from `Suma/quotes.md` and rotated by date. The kit ships a starter set, so it works immediately. It's optional — delete the file and the quote area is just empty, no error. The user can prune or add their own; headings and `---` rules in the file are ignored.
