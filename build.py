#!/usr/bin/env python3
"""
Render Suma: markdown sources in vault/Suma/ → dashboard.html in the same folder.

Everything lives in one folder, `Suma/`, inside your vault:
    your-vault/Suma/
        build.py          (this script)
        dashboard.md, projects.md, ...  (the sources you edit)
        dashboard.html    (generated — open this)

No separate code folder, no path config. The script reads the .md files next to
it and writes dashboard.html alongside them. Vault-relative links in the source
(e.g. `Projects/notes/`) are rewritten to `../Projects/notes/` so the rendered
HTML, sitting in Suma/, can reach the rest of the vault one level up.

Run it (stdlib only, no pip install):
    python3 build.py            # from inside the Suma folder
    python3 path/to/Suma/build.py
"""

from __future__ import annotations

import base64
import datetime as _dt
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent   # this is your vault's Suma/ folder
SUMA = SCRIPT_DIR                               # sources + this script live together
VAULT = SCRIPT_DIR.parent                       # the vault root, one level up from Suma/
ROOT = VAULT
# Only the Builds tab uses this — where your code projects live. Edit if yours
# are elsewhere; if the folder doesn't exist, the Builds tab just shows nothing.
CODE_ROOT = Path.home() / "Desktop" / "code"
DASH_SRC = SUMA / "dashboard.md"
LOG_SRC = SUMA / "changelog.md"
LEARN_SRC = SUMA / "learning.md"
IDEAS_SRC = SUMA / "ideas.md"
PROJ_SRC = SUMA / "projects.md"
SUBS_SRC = SUMA / "subscriptions.md"
BUILDS_OUT = SUMA / "builds.md"
TOOLKIT_OUT = SUMA / "toolkit.md"
QUOTES_SRC = SUMA / "quotes.md"
OUT = SCRIPT_DIR / "dashboard.html"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

SECTION_DOTS = {
    # Dashboard sections (H2)
    "Overview": "MIST",                 # portfolio summary
    "Now": "VIBRANT",                   # high-energy attention
    "Active": "COOL",                   # forward momentum
    "Idle / Resumable": "SAND",         # quiet / dormant
    "Ideas": "SUNSET",                  # creative / generative
    "Personal": "WARM",                 # human / domestic
    "Check-ins": "WARM",
    "Learning": "MIST",
    "Subscriptions": "FOREST",
    # Toolkit sections
    "MCP servers": "COOL",
    "Skills": "VIBRANT",
    "Plugins": "TWILIGHT",
    "Commands": "SUNSET",
    "CLIs": "FOREST",
    # Learning sub-sections (H3) — used by their own TOC
    "Currently reading": "COOL",
    "Now learning": "VIBRANT",          # a focus topic
    "Books": "FOREST",                  # text content
    "Articles & longreads": "FOREST",
    "Watch": "TWILIGHT",                # video / passive
    "Leisure": "TWILIGHT",
    "Tools & apps": "MIST",             # utility
    "Design references": "MIST",
    "People & blogs": "MIST",
    "Other bookmarks": "SAND",
    "To review": "SAND",
    "Twitter bookmarks": "MIST",
}

GRADIENT_CLASSES = {
    "VIBRANT": "dot-vibrant",
    "COOL": "dot-cool",
    "SUNSET": "dot-sunset",
    "WARM": "dot-warm",
    "FOREST": "dot-forest",
    "TWILIGHT": "dot-twilight",
    "SAND": "dot-sand",
    "MIST": "dot-mist",
    # Backward-compatible alias
    "GRADIENT": "dot-vibrant",
}


def dot_html(color: str) -> str:
    if color in GRADIENT_CLASSES:
        return f'<span class="dot {GRADIENT_CLASSES[color]}"></span>'
    return f'<span class="dot" style="background:{color}"></span>'


def rewrite_link(url: str) -> str:
    """dashboard.html sits in vault/Suma/, so a vault-relative link resolves one
    level up (../). External and already-relative links pass through unchanged."""
    if url.startswith(("http://", "https://", "mailto:", "#", "/", "../")):
        return url
    return "../" + url


def render_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{rewrite_link(m.group(2))}">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def slug(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s-]+", "-", s)


def md_to_html(md: str) -> tuple[str, list[tuple[int, str, str]]]:
    lines = md.splitlines()
    out: list[str] = []
    toc: list[tuple[int, str, str]] = []
    i = 0
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            close_list()
            i += 1
            continue

        if line.startswith("---") and set(line.strip()) == {"-"}:
            close_list()
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            close_list()
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = slug(title)
            toc.append((level, anchor, title))
            if level == 2 and not DATE_RE.match(title):
                color = SECTION_DOTS.get(title, "MIST")
                out.append(
                    f'<h2 id="{anchor}">'
                    f'{dot_html(color)}'
                    f'{render_inline(title)}'
                    f'</h2>'
                )
            elif level == 2 and DATE_RE.match(title):
                out.append(
                    f'<h2 id="{anchor}" class="date">{render_inline(title)}</h2>'
                )
            else:
                out.append(
                    f'<h{level} id="{anchor}">{render_inline(title)}</h{level}>'
                )
            i += 1
            continue

        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            content = line[2:]
            while i + 1 < len(lines) and lines[i + 1].startswith("  "):
                content += " " + lines[i + 1].strip()
                i += 1
            cb = re.match(r"^\[([ xX])\]\s+(.*)$", content)
            if cb:
                checked = cb.group(1).lower() == "x"
                klass = "task task-done" if checked else "task"
                mark = "✓" if checked else ""
                out.append(
                    f'<li class="{klass}">'
                    f'<span class="check" aria-hidden="true">{mark}</span>'
                    f'<span class="task-text">{render_inline(cb.group(2))}</span>'
                    f'</li>'
                )
            else:
                out.append(f"<li>{render_inline(content)}</li>")
            i += 1
            continue

        close_list()
        para = [line]
        while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(
            r"^(#|-|\s*---)", lines[i + 1]
        ):
            i += 1
            para.append(lines[i])
        out.append(f"<p>{render_inline(' '.join(para))}</p>")
        i += 1

    close_list()
    return "\n".join(out), toc


def build_toc(toc: list[tuple[int, str, str]], level: int = 2) -> str:
    items = []
    for lv, anchor, title in toc:
        if lv != level:
            continue
        if DATE_RE.match(title):
            continue
        color = SECTION_DOTS.get(title, "MIST")
        items.append(
            f'<a href="#{anchor}">'
            f'{dot_html(color)}'
            f'{html.escape(title)}'
            f'</a>'
        )
    return "\n".join(items)


def latest_changelog_date(md: str) -> str:
    """Return the most recent YYYY-MM-DD heading from changelog.md, or ''."""
    dates = []
    for line in md.splitlines():
        m = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})", line)
        if m:
            dates.append(m.group(1))
    return max(dates) if dates else ""


_COMPLETED_TASK_RE = re.compile(r"^-\s+\[[xX]\]\s+(.+)$")


def archive_completed_tasks() -> int:
    """Move [x] tasks under `## Now` from dashboard.md into today's changelog entry.

    Modifies both source files in place. Returns the number of tasks archived.
    Tasks outside the Now section (e.g. under Check-ins) are left untouched.
    """
    dash_md = DASH_SRC.read_text(encoding="utf-8")
    log_md = LOG_SRC.read_text(encoding="utf-8")

    lines = dash_md.splitlines()
    out_lines: list[str] = []
    archived: list[tuple[str, str]] = []
    current_h2: str | None = None
    current_h3: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m2 = re.match(r"^##\s+(.+?)\s*$", line)
        if m2:
            current_h2 = m2.group(1).strip()
            current_h3 = None
            out_lines.append(line)
            i += 1
            continue
        m3 = re.match(r"^###\s+(.+?)\s*$", line)
        if m3:
            current_h3 = m3.group(1).strip()
            out_lines.append(line)
            i += 1
            continue
        cb = _COMPLETED_TASK_RE.match(line)
        if cb and current_h2 == "Now":
            content = cb.group(1).strip()
            while i + 1 < len(lines) and lines[i + 1].startswith("  "):
                content += " " + lines[i + 1].strip()
                i += 1
            project = current_h3 or "Misc"
            archived.append((project, content))
            i += 1
            continue
        out_lines.append(line)
        i += 1

    if not archived:
        return 0

    new_dash = "\n".join(out_lines)
    if dash_md.endswith("\n") and not new_dash.endswith("\n"):
        new_dash += "\n"

    today = _dt.date.today().isoformat()
    today_heading = f"## {today}"
    archive_bullets = [f"- **{p}** done: {t}" for p, t in archived]

    log_lines = log_md.splitlines()
    today_idx: int | None = None
    for idx, line in enumerate(log_lines):
        if line.strip() == today_heading:
            today_idx = idx
            break

    if today_idx is None:
        insert_at = None
        for idx, line in enumerate(log_lines):
            if re.match(r"^##\s+\d{4}-\d{2}-\d{2}", line):
                insert_at = idx
                break
        if insert_at is None:
            insert_at = len(log_lines)
        block = [today_heading, ""] + archive_bullets + [""]
        log_lines = log_lines[:insert_at] + block + log_lines[insert_at:]
    else:
        insert_at = today_idx + 1
        if insert_at < len(log_lines) and log_lines[insert_at].strip() == "":
            insert_at += 1
        log_lines = log_lines[:insert_at] + archive_bullets + log_lines[insert_at:]

    new_log = "\n".join(log_lines)
    if log_md.endswith("\n") and not new_log.endswith("\n"):
        new_log += "\n"

    DASH_SRC.write_text(new_dash, encoding="utf-8")
    LOG_SRC.write_text(new_log, encoding="utf-8")
    return len(archived)


def load_quotes() -> list[str]:
    """Read Suma/quotes.md and return a list of quote chunks (paragraph-separated).

    Optional file. Each chunk is a quote plus its attribution line. Markdown
    headings (`# Quotes`, `## Section`) and horizontal rules are skipped, so the
    file can be organised into categories without those leaking in as quotes.
    """
    if not QUOTES_SRC.exists():
        return []
    text = QUOTES_SRC.read_text(encoding="utf-8")
    chunks = re.split(r"\n\s*\n", text)
    quotes = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if set(chunk) <= set("-—"):           # horizontal-rule separator
            continue
        if chunk.startswith("#"):              # markdown heading, not a quote
            continue
        quotes.append(chunk)
    return quotes


def pick_quote_for_today(quotes: list[str]) -> str:
    """Deterministic pick: same quote all day, rotates daily."""
    if not quotes:
        return ""
    seed = _dt.date.today().toordinal()
    return quotes[seed % len(quotes)]


_Q_OPEN = "“‘\"'«„"
_Q_CLOSE = "”’\"'»"
_Q_DASH_RE = re.compile(r"[—–―]")


def _strip_wrap_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] in _Q_OPEN and s[-1] in _Q_CLOSE:
        return s[1:-1].strip()
    return s


def _looks_like_author(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 60:
        return False
    if line[-1] in ".!?…":
        return False
    return len(line.split()) <= 7


def split_quote(chunk: str) -> tuple[str, str | None]:
    """Separate a quote's body from its trailing attribution.

    Handles `quote — Author`, a quote then an `— Author` line, and a short
    plain trailing line that looks like a name. Returns (text, author|None).
    """
    text = chunk.strip()
    author: str | None = None

    dash = None
    for m in _Q_DASH_RE.finditer(text):
        dash = m
    if dash:
        after = text[dash.end():].strip()
        if after and "\n" not in after and len(after) <= 120:
            text = text[: dash.start()].rstrip()
            author = after

    if author is None:
        lines = text.splitlines()
        if len(lines) >= 2:
            last = lines[-1].strip()
            mh = re.match(r"^-{1,2}\s*(.+)$", last)
            if mh:
                author = mh.group(1).strip()
                text = "\n".join(lines[:-1])
            elif _looks_like_author(last):
                author = last
                text = "\n".join(lines[:-1])

    if author is None:
        m = re.match(r'^[“"\'](.+)[”"\']\s+([^\s].{0,58})$', text)
        if m and _looks_like_author(m.group(2)):
            text, author = m.group(1), m.group(2).strip()

    text = re.sub(r"\s*\n\s*", " ", text).strip()
    text = _strip_wrap_quotes(text)
    if author:
        author = author.strip(" —–-•").strip()
    return text, (author or None)


def render_quote_block(quote: str) -> str:
    """A calm card: gutter quote-mark, quote text, author below, swap button."""
    if not quote:
        return ""
    text, author = split_quote(quote)
    if not text:
        text = quote.strip()
    body = f'<blockquote class="quote-text">{html.escape(text)}</blockquote>'
    cap = (
        f'<figcaption class="quote-author">{html.escape(author)}</figcaption>'
        if author
        else ""
    )
    swap = (
        '<button class="quote-swap" type="button" aria-label="Show another quote" '
        'title="Another quote">'
        '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M2.5 8a5.5 5.5 0 0 1 9.4-3.9"/>'
        '<path d="M13.5 8a5.5 5.5 0 0 1-9.4 3.9"/>'
        '<path d="M11.9 1.6v2.6h-2.6"/>'
        '<path d="M4.1 14.4v-2.6h2.6"/>'
        "</svg></button>"
    )
    return f'<figure class="quote-block">{swap}{body}{cap}</figure>'


# ─── Dashboard: Now + Check-ins as cards ─────────────────────────────────────
# Each project (and each person under Check-ins) renders as a calm collapsible
# card with a muted count badge; tasks inside get a small round dot bullet.

# Which project card opens by default. Set to a project name in your Now list,
# or "" to start them all closed.
DEFAULT_OPEN_GROUP = "Project One"


def render_now_html(md: str) -> str:
    """Render every project under `## Now` as a collapsible card — project name
    + count badge on the left, opener on the right — with its tasks inside.
    The card named `DEFAULT_OPEN_GROUP` starts open; the rest start closed."""
    lines = md.splitlines()
    cur_h2: str | None = None
    cur_h3: str | None = None
    groups: list[tuple[str, list[tuple[str, str]]]] = []
    index: dict[str, int] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m2 = re.match(r"^##\s+(.+?)\s*$", line)
        if m2:
            cur_h2 = m2.group(1).strip()
            cur_h3 = None
            i += 1
            continue
        m3 = re.match(r"^###\s+(.+?)\s*$", line)
        if m3:
            cur_h3 = m3.group(1).strip()
            i += 1
            continue
        if cur_h2 == "Now" and line.startswith("- "):
            content = line[2:]
            while i + 1 < len(lines) and lines[i + 1].startswith("  "):
                content += " " + lines[i + 1].strip()
                i += 1
            cb = re.match(r"^\[([ xX])\]\s+(.*)$", content)
            if cb:
                proj = cur_h3 or "Other"
                if proj not in index:
                    index[proj] = len(groups)
                    groups.append((proj, []))
                groups[index[proj]][1].append((cb.group(1).lower(), cb.group(2)))
        i += 1

    if not groups:
        return '<p class="focus-empty">No tasks yet.</p>'

    plus = (
        '<svg class="chev" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" aria-hidden="true">'
        '<line x1="8" y1="3" x2="8" y2="13"/><line x1="3" y1="8" x2="13" y2="8"/></svg>'
    )
    blocks = []
    for proj, tasks in groups:
        lis = []
        for state, text in tasks:
            klass = "task task-done" if state == "x" else "task"
            lis.append(f'<li class="{klass}"><span class="task-text">{render_inline(text)}</span></li>')
        open_attr = " open" if proj == DEFAULT_OPEN_GROUP else ""
        badge = f'<span class="focus-count">{len(tasks)}</span>'
        blocks.append(
            f'<details class="focus-group"{open_attr}>'
            f'<summary><span class="focus-name">{html.escape(proj)}{badge}</span>{plus}</summary>'
            f'<ul class="focus-tasks">{"".join(lis)}</ul>'
            "</details>"
        )
    return '<div class="focus-groups">' + "\n".join(blocks) + "</div>"


def render_checkins_html(md: str) -> str:
    """Render the Check-ins section as focus-group cards, one per person, so it
    matches the Now list. Agenda items are plain bullets (no checkboxes)."""
    lines = md.splitlines()
    in_section = False
    cur_h3: str | None = None
    groups: list[tuple[str, list[str]]] = []
    index: dict[str, int] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m2 = re.match(r"^##\s+(.+?)\s*$", line)
        if m2:
            in_section = m2.group(1).strip() == "Check-ins"
            cur_h3 = None
            i += 1
            continue
        if not in_section:
            i += 1
            continue
        m3 = re.match(r"^###\s+(.+?)\s*$", line)
        if m3:
            cur_h3 = m3.group(1).strip()
            i += 1
            continue
        if cur_h3 and line.startswith("- "):
            content = line[2:]
            while i + 1 < len(lines) and lines[i + 1].startswith("  "):
                content += " " + lines[i + 1].strip()
                i += 1
            if cur_h3 not in index:
                index[cur_h3] = len(groups)
                groups.append((cur_h3, []))
            groups[index[cur_h3]][1].append(content)
        i += 1

    if not groups:
        return ""

    plus = (
        '<svg class="chev" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" aria-hidden="true">'
        '<line x1="8" y1="3" x2="8" y2="13"/><line x1="3" y1="8" x2="13" y2="8"/></svg>'
    )
    blocks = []
    for person, items in groups:
        lis = "".join(
            f'<li class="task"><span class="task-text">{render_inline(t)}</span></li>'
            for t in items
        )
        badge = f'<span class="focus-count">{len(items)}</span>'
        blocks.append(
            '<details class="focus-group" open>'
            f'<summary><span class="focus-name">{html.escape(person)}{badge}</span>{plus}</summary>'
            f'<ul class="focus-tasks">{lis}</ul>'
            "</details>"
        )
    return (
        '<div class="checkins-label">Check-ins</div>'
        '<div class="focus-groups">' + "\n".join(blocks) + "</div>"
    )


# ─── Birthdays this month ────────────────────────────────────────────────────
# Reads People notes for a `**Birthday:** Month Day` line. People notes live one
# level up from Suma, in `vault/People/`. For a self-contained demo (and so the
# starter shows something on first build) we also accept a `people/` folder next
# to build.py, including the kit's `sources/people/` staging copy.

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _people_dirs() -> list[Path]:
    return [
        VAULT / "People",          # installed layout: vault/People/
        SUMA / "people",           # optional folder next to build.py
        SUMA / "sources" / "people",  # kit staging copy (repo demo)
    ]


def scan_birthdays() -> list[tuple[int, int, str]]:
    """(month, day, name) for each People note with a `**Birthday:** Month Day` line."""
    out = []
    seen_names: set[str] = set()
    for people in _people_dirs():
        if not people.is_dir():
            continue
        for f in sorted(people.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            m = re.search(r"\*\*Birthday:\*\*\s*([A-Za-z]+)\s+(\d{1,2})", text, re.I)
            if not m:
                continue
            mon = _MONTHS.get(m.group(1)[:3].lower())
            if not mon:
                continue
            name = f.stem.replace("-", " ").title()
            if name in seen_names:
                continue
            seen_names.add(name)
            out.append((mon, int(m.group(2)), name))
    return out


def render_birthdays_html(today: _dt.date) -> str:
    """Birthdays falling in the current month, as a quiet name/date list.
    Hidden entirely when there are none this month."""
    month_bdays = sorted(
        (day, name) for (mon, day, name) in scan_birthdays() if mon == today.month
    )
    if not month_bdays:
        return ""
    rows = []
    for day, name in month_bdays:
        cls = "bday-row"
        if day == today.day:
            cls += " is-today"
            date_lbl = "Today"
        else:
            if day < today.day:
                cls += " is-past"
            date_lbl = f"{day} {today.strftime('%b')}"
        rows.append(
            f'<li class="{cls}">'
            f'<span class="bday-name">{html.escape(name)}</span>'
            f'<span class="bday-date">{html.escape(date_lbl)}</span>'
            "</li>"
        )
    return (
        '<div class="checkins-label">Birthdays this month</div>'
        '<ul class="bday-list">' + "".join(rows) + "</ul>"
    )


# ─── Builds scanner ─────────────────────────────────────────────────────────
# Walks ~/Desktop/code/*, reads .git/config for the remote, scans each
# project's README for live URLs. Passive read-out, no manual config required.

_BUILD_NUM_RE = re.compile(r"^(\d+)-(.+)$")
_GIT_URL_RE = re.compile(r"url\s*=\s*(.+)")
_HOST_LIVE_RE = re.compile(
    r"https?://[A-Za-z0-9.\-]+\.(?:here\.now|vercel\.app|netlify\.app|pages\.dev|fly\.dev)(?:/[^\s)>\]\[(\"'<]*)?"
)
_GENERIC_URL_RE = re.compile(
    r"https?://[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?:/[^\s)>\]\[(\"'<]*)?"
)
_LIVE_LINE_RE = re.compile(r"\b(?:live|deploy(?:ed)?|production|prod|domain|hosted)\b", re.I)

# Hosts/paths that are boilerplate (Next.js template, etc.), not real deploys.
_URL_BLOCKLIST = (
    "vercel.com/new",
    "vercel.com/templates",
    "github.com",
    "nextjs.org",
    "tailwindcss.com",
    "create-next-app",
)


def _normalize_git_remote(url: str) -> tuple[str, str]:
    """Return (display, href). Accepts SSH or HTTPS GitHub-style remotes."""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    m = re.match(r"git@([^:]+):(.+)$", url)
    if m:
        host, path = m.group(1), m.group(2)
        return f"{host}/{path}", f"https://{host}/{path}"
    m = re.match(r"https?://([^/]+)/(.+)$", url)
    if m:
        host, path = m.group(1), m.group(2)
        return f"{host}/{path}", f"https://{host}/{path}"
    return url, url


def _read_git_remote(folder: Path) -> tuple[str, str] | None:
    cfg = folder / ".git" / "config"
    if not cfg.exists():
        return None
    try:
        text = cfg.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    in_origin = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_origin = line == '[remote "origin"]'
            continue
        if in_origin:
            m = _GIT_URL_RE.match(line)
            if m:
                return _normalize_git_remote(m.group(1))
    return None


def _vercel_url(folder: Path) -> str | None:
    """If .vercel/project.json exists, derive the *.vercel.app URL."""
    cfg = folder / ".vercel" / "project.json"
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return None
    name = data.get("projectName")
    if not name:
        pkg = folder / "package.json"
        if pkg.exists():
            try:
                name = json.loads(pkg.read_text(encoding="utf-8", errors="ignore")).get("name")
            except (OSError, json.JSONDecodeError):
                name = None
    if not name:
        return None
    return f"https://{name}.vercel.app"


def _find_live_urls(folder: Path) -> list[str]:
    """Detect deploy URLs. README scan + Vercel project signal."""
    urls: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = u.rstrip(".,;:)]")
        low = u.lower()
        for bad in _URL_BLOCKLIST:
            if bad in low:
                return
        if u in seen:
            return
        seen.add(u)
        urls.append(u)

    vercel = _vercel_url(folder)
    if vercel:
        add(vercel)

    for name in ("README.md", "Readme.md", "readme.md"):
        f = folder / name
        if not f.exists():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Always pick up known deploy hosts wherever they appear.
        for m in _HOST_LIVE_RE.finditer(text):
            add(m.group(0))
        # Pick up custom domains only when the line is explicitly tagged live.
        for line in text.splitlines():
            if not _LIVE_LINE_RE.search(line):
                continue
            for m in _GENERIC_URL_RE.finditer(line):
                add(m.group(0))
        break  # one README is enough
    return urls


def _pretty_name(folder_name: str) -> str:
    m = _BUILD_NUM_RE.match(folder_name)
    base = m.group(2) if m else folder_name
    return base.replace("-", " ")


def scan_builds() -> list[dict]:
    if not CODE_ROOT.exists():
        return []
    builds = []
    for child in sorted(CODE_ROOT.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        if child.resolve() == SCRIPT_DIR:  # the Suma renderer folder itself — skip
            continue
        remote = _read_git_remote(child)
        live = _find_live_urls(child)
        m = _BUILD_NUM_RE.match(child.name)
        sort_key = (int(m.group(1)) if m else 9999, child.name)
        builds.append({
            "folder": child.name,
            "display": _pretty_name(child.name),
            "path": f"~/Desktop/code/{child.name}",
            "remote": remote,            # (display, href) or None
            "live": live,                # list[str]
            "sort_key": sort_key,
        })
    builds.sort(key=lambda b: b["sort_key"])
    return builds


def _short_url(url: str) -> str:
    return re.sub(r"^https?://", "", url).rstrip("/")


def render_builds_html(builds: list[dict]) -> str:
    if not builds:
        return "<p>No builds found in <code>~/Desktop/code/</code>.</p>"
    rows = []
    n_live = n_git = n_local = 0
    for b in builds:
        if b["live"]:
            n_live += 1
        if b["remote"]:
            n_git += 1
        if not b["live"] and not b["remote"]:
            n_local += 1

        bits = []
        bits.append(f'<strong>{html.escape(b["display"])}</strong>')

        chips = []
        if b["live"]:
            chips.append('<span class="build-tag build-tag-live">live</span>')
        if b["remote"]:
            chips.append('<span class="build-tag build-tag-git">git</span>')
        if not b["live"] and not b["remote"]:
            chips.append('<span class="build-tag build-tag-local">local</span>')
        if chips:
            bits.append(" ".join(chips))

        links = []
        if b["remote"]:
            disp, href = b["remote"]
            links.append(
                f'<a href="{html.escape(href)}" target="_blank" rel="noopener">'
                f'{html.escape(disp)}</a>'
            )
        for url in b["live"]:
            links.append(
                f'<a href="{html.escape(url)}" target="_blank" rel="noopener">'
                f'{html.escape(_short_url(url))}</a>'
            )
        if links:
            bits.append(
                '<span class="build-links">' + " · ".join(links) + "</span>"
            )
        bits.append(f'<code class="build-path">{html.escape(b["path"])}</code>')
        rows.append('<li class="build-row">' + "".join(bits) + "</li>")

    summary = (
        f'<p class="build-summary">'
        f'{len(builds)} builds · {n_live} live · {n_git} on git · '
        f'{n_local} local only'
        f'</p>'
    )
    return (
        '<h2 id="builds">' + dot_html("COOL") + "Builds</h2>"
        + summary
        + '<ul class="builds">' + "\n".join(rows) + "</ul>"
    )


def render_builds_md(builds: list[dict]) -> str:
    """Write a readable markdown mirror to vault/Suma/builds.md."""
    lines = [
        "# Builds",
        "",
        "_Auto-generated by `build.py`. Edits will be overwritten — change the source folders, README, or git config instead._",
        "",
    ]

    def fmt_row(b: dict) -> str:
        parts = [f'**{b["display"]}**']
        if b["live"]:
            for url in b["live"]:
                parts.append(f"live: [{_short_url(url)}]({url})")
        if b["remote"]:
            disp, href = b["remote"]
            parts.append(f"repo: [{disp}]({href})")
        else:
            parts.append("no git")
        parts.append(f"`{b['path']}`")
        return "- " + " — ".join(parts)

    live = [b for b in builds if b["live"]]
    git_only = [b for b in builds if not b["live"] and b["remote"]]
    local = [b for b in builds if not b["live"] and not b["remote"]]

    if live:
        lines.append("## Live")
        lines.append("")
        lines.extend(fmt_row(b) for b in live)
        lines.append("")
    if git_only:
        lines.append("## On git, not deployed")
        lines.append("")
        lines.extend(fmt_row(b) for b in git_only)
        lines.append("")
    if local:
        lines.append("## Local only")
        lines.append("")
        lines.extend(fmt_row(b) for b in local)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ─── Toolkit scanner ────────────────────────────────────────────────────────
# Surfaces the otherwise-invisible agent environment: configured MCP servers,
# installed skills, plugins, personal slash-commands, and CLIs. Read-only from
# ~/.claude.json, ~/.claude/, and brew/npm. Passive — installing a new skill or
# MCP server makes it show up on the next rebuild, no config. Safe to ship in a
# template: it scans whoever runs it, and shows a quiet empty state if the
# machine has none of these (e.g. someone not using a coding agent).

CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_JSON = Path.home() / ".claude.json"

# Curated one-liners for things that carry no on-disk description. Anything not
# listed still shows up (name + factual config) — the blurb is just nicer when
# we're confident. Generic, well-known tools only; extend for your own setup.
MCP_DESC = {
    "shadcn": "shadcn/ui component registry",
    "playwright": "Browser automation & testing",
    "github": "GitHub repos, issues and PRs",
}
PLUGIN_DESC: dict[str, str] = {}
CLI_DESC = {
    "claude": "Claude Code CLI",
    "gh": "GitHub CLI",
    "git": "Version control",
    "node": "Node.js runtime",
    "bun": "JS runtime & toolkit",
    "deno": "Secure JS/TS runtime",
    "pnpm": "Fast package manager",
    "yarn": "Package manager",
    "vercel": "Deploy & hosting CLI",
    "ffmpeg": "Audio & video processing",
    "poppler": "PDF rendering utilities",
    "go": "Go toolchain",
    "rustc": "Rust compiler",
    "cargo": "Rust package manager",
    "docker": "Containers",
    "jq": "JSON processor",
    "rg": "ripgrep — fast search",
    "fzf": "Fuzzy finder",
}


def _read_frontmatter(path: Path) -> dict:
    """Parse leading `--- ... ---` YAML-ish frontmatter into a flat dict.

    Tolerant of multi-line values and YAML block scalars (`|`, `>`).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    key = None
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            data[key] = "" if re.fullmatch(r"[|>][+\-]?\d*", val) else val.strip('"\'')
        elif key and line.strip():
            data[key] = (data[key] + " " + line.strip()).strip()
    return data


def _short_desc(text: str, limit: int = 130) -> str:
    """First sentence, or a clipped clause — keeps rows scannable."""
    text = " ".join((text or "").split())
    if not text:
        return ""
    m = re.match(r"^(.*?[.!?])(\s|$)", text)
    if m and len(m.group(1)) <= limit:
        return m.group(1)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _run(cmd: list[str], timeout: int = 12) -> list[str]:
    """Run a command, return non-empty stdout lines, or [] on any failure."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def _installed_plugins() -> list[dict]:
    f = CLAUDE_HOME / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for key, entries in (data.get("plugins") or {}).items():
        name, _, marketplace = key.partition("@")
        for e in entries or []:
            ip = e.get("installPath")
            if ip:
                out.append({
                    "name": name, "marketplace": marketplace,
                    "installPath": ip, "version": e.get("version", ""),
                })
    return out


def _mcp_transport(cfg: dict) -> str:
    return cfg.get("type") or ("http" if cfg.get("url") else "stdio")


def scan_mcp_servers() -> list[dict]:
    try:
        data = json.loads(CLAUDE_JSON.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return []
    servers: dict[str, dict] = {}
    for name, cfg in (data.get("mcpServers") or {}).items():
        servers[name] = {
            "name": name, "scope": "global", "transport": _mcp_transport(cfg),
            "command": cfg.get("command", ""), "projects": [],
        }
    for ppath, pcfg in (data.get("projects") or {}).items():
        label = Path(ppath).name or ppath
        for name, cfg in (pcfg.get("mcpServers") or {}).items():
            if name in servers:
                s = servers[name]
                if s["scope"] != "global" and label not in s["projects"]:
                    s["projects"].append(label)
            else:
                servers[name] = {
                    "name": name, "scope": "project", "transport": _mcp_transport(cfg),
                    "command": cfg.get("command", ""), "projects": [label],
                }
    return sorted(
        servers.values(),
        key=lambda s: (0 if s["scope"] == "global" else 1, s["name"].lower()),
    )


def scan_skills() -> list[dict]:
    out = []
    sk_dir = CLAUDE_HOME / "skills"
    if sk_dir.is_dir():
        for child in sorted(sk_dir.iterdir()):
            f = child / "SKILL.md"
            if f.is_file():
                fm = _read_frontmatter(f)
                out.append({
                    "name": fm.get("name", child.name),
                    "desc": _short_desc(fm.get("description", "")),
                    "source": "personal",
                })
    for plug in _installed_plugins():
        skills_dir = Path(plug["installPath"]) / "skills"
        if not skills_dir.is_dir():
            continue
        for child in sorted(skills_dir.iterdir()):
            f = child / "SKILL.md"
            if f.is_file():
                fm = _read_frontmatter(f)
                out.append({
                    "name": fm.get("name", child.name),
                    "desc": _short_desc(fm.get("description", "")),
                    "source": "plugin",
                })
    return out


def scan_plugins() -> list[dict]:
    out = []
    for p in _installed_plugins():
        desc = PLUGIN_DESC.get(p["name"], "")
        for cand in (
            Path(p["installPath"]) / ".claude-plugin" / "plugin.json",
            Path(p["installPath"]) / "plugin.json",
        ):
            if cand.is_file():
                try:
                    pj = json.loads(cand.read_text(encoding="utf-8", errors="ignore"))
                    desc = pj.get("description") or desc
                except (OSError, json.JSONDecodeError):
                    pass
                break
        out.append({**p, "desc": _short_desc(desc)})
    return sorted(out, key=lambda p: p["name"].lower())


def scan_commands() -> list[dict]:
    out = []
    cmd_dir = CLAUDE_HOME / "commands"
    if cmd_dir.is_dir():
        for f in sorted(cmd_dir.glob("*.md")):
            fm = _read_frontmatter(f)
            desc = fm.get("description", "")
            if not desc:
                for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                    s = line.strip()
                    if s and not s.startswith(("#", "---")):
                        desc = s
                        break
            out.append({"name": f.stem, "desc": _short_desc(desc), "source": "personal"})
    for plug in _installed_plugins():
        cdir = Path(plug["installPath"]) / "commands"
        if not cdir.is_dir():
            continue
        for f in sorted(cdir.glob("*.md")):
            fm = _read_frontmatter(f)
            out.append({
                "name": f"{plug['name']}:{f.stem}",
                "desc": _short_desc(fm.get("description", "")),
                "source": "plugin",
            })
    return out


def _npm_globals() -> list[str]:
    skip = {"npm", "corepack", "npx"}
    candidates = [
        Path("/opt/homebrew/lib/node_modules"),
        Path("/usr/local/lib/node_modules"),
        Path.home() / ".npm-global" / "lib" / "node_modules",
    ]
    for d in candidates:
        if not d.is_dir():
            continue
        pkgs = []
        for entry in sorted(d.iterdir()):
            nm = entry.name
            if nm.startswith("."):
                continue
            if nm.startswith("@"):
                for sub in sorted(entry.iterdir()):
                    if sub.is_dir() and not sub.name.startswith("."):
                        pkgs.append(f"{nm}/{sub.name}")
            elif nm not in skip:
                pkgs.append(nm)
        return pkgs
    return []


def scan_clis() -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    order = {"brew": 0, "cask": 1, "npm": 2, "local": 3}

    def add(name: str, source: str) -> None:
        key = name.lower()
        if key in seen:
            return
        seen.add(key)
        out.append({"name": name, "source": source, "desc": CLI_DESC.get(name, "")})

    for f in _run(["brew", "leaves"]):
        add(f.split("/")[-1], "brew")          # strip tap prefix (oven-sh/bun/bun)
    for c in _run(["brew", "list", "--cask"]):
        add(c, "cask")
    for pkg in _npm_globals():
        add(pkg, "npm")
    if shutil.which("claude"):
        add("claude", "local")

    out.sort(key=lambda c: (order.get(c["source"], 9), c["name"].lower()))
    return out


def scan_toolkit() -> dict:
    return {
        "mcp": scan_mcp_servers(),
        "skills": scan_skills(),
        "plugins": scan_plugins(),
        "commands": scan_commands(),
        "clis": scan_clis(),
    }


# ─── Toolkit renderer ───────────────────────────────────────────────────────

def _kit_tag(label: str) -> str:
    return f'<span class="build-tag">{html.escape(label)}</span>'


def _kit_row(name: str, tags: list[str], desc: str = "", detail: str = "") -> str:
    head = (
        '<div class="kit-head">'
        f'<strong>{html.escape(name)}</strong>'
        + "".join(_kit_tag(t) for t in tags if t)
        + "</div>"
    )
    body = f'<div class="kit-desc">{html.escape(desc)}</div>' if desc else ""
    foot = f'<code class="kit-detail">{html.escape(detail)}</code>' if detail else ""
    return f'<li class="kit-row">{head}{body}{foot}</li>'


def render_toolkit_html(kit: dict) -> tuple[str, str]:
    """Return (toc_html, body_html). Empty sections are skipped; an all-empty
    toolkit (e.g. no coding-agent setup on this machine) shows a quiet note."""
    sections: list[tuple[str, str, str, str, str]] = []  # title, anchor, color, summary, rows

    mcp = kit["mcp"]
    if mcp:
        n_global = sum(1 for s in mcp if s["scope"] == "global")
        rows = "".join(
            _kit_row(s["name"], [s["scope"], s["transport"]],
                     MCP_DESC.get(s["name"], ""), s["command"])
            for s in mcp
        )
        summary = f'{len(mcp)} servers · {n_global} global · {len(mcp) - n_global} project'
        sections.append(("MCP servers", "mcp-servers", "COOL", summary, rows))

    skills = kit["skills"]
    if skills:
        n_pers = sum(1 for s in skills if s["source"] == "personal")
        rows = "".join(_kit_row(s["name"], [s["source"]], s["desc"]) for s in skills)
        summary = f'{len(skills)} skills · {n_pers} personal'
        if len(skills) - n_pers:
            summary += f' · {len(skills) - n_pers} from plugins'
        sections.append(("Skills", "skills", "VIBRANT", summary, rows))

    plugins = kit["plugins"]
    if plugins:
        rows = "".join(
            _kit_row(p["name"],
                     [f'v{p["version"]}' if p["version"] else "", p.get("marketplace", "")],
                     p["desc"])
            for p in plugins
        )
        sections.append(("Plugins", "plugins", "TWILIGHT", f'{len(plugins)} installed', rows))

    commands = kit["commands"]
    if commands:
        rows = "".join(_kit_row(f'/{c["name"]}', [c["source"]], c["desc"]) for c in commands)
        sections.append(("Commands", "commands", "SUNSET", f'{len(commands)} commands', rows))

    clis = kit["clis"]
    if clis:
        counts: dict[str, int] = {}
        for c in clis:
            counts[c["source"]] = counts.get(c["source"], 0) + 1
        rows = "".join(_kit_row(c["name"], [c["source"]], c["desc"]) for c in clis)
        bits = " · ".join(f'{n} {src}' for src, n in counts.items())
        sections.append(("CLIs", "clis", "FOREST", f'{len(clis)} CLIs · {bits}', rows))

    intro = (
        '<p class="kit-intro">Everything wired into your coding agent on this '
        'machine — scanned fresh on each rebuild.</p>'
    )
    if not sections:
        return "", intro + (
            '<p class="kit-empty">Nothing detected yet. This tab fills in once you '
            'have MCP servers, skills or CLIs installed (e.g. via Claude Code or '
            'Homebrew).</p>'
        )

    toc = "\n".join(
        f'<a href="#{anchor}">{dot_html(color)}{html.escape(title)}</a>'
        for title, anchor, color, _, _ in sections
    )
    body = intro + "\n".join(
        f'<h2 id="{anchor}">{dot_html(color)}{html.escape(title)}</h2>'
        f'<p class="build-summary">{html.escape(summary)}</p>'
        f'<ul class="kit">{rows}</ul>'
        for title, anchor, color, summary, rows in sections
    )
    return toc, body


def render_toolkit_md(kit: dict) -> str:
    lines = [
        "# Toolkit",
        "",
        "_Auto-generated by `build.py`. Edits will be overwritten — install or "
        "remove the actual MCP server, skill, plugin, command or CLI instead._",
        "",
    ]

    def section(title: str, items: list[str]) -> None:
        if not items:
            return
        lines.append(f"## {title}")
        lines.append("")
        lines.extend(items)
        lines.append("")

    section("MCP servers", [
        "- **{name}** — {scope} · {transport}{cmd}{desc}".format(
            name=s["name"], scope=s["scope"], transport=s["transport"],
            cmd=f' · `{s["command"]}`' if s["command"] else "",
            desc=f' — {MCP_DESC[s["name"]]}' if s["name"] in MCP_DESC else "",
        ) for s in kit["mcp"]
    ])
    section("Skills", [
        "- **{name}** ({source}){desc}".format(
            name=s["name"], source=s["source"],
            desc=f' — {s["desc"]}' if s["desc"] else "",
        ) for s in kit["skills"]
    ])
    section("Plugins", [
        "- **{name}** v{ver} ({mkt}){desc}".format(
            name=p["name"], ver=p["version"], mkt=p["marketplace"],
            desc=f' — {p["desc"]}' if p["desc"] else "",
        ) for p in kit["plugins"]
    ])
    section("Commands", [
        "- **/{name}** ({source}){desc}".format(
            name=c["name"], source=c["source"],
            desc=f' — {c["desc"]}' if c["desc"] else "",
        ) for c in kit["commands"]
    ])
    section("CLIs", [
        "- **{name}** ({source}){desc}".format(
            name=c["name"], source=c["source"],
            desc=f' — {c["desc"]}' if c["desc"] else "",
        ) for c in kit["clis"]
    ])
    return "\n".join(lines).rstrip() + "\n"


# ─── Activity heatmap ───────────────────────────────────────────────────────
# Contribution-graph view of changelog activity. For each dated entry we count
# the project paragraphs and completed-task bullets; the grid shades by volume.
# Monochrome ink ramp, not the GitHub blue — stays inside Suma's calm palette.

_ACT_DATE_RE = re.compile(r"^##\s+(\d{4})-(\d{2})-(\d{2})\b")
_ACT_PARA_RE = re.compile(r"^\*\*[^*]+\*\*\s+—")
_ACT_DONE_RE = re.compile(r"^-\s+\*\*[^*]+\*\*\s+done:")


def scan_activity(md: str) -> dict[_dt.date, int]:
    """Map each changelog date → number of things that happened that day."""
    counts: dict[_dt.date, int] = {}
    cur: _dt.date | None = None
    for line in md.splitlines():
        m = _ACT_DATE_RE.match(line)
        if m:
            try:
                cur = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                cur = None
            if cur is not None and cur not in counts:
                counts[cur] = 0
            continue
        if cur is None:
            continue
        # Count plain changelog bullets too, so a normal entry registers.
        if line.startswith("- ") or _ACT_PARA_RE.match(line) or _ACT_DONE_RE.match(line):
            counts[cur] += 1
    # A dated entry always means *something* happened, even if unparsed.
    for d in list(counts):
        if counts[d] == 0:
            counts[d] = 1
    return counts


def _act_level(n: int) -> int:
    if n <= 0:
        return 0
    if n == 1:
        return 1
    if n == 2:
        return 2
    if n <= 4:
        return 3
    return 4


def activity_stats(counts: dict[_dt.date, int], today: _dt.date) -> dict:
    days = sorted(counts)
    busiest = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
    longest = run = 1
    for prev, d in zip(days, days[1:]):
        run = run + 1 if (d - prev).days == 1 else 1
        longest = max(longest, run)
    current = 0
    probe = today
    while probe in counts:
        current += 1
        probe -= _dt.timedelta(days=1)
    return {
        "active_days": len(days),
        "busiest_date": busiest[0],
        "busiest_n": busiest[1],
        "longest": longest,
        "current": current,
        "first": days[0],
        "last": days[-1],
    }


def render_activity_html(counts: dict[_dt.date, int], today: _dt.date) -> str:
    if not counts:
        return ""
    s = activity_stats(counts, today)

    cap_start = today - _dt.timedelta(weeks=52)
    start = max(s["first"], cap_start)
    start -= _dt.timedelta(days=(start.weekday() + 1) % 7)        # back to Sunday
    end = today + _dt.timedelta(days=(5 - today.weekday()) % 7)    # forward to Saturday

    weeks: list[list[_dt.date]] = []
    d = start
    while d <= end:
        weeks.append([d + _dt.timedelta(days=k) for k in range(7)])
        d += _dt.timedelta(days=7)

    cells: list[str] = []
    for week in weeks:
        for day in week:
            n = counts.get(day, 0)
            if day > today:
                title = day.isoformat()
            elif n:
                title = f'{day.isoformat()} · {n} update' + ("" if n == 1 else "s")
            else:
                title = day.isoformat()
            cells.append(
                f'<span class="act-cell act-l{_act_level(n)}" '
                f'title="{html.escape(title)}"></span>'
            )

    months: list[str] = []
    prev_mon = None
    for week in weeks:
        mon = week[0].month
        label = week[0].strftime("%b") if mon != prev_mon else ""
        months.append(f'<span class="act-mon">{label}</span>')
        prev_mon = mon

    b = s["busiest_date"]
    meta = (
        f'{s["active_days"]} active days · current streak {s["current"]} · '
        f'longest {s["longest"]} · busiest {b.day} {b.strftime("%b")} '
        f'({s["busiest_n"]})'
    )
    return (
        '<section class="act-widget" aria-label="Activity">'
        '<div class="act-widget-label">Activity</div>'
        '<div class="act-scroll">'
        '<div class="act-months">' + "".join(months) + "</div>"
        '<div class="act-grid">' + "".join(cells) + "</div>"
        "</div>"
        f'<div class="act-widget-meta">{html.escape(meta)}</div>'
        "</section>"
    )


def favicon_data_uri() -> str:
    """A generic Suma mark — a vibrant gradient dot on a rounded near-black tile,
    as an inline SVG data URI. Matches the section-dot identity; no asset file."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#b8ff45"/>'
        '<stop offset="0.35" stop-color="#ffcb45"/>'
        '<stop offset="1" stop-color="#ff00b8"/>'
        "</linearGradient></defs>"
        '<rect width="100" height="100" rx="22" fill="#0b0b0b"/>'
        '<circle cx="50" cy="50" r="22" fill="url(#g)"/>'
        "</svg>"
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return "data:image/svg+xml;base64," + b64


HTML_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Suma</title>
<link rel="icon" type="image/svg+xml" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    /* Endlesstools palette — inverted for light mode.
       Token names preserved (semantic role unchanged), values flipped:
       primary surface stays "the page bg", primary text stays "the readable
       text on it", just swapped between near-black and near-white. */
    --color-midnight-ink:    #f7f7f7;  /* page + card bg */
    --color-stormy-night:    #ececec;  /* subtle surface (tags, code) */
    --color-deep-shadow:     #d8d8d8;  /* inactive buttons, inset borders */
    --color-charcoal-border: #afafaf;  /* stronger borders */
    --color-ash-gray:        #6a6a6a;  /* secondary text */
    --color-cloud-white:     #000000;  /* primary text + filled CTA */
    --color-electric-blue:   #1d9bf0;  /* unchanged — works on both modes */
    --gradient-vibrant: linear-gradient(97.25deg,
      rgb(184, 255, 69) 3%,
      rgb(255, 203, 69) 22%,
      rgb(255, 0, 184) 100%);
    --gradient-cool: linear-gradient(97.25deg,
      rgb(92, 225, 230) 3%,
      rgb(29, 155, 240) 22%,
      rgb(124, 58, 237) 100%);
    --gradient-sunset: linear-gradient(97.25deg,
      rgb(255, 180, 200) 3%,
      rgb(255, 140, 80) 22%,
      rgb(255, 210, 80) 100%);
    --gradient-warm: linear-gradient(97.25deg,
      rgb(255, 165, 120) 3%,
      rgb(255, 100, 100) 22%,
      rgb(220, 80, 140) 100%);
    --gradient-forest: linear-gradient(97.25deg,
      rgb(180, 240, 200) 3%,
      rgb(80, 200, 140) 22%,
      rgb(40, 140, 140) 100%);
    --gradient-twilight: linear-gradient(97.25deg,
      rgb(150, 130, 255) 3%,
      rgb(120, 80, 200) 22%,
      rgb(220, 80, 200) 100%);
    --gradient-sand: linear-gradient(97.25deg,
      rgb(245, 225, 180) 3%,
      rgb(220, 180, 130) 22%,
      rgb(180, 130, 90) 100%);
    --gradient-mist: linear-gradient(97.25deg,
      rgb(200, 220, 230) 3%,
      rgb(150, 180, 210) 22%,
      rgb(120, 140, 180) 100%);

    --inset-subtle:   rgb(216, 216, 216) 0px 0px 0px 1px inset;
    --inset-stronger: rgb(175, 175, 175) 0px 0px 0px 1px inset;

    --font-body: 'Inter', ui-sans-serif, system-ui, -apple-system,
                 BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-mono: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;

    color-scheme: light;
  }}

  /* Night mode — original Endlesstools dark palette. Same semantic
     roles, values un-inverted: near-black surfaces, near-white text. */
  :root[data-theme="dark"] {{
    --color-midnight-ink:    #080808;
    --color-stormy-night:    #1a1a1a;
    --color-deep-shadow:     #2a2a2a;
    --color-charcoal-border: #4a4a4a;
    --color-ash-gray:        #8a8a8a;
    --color-cloud-white:     #f7f7f7;
    --inset-subtle:   rgb(42, 42, 42) 0px 0px 0px 1px inset;
    --inset-stronger: rgb(74, 74, 74) 0px 0px 0px 1px inset;
    color-scheme: dark;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0;
    background: var(--color-midnight-ink);
    color: var(--color-cloud-white);
  }}
  body {{
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 1.25;
    letter-spacing: -0.35px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}
  .wrap {{
    max-width: 920px;
    margin: 0 auto;
    padding: 60px 32px 140px;
  }}

  /* ─── Header ─── */
  header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 28px;
  }}
  header h1 {{
    font-family: var(--font-body);
    font-size: 42px;
    font-weight: 500;
    letter-spacing: -1.05px;
    line-height: 1.08;
    margin: 0;
    color: var(--color-cloud-white);
  }}
  header h1 a {{
    color: inherit;
    text-decoration: none;
    border-bottom: 0;
    cursor: pointer;
  }}
  header h1 a:hover {{ border-bottom: 0; }}
  header .meta {{
    font-family: var(--font-mono);
    font-weight: 400;
    font-size: 12px;
    color: var(--color-ash-gray);
    letter-spacing: 0;
    white-space: nowrap;
  }}
  header .header-right {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}

  /* ─── Theme toggle ─── */
  .theme-toggle {{
    appearance: none;
    cursor: pointer;
    background: transparent;
    color: var(--color-ash-gray);
    border: 0;
    width: 30px;
    height: 30px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    box-shadow: var(--inset-subtle);
    transition: color 120ms ease, box-shadow 120ms ease;
  }}
  .theme-toggle:hover {{
    color: var(--color-cloud-white);
    box-shadow: var(--inset-stronger);
  }}
  .theme-toggle svg {{ width: 15px; height: 15px; display: block; }}
  .theme-toggle .icon-sun {{ display: none; }}
  :root[data-theme="dark"] .theme-toggle .icon-moon {{ display: none; }}
  :root[data-theme="dark"] .theme-toggle .icon-sun {{ display: block; }}

  /* ─── Tabs ─── */
  nav.tabs {{
    display: flex;
    gap: 8px;
    margin: 0 0 40px;
  }}
  nav.tabs button {{
    appearance: none;
    cursor: pointer;
    background: var(--color-deep-shadow);
    color: var(--color-cloud-white);
    font-family: var(--font-body);
    font-weight: 500;
    font-size: 14px;
    letter-spacing: -0.35px;
    line-height: 1;
    padding: 10px 20px;
    border: 0;
    border-radius: 10px;
    box-shadow: var(--inset-subtle);
    transition: background 120ms ease, color 120ms ease, box-shadow 120ms ease;
  }}
  nav.tabs button:hover {{
    box-shadow: var(--inset-stronger);
  }}
  nav.tabs button.active {{
    background: var(--color-cloud-white);
    color: var(--color-midnight-ink);
    box-shadow: none;
  }}

  .view[hidden] {{ display: none; }}

  /* ─── TOC pill nav ─── */
  nav.toc {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin: 0 0 40px;
  }}
  nav.toc a {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--color-stormy-night);
    color: var(--color-ash-gray);
    text-decoration: none;
    border: 0;
    font-family: var(--font-body);
    font-weight: 400;
    font-size: 12px;
    line-height: 1;
    padding: 8px 15px;
    border-radius: 7px;
    box-shadow: var(--inset-subtle);
    transition: color 120ms ease, box-shadow 120ms ease;
  }}
  nav.toc a:hover {{
    color: var(--color-cloud-white);
    box-shadow: var(--inset-stronger);
  }}
  nav.toc a .dot {{
    width: 6px; height: 6px; border-radius: 50%;
    display: inline-block;
    flex: none;
  }}

  /* ─── Section headings ─── */
  h2 {{
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: var(--font-body);
    font-size: 24px;
    font-weight: 500;
    letter-spacing: -0.6px;
    line-height: 1.11;
    margin: 56px 0 20px;
    color: var(--color-cloud-white);
  }}
  h2 .dot {{
    width: 10px; height: 10px;
    border-radius: 50%;
    display: inline-block;
    flex: none;
  }}
  .dot-vibrant {{
    background: var(--gradient-vibrant);
    box-shadow: 0 0 6px rgba(255, 0, 184, 0.20);
  }}
  .dot-cool {{
    background: var(--gradient-cool);
    box-shadow: 0 0 6px rgba(124, 58, 237, 0.20);
  }}
  .dot-sunset {{
    background: var(--gradient-sunset);
    box-shadow: 0 0 6px rgba(255, 140, 80, 0.20);
  }}
  .dot-warm {{
    background: var(--gradient-warm);
    box-shadow: 0 0 6px rgba(220, 80, 140, 0.20);
  }}
  .dot-forest {{
    background: var(--gradient-forest);
    box-shadow: 0 0 6px rgba(40, 140, 140, 0.20);
  }}
  .dot-twilight {{
    background: var(--gradient-twilight);
    box-shadow: 0 0 6px rgba(150, 130, 255, 0.20);
  }}
  .dot-sand {{
    background: var(--gradient-sand);
    box-shadow: 0 0 6px rgba(180, 130, 90, 0.20);
  }}
  .dot-mist {{
    background: var(--gradient-mist);
    box-shadow: 0 0 6px rgba(120, 140, 180, 0.20);
  }}
  h2.date {{
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 400;
    letter-spacing: 0;
    color: var(--color-ash-gray);
    margin: 40px 0 12px;
    text-transform: none;
  }}
  .view > main > h2.date:first-child {{ margin-top: 0; }}

  h3 {{
    font-family: var(--font-body);
    font-weight: 500;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--color-ash-gray);
    margin: 28px 0 8px;
  }}

  /* ─── Body type ─── */
  p {{
    margin: 12px 0;
    color: var(--color-ash-gray);
    font-size: 14px;
    line-height: 1.5;
  }}

  /* ─── Lists ─── */
  ul {{
    list-style: none;
    padding: 0;
    margin: 0;
  }}
  li {{
    padding: 12px 0;
    border-bottom: 1px solid var(--color-stormy-night);
    color: var(--color-ash-gray);
    font-size: 14px;
    line-height: 1.5;
  }}
  li:last-child {{ border-bottom: none; }}
  li strong {{ color: var(--color-cloud-white); font-weight: 500; }}
  li a {{
    color: var(--color-cloud-white);
    font-weight: 500;
    text-decoration: none;
    border-bottom: 0;
  }}
  li a:hover {{ color: var(--color-electric-blue); }}

  a {{
    color: var(--color-electric-blue);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 120ms ease;
  }}
  a:hover {{ border-bottom-color: var(--color-electric-blue); }}

  strong {{ color: var(--color-cloud-white); font-weight: 500; }}
  em {{ font-style: italic; color: var(--color-ash-gray); }}

  code {{
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--color-cloud-white);
    background: var(--color-stormy-night);
    padding: 1px 6px;
    border-radius: 7px;
    box-shadow: var(--inset-subtle);
  }}

  /* ─── Tasks card — any ul containing task rows ─── */
  ul:has(> li.task) {{
    background: var(--color-midnight-ink);
    border-radius: 10px;
    box-shadow: var(--inset-subtle);
    padding: 0 15px;
    margin: 0 0 18px;
  }}
  ul:has(> li.task) li {{
    border-bottom: 1px solid var(--color-stormy-night);
    padding: 12px 0;
  }}
  ul:has(> li.task) li:last-child {{ border-bottom: none; }}
  h3 + ul:has(> li.task) {{ margin-top: 0; }}

  li.task {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }}
  li.task .check {{
    flex: none;
    width: 16px;
    height: 16px;
    border-radius: 4px;
    box-shadow: var(--inset-stronger);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    line-height: 1;
    color: var(--color-cloud-white);
    margin-top: 3px;
    background: transparent;
  }}
  li.task-done .check {{
    background: var(--color-cloud-white);
    color: var(--color-midnight-ink);
    box-shadow: none;
  }}
  li.task .task-text {{ flex: 1; }}
  li.task-done .task-text {{
    text-decoration: line-through;
    color: var(--color-ash-gray);
  }}
  li.task-done .task-text strong {{
    color: var(--color-ash-gray);
    font-weight: 500;
  }}

  /* ─── Builds tab ─── */
  .build-summary {{
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-ash-gray);
    margin: 0 0 24px;
  }}
  ul.builds {{ margin: 0; padding: 0; }}
  ul.builds li.build-row {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    padding: 14px 0;
  }}
  ul.builds li.build-row strong {{ flex: 0 0 auto; }}
  ul.builds .build-links {{
    color: var(--color-ash-gray);
    font-size: 13px;
  }}
  ul.builds .build-links a {{
    color: var(--color-cloud-white);
    border-bottom: 0;
    text-decoration: none;
  }}
  ul.builds .build-links a:hover {{ color: var(--color-electric-blue); }}
  ul.builds .build-path {{
    margin-left: auto;
    font-size: 11px;
    background: transparent;
    box-shadow: none;
    padding: 0;
    color: var(--color-ash-gray);
  }}
  .build-tag {{
    display: inline-block;
    font-family: var(--font-mono);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    padding: 2px 7px;
    border-radius: 6px;
    box-shadow: var(--inset-subtle);
    color: var(--color-ash-gray);
    background: var(--color-stormy-night);
  }}
  .build-tag-live {{
    color: var(--color-midnight-ink);
    background: var(--gradient-forest);
    box-shadow: none;
  }}
  .build-tag-git {{
    color: var(--color-midnight-ink);
    background: var(--color-cloud-white);
    box-shadow: none;
  }}
  .build-tag-local {{
    color: var(--color-ash-gray);
    background: var(--color-stormy-night);
  }}
  @media (max-width: 720px) {{
    ul.builds .build-path {{ margin-left: 0; flex-basis: 100%; }}
  }}

  /* ─── Toolkit tab ─── */
  .kit-intro {{
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-ash-gray);
    margin: 0 0 8px;
    max-width: 620px;
    line-height: 1.5;
  }}
  .kit-intro + h2 {{ margin-top: 36px; }}
  .kit-empty {{ color: var(--color-ash-gray); font-size: 14px; line-height: 1.5; max-width: 560px; }}
  ul.kit {{ margin: 0; padding: 0; }}
  ul.kit li.kit-row {{
    display: block;
    padding: 13px 0;
    border-bottom: 1px solid var(--color-stormy-night);
  }}
  ul.kit li.kit-row:last-child {{ border-bottom: none; }}
  .kit-head {{
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 9px;
  }}
  .kit-head strong {{ color: var(--color-cloud-white); font-weight: 500; }}
  .kit-desc {{
    color: var(--color-ash-gray);
    font-size: 13px;
    line-height: 1.45;
    margin-top: 3px;
  }}
  .kit-detail {{
    display: inline-block;
    margin-top: 5px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--color-ash-gray);
    background: transparent;
    box-shadow: none;
    padding: 0;
  }}

  /* ─── Dashboard cards: Now + Check-ins ─── */
  .focus-groups {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin: 0;
  }}
  .checkins-label {{
    margin: 28px 0 12px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.45px;
    text-transform: uppercase;
    color: var(--color-ash-gray);
  }}
  .focus-group {{
    background: var(--color-stormy-night);
    border-radius: 14px;
    padding: 4px 22px;
  }}
  .focus-group > summary {{
    list-style: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 0;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 500;
    color: var(--color-cloud-white);
  }}
  .focus-group > summary::-webkit-details-marker {{ display: none; }}
  .focus-group .chev {{
    width: 15px;
    height: 15px;
    flex: none;
    color: var(--color-ash-gray);
    transition: transform 180ms ease;
  }}
  .focus-group[open] > summary .chev {{ transform: rotate(45deg); }}
  .focus-group[open] > summary {{
    border-bottom: 1px solid var(--color-deep-shadow);
    margin-bottom: 8px;
  }}
  .focus-group .focus-name {{ flex: 1; }}
  .focus-count {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    margin-left: 9px;
    border-radius: 9px;
    background: var(--color-deep-shadow);
    color: var(--color-ash-gray);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    line-height: 1;
    vertical-align: middle;
  }}
  .focus-group .focus-tasks {{
    background: transparent;
    box-shadow: none;
    border-radius: 0;
    padding: 0;
    margin: 0 0 6px;
  }}
  .focus-group .focus-tasks li {{
    padding: 10px 0;
    border-bottom: 1px solid var(--color-deep-shadow);
  }}
  .focus-group .focus-tasks li:first-child {{ padding-top: 2px; }}
  .focus-group .focus-tasks li:last-child {{ border-bottom: none; }}
  .focus-group .focus-tasks li.task {{ gap: 10px; }}
  .focus-group .focus-tasks li.task::before {{
    content: "";
    flex: none;
    width: 5px;
    height: 5px;
    margin-top: 8px;
    border-radius: 50%;
    background: var(--color-ash-gray);
  }}
  .focus-group .focus-tasks li.task-done::before {{ opacity: 0.45; }}
  .focus-empty {{
    color: var(--color-ash-gray);
    font-size: 14px;
    line-height: 1.6;
  }}

  /* ─── Birthdays this month ─── */
  .bday-list {{
    background: var(--color-stormy-night);
    border-radius: 14px;
    padding: 2px 22px;
    margin: 0;
  }}
  .bday-row {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid var(--color-deep-shadow);
  }}
  .bday-row:last-child {{ border-bottom: none; }}
  .bday-name {{ color: var(--color-cloud-white); font-size: 14px; }}
  .bday-date {{
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-ash-gray);
    white-space: nowrap;
  }}
  .bday-row.is-past .bday-name {{ color: var(--color-ash-gray); }}
  .bday-row.is-today .bday-name {{ font-weight: 500; }}
  .bday-row.is-today .bday-date {{ color: var(--color-electric-blue); }}

  /* ─── Daily quote ─── */
  .quote-block {{
    position: relative;
    margin: 0 0 16px;
    padding: 26px 30px 26px 58px;
    background: var(--color-stormy-night);
    border-radius: 18px;
  }}
  .quote-block::before {{
    content: "“";
    position: absolute;
    top: 16px;
    left: 24px;
    font-size: 40px;
    line-height: 1;
    color: var(--color-ash-gray);
    opacity: 0.55;
    pointer-events: none;
  }}
  .quote-text {{
    position: relative;
    margin: 0;
    color: var(--color-cloud-white);
    font-size: 16px;
    line-height: 1.65;
    letter-spacing: -0.2px;
  }}
  .quote-author {{
    margin-top: 14px;
    font-size: 13px;
    color: var(--color-ash-gray);
  }}
  .quote-swap {{
    position: absolute;
    top: 14px;
    right: 16px;
    appearance: none;
    cursor: pointer;
    background: transparent;
    border: 0;
    padding: 4px;
    line-height: 0;
    border-radius: 7px;
    color: var(--color-ash-gray);
    opacity: 0.55;
    transition: opacity 120ms ease, color 120ms ease, transform 200ms ease;
  }}
  .quote-swap:hover {{ opacity: 1; color: var(--color-cloud-white); }}
  .quote-swap:active {{ transform: rotate(-90deg); }}
  .quote-swap svg {{ width: 14px; height: 14px; display: block; }}

  /* ─── Activity heatmap (Dashboard widget) ─── */
  .act-widget {{
    background: var(--color-midnight-ink);
    border-radius: 18px;
    box-shadow: var(--inset-subtle);
    padding: 20px 24px 18px;
    margin: 0 0 22px;
  }}
  .act-widget-label {{
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.45px;
    text-transform: uppercase;
    color: var(--color-ash-gray);
    margin-bottom: 14px;
  }}
  .act-widget-meta {{
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.2px;
    color: var(--color-ash-gray);
    margin-top: 14px;
  }}
  .act-scroll {{
    overflow-x: auto;
    padding-bottom: 4px;
  }}
  .act-months {{
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: 13px;
    gap: 4px;
    margin-bottom: 7px;
  }}
  .act-mon {{
    font-family: var(--font-mono);
    font-size: 10px;
    line-height: 1;
    color: var(--color-ash-gray);
    white-space: nowrap;
    overflow: visible;
  }}
  .act-grid {{
    display: grid;
    grid-template-rows: repeat(7, 13px);
    grid-auto-flow: column;
    grid-auto-columns: 13px;
    gap: 4px;
    width: max-content;
  }}
  .act-cell {{
    width: 13px;
    height: 13px;
    border-radius: 3px;
    background: var(--color-stormy-night);
    box-shadow: var(--inset-subtle);
  }}
  .act-l1 {{ background: color-mix(in srgb, var(--color-cloud-white) 16%, transparent); box-shadow: none; }}
  .act-l2 {{ background: color-mix(in srgb, var(--color-cloud-white) 34%, transparent); box-shadow: none; }}
  .act-l3 {{ background: color-mix(in srgb, var(--color-cloud-white) 56%, transparent); box-shadow: none; }}
  .act-l4 {{ background: color-mix(in srgb, var(--color-cloud-white) 82%, transparent); box-shadow: none; }}

  /* ─── Dashboard widget row (calendar + activity) ─── */
  .widget-row {{
    display: flex;
    gap: 16px;
    align-items: stretch;
    margin: 0 0 16px;
  }}
  .widget-row > .cal-widget {{ flex: 0 0 248px; }}
  .widget-row > .act-widget {{ flex: 1 1 auto; min-width: 0; margin: 0; }}
  @media (max-width: 720px) {{
    .widget-row {{ flex-wrap: wrap; }}
    .widget-row > .cal-widget,
    .widget-row > .act-widget {{ flex: 1 1 100%; }}
  }}

  /* ─── Calendar widget ─── */
  .cal-widget {{
    background: var(--color-midnight-ink);
    border-radius: 18px;
    box-shadow: var(--inset-subtle);
    padding: 18px 20px 20px;
  }}
  .cal-month {{
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.5px;
    color: var(--color-electric-blue);
    margin-bottom: 14px;
  }}
  .cal-grid {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
  }}
  .cal-head {{
    text-align: center;
    font-size: 11px;
    color: var(--color-ash-gray);
    padding-bottom: 10px;
  }}
  .cal-cell {{
    display: flex;
    align-items: center;
    justify-content: center;
    aspect-ratio: 1 / 1;
    font-size: 13px;
  }}
  .cal-num {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    color: var(--color-cloud-white);
    font-variant-numeric: tabular-nums;
  }}
  .cal-head.cal-weekend,
  .cal-weekend .cal-num {{ color: var(--color-ash-gray); }}
  .cal-today .cal-num {{
    background: var(--color-electric-blue);
    color: #fff;
    font-weight: 500;
  }}

  /* ─── Footer ─── */
  footer {{
    margin-top: 100px;
    padding-top: 20px;
    border-top: 1px solid var(--color-stormy-night);
    color: var(--color-ash-gray);
    font-size: 12px;
  }}
  footer code {{
    background: transparent;
    box-shadow: none;
    padding: 0;
    color: var(--color-ash-gray);
  }}

  /* ─── Responsive ─── */
  @media (max-width: 720px) {{
    .wrap {{ padding: 40px 20px 80px; }}
    header {{ flex-direction: column; gap: 8px; align-items: flex-start; }}
    header h1 {{ font-size: 32px; letter-spacing: -0.8px; }}
    nav.tabs {{ margin-bottom: 28px; }}
    nav.toc {{ margin-bottom: 28px; }}
    h2 {{ font-size: 20px; letter-spacing: -0.5px; margin: 40px 0 16px; }}
  }}
</style>
<script>
  /* Set theme before render to avoid flash. */
  (function () {{
    try {{
      var saved = localStorage.getItem('vault.theme');
      if (saved === 'dark') {{
        document.documentElement.dataset.theme = 'dark';
      }} else if (!saved && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {{
        document.documentElement.dataset.theme = 'dark';
      }}
    }} catch (e) {{}}
  }})();
</script>
</head>
<body>
  <div class="wrap">
    <header>
      <h1><a class="logo-home" href="#dashboard" aria-label="Back to dashboard">Suma</a></h1>
      <div class="header-right">
        <span class="meta">Updated {updated}</span>
        <button class="theme-toggle" type="button" aria-label="Toggle theme" title="Toggle theme">
          <svg class="icon-moon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M6.1 1.6a6 6 0 1 0 8.3 8.3 5 5 0 0 1-8.3-8.3z"/></svg>
          <svg class="icon-sun" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" aria-hidden="true"><circle cx="8" cy="8" r="3"/><line x1="8" y1="1.4" x2="8" y2="3"/><line x1="8" y1="13" x2="8" y2="14.6"/><line x1="1.4" y1="8" x2="3" y2="8"/><line x1="13" y1="8" x2="14.6" y2="8"/><line x1="3.4" y1="3.4" x2="4.6" y2="4.6"/><line x1="11.4" y1="11.4" x2="12.6" y2="12.6"/><line x1="3.4" y1="12.6" x2="4.6" y2="11.4"/><line x1="11.4" y1="4.6" x2="12.6" y2="3.4"/></svg>
        </button>
      </div>
    </header>

    <nav class="tabs" role="tablist">
      <button class="tab active" data-target="view-dashboard" role="tab">Dashboard</button>
      <button class="tab" data-target="view-projects" role="tab">Projects</button>
      <button class="tab" data-target="view-ideas" role="tab">Ideas</button>
      <button class="tab" data-target="view-learning" role="tab">Learning</button>
      <button class="tab" data-target="view-subscriptions" role="tab">Subscriptions</button>
      <button class="tab" data-target="view-builds" role="tab">Builds</button>
      <button class="tab" data-target="view-toolkit" role="tab">Toolkit</button>
      <button class="tab" data-target="view-changelog" role="tab">Changelog</button>
    </nav>

    <section id="view-dashboard" class="view" role="tabpanel">
      {quote_block}
      <div class="widget-row">
        <section class="cal-widget" id="calwidget" aria-label="Calendar"></section>
        {activity_block}
      </div>
      <main>
        {now_body}
        {checkins_body}
        {birthdays_block}
      </main>
    </section>

    <section id="view-projects" class="view" role="tabpanel" hidden>
      <nav class="toc">
        {projects_toc}
      </nav>
      <main>
        {projects_body}
      </main>
    </section>

    <section id="view-ideas" class="view" role="tabpanel" hidden>
      <main>
        {ideas_body}
      </main>
    </section>

    <section id="view-learning" class="view" role="tabpanel" hidden>
      <nav class="toc">
        {learning_toc}
      </nav>
      <main>
        {learning_body}
      </main>
    </section>

    <section id="view-subscriptions" class="view" role="tabpanel" hidden>
      <nav class="toc">
        {subscriptions_toc}
      </nav>
      <main>
        {subscriptions_body}
      </main>
    </section>

    <section id="view-builds" class="view" role="tabpanel" hidden>
      <main>
        {builds_body}
      </main>
    </section>

    <section id="view-toolkit" class="view" role="tabpanel" hidden>
      <nav class="toc">
        {toolkit_toc}
      </nav>
      <main>
        {toolkit_body}
      </main>
    </section>

    <section id="view-changelog" class="view" role="tabpanel" hidden>
      <main>
        {changelog_body}
      </main>
    </section>

    <footer>
      Source <code>Suma/*.md</code> · Rebuild <code>python3 build.py</code>
    </footer>
  </div>

<script>
  (function () {{
    const tabs = document.querySelectorAll('nav.tabs .tab');
    const views = document.querySelectorAll('.view');

    function show(target) {{
      tabs.forEach(t => t.classList.toggle('active', t.dataset.target === target));
      views.forEach(v => {{
        if (v.id === target) v.removeAttribute('hidden');
        else v.setAttribute('hidden', '');
      }});
      try {{ localStorage.setItem('vault.tab', target); }} catch (e) {{}}
    }}

    tabs.forEach(t => t.addEventListener('click', () => {{
      const target = t.dataset.target;
      show(target);
      history.replaceState(null, '', '#' + target.replace(/^view-/, ''));
    }}));

    // Logo → back to dashboard
    const logo = document.querySelector('.logo-home');
    if (logo) {{
      logo.addEventListener('click', (e) => {{
        e.preventDefault();
        show('view-dashboard');
        history.replaceState(null, '', '#dashboard');
      }});
    }}

    // Initial state: URL hash > localStorage > default dashboard
    const hash = location.hash.replace('#', '');
    const valid = ['view-dashboard', 'view-projects', 'view-ideas', 'view-learning', 'view-subscriptions', 'view-builds', 'view-toolkit', 'view-changelog'];
    let initial = 'view-dashboard';
    if (valid.includes('view-' + hash)) initial = 'view-' + hash;
    else {{
      try {{
        const saved = localStorage.getItem('vault.tab');
        if (valid.includes(saved)) initial = saved;
      }} catch (e) {{}}
    }}
    show(initial);

    // Theme toggle
    const toggleBtn = document.querySelector('.theme-toggle');
    if (toggleBtn) {{
      toggleBtn.addEventListener('click', () => {{
        const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        if (next === 'dark') document.documentElement.dataset.theme = 'dark';
        else delete document.documentElement.dataset.theme;
        try {{ localStorage.setItem('vault.theme', next); }} catch (e) {{}}
      }});
    }}
  }})();
</script>

<script>
  /* Calendar — current month with today marked, Monday-first. Rendered live. */
  (function () {{
    const el = document.getElementById('calwidget');
    if (!el) return;
    function render() {{
      const now = new Date();
      const y = now.getFullYear(), m = now.getMonth(), today = now.getDate();
      const monthName = now.toLocaleString('en-GB', {{ month: 'long' }}).toUpperCase();
      const startCol = (new Date(y, m, 1).getDay() + 6) % 7;   // Monday-first
      const days = new Date(y, m + 1, 0).getDate();
      const heads = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
      let cells = '';
      for (let i = 0; i < startCol; i++) cells += '<span class="cal-cell cal-empty"></span>';
      for (let d = 1; d <= days; d++) {{
        const col = (startCol + d - 1) % 7;
        let cls = 'cal-cell';
        if (col >= 5) cls += ' cal-weekend';
        if (d === today) cls += ' cal-today';
        cells += '<span class="' + cls + '"><span class="cal-num">' + d + '</span></span>';
      }}
      el.innerHTML =
        '<div class="cal-month">' + monthName + '</div>' +
        '<div class="cal-grid cal-heads">' + heads.map(function (h, i) {{
          return '<span class="cal-head' + (i >= 5 ? ' cal-weekend' : '') + '">' + h + '</span>';
        }}).join('') + '</div>' +
        '<div class="cal-grid cal-days">' + cells + '</div>';
    }}
    render();
  }})();
</script>

<script id="quotes-data" type="application/json">{quotes_json}</script>
<script>
  /* Swap quote — pick another from the embedded list, no rebuild needed. */
  (function () {{
    var el = document.getElementById('quotes-data');
    var btn = document.querySelector('.quote-swap');
    var fig = document.querySelector('.quote-block');
    if (!el || !btn || !fig) return;
    var quotes = [];
    try {{ quotes = JSON.parse(el.textContent); }} catch (e) {{}}
    if (quotes.length < 2) {{ btn.style.display = 'none'; return; }}
    var textEl = fig.querySelector('.quote-text');
    var cur = textEl ? textEl.textContent : '';
    btn.addEventListener('click', function () {{
      var q, n = 0;
      do {{ q = quotes[Math.floor(Math.random() * quotes.length)]; n++; }} while (q.t === cur && n < 12);
      cur = q.t;
      if (textEl) textEl.textContent = q.t;
      var a = fig.querySelector('.quote-author');
      if (q.a) {{
        if (!a) {{ a = document.createElement('figcaption'); a.className = 'quote-author'; fig.appendChild(a); }}
        a.textContent = q.a;
      }} else if (a) {{
        a.parentNode.removeChild(a);
      }}
    }});
  }})();
</script>
</body>
</html>
"""


def main() -> None:
    archived = archive_completed_tasks()
    if archived:
        print(f"archived {archived} completed task(s) → changelog {_dt.date.today().isoformat()}")

    dash_md = DASH_SRC.read_text(encoding="utf-8")
    log_md = LOG_SRC.read_text(encoding="utf-8")
    learn_md = LEARN_SRC.read_text(encoding="utf-8")
    ideas_md = IDEAS_SRC.read_text(encoding="utf-8")
    proj_md = PROJ_SRC.read_text(encoding="utf-8")
    subs_md = SUBS_SRC.read_text(encoding="utf-8")

    # Header date comes from changelog, not from a hand-maintained line.
    updated = latest_changelog_date(log_md) or "—"

    # Strip cosmetic leading title + manual "Last updated:" from dashboard.md
    dash_md = re.sub(r"^Last updated:\s*.+\n+", "", dash_md, count=1, flags=re.MULTILINE)
    dash_md = re.sub(r"^# Dashboard\s*\n+", "", dash_md, count=1)
    log_md = re.sub(r"^# Changelog\s*\n+", "", log_md, count=1)
    learn_md = re.sub(r"^# Learning\s*\n+", "", learn_md, count=1)
    ideas_md = re.sub(r"^# Ideas\s*\n+", "", ideas_md, count=1)
    proj_md = re.sub(r"^# Projects\s*\n+", "", proj_md, count=1)
    subs_md = re.sub(r"^# Subscriptions\s*\n+", "", subs_md, count=1)

    today = _dt.date.today()
    now_body = render_now_html(dash_md)
    checkins_body = render_checkins_html(dash_md)
    birthdays_block = render_birthdays_html(today)
    activity_block = render_activity_html(scan_activity(log_md), today)
    changelog_body, _ = md_to_html(log_md)
    learning_body, learning_toc = md_to_html(learn_md)
    ideas_body, _ = md_to_html(ideas_md)
    projects_body, projects_toc = md_to_html(proj_md)
    subscriptions_body, subscriptions_toc = md_to_html(subs_md)
    learning_nav = build_toc(learning_toc, level=3)
    projects_nav = build_toc(projects_toc, level=2)
    subscriptions_nav = build_toc(subscriptions_toc, level=2)
    quotes_raw = load_quotes()
    quote_block = render_quote_block(pick_quote_for_today(quotes_raw))
    quotes_parsed = []
    for _q in quotes_raw:
        _t, _a = split_quote(_q)
        quotes_parsed.append({"t": _t or _q.strip(), "a": _a or ""})
    quotes_json = json.dumps(quotes_parsed, ensure_ascii=False).replace("</", "<\\/")
    favicon = favicon_data_uri()
    builds = scan_builds()
    builds_body = render_builds_html(builds)
    BUILDS_OUT.write_text(render_builds_md(builds), encoding="utf-8")

    kit = scan_toolkit()
    toolkit_toc, toolkit_body = render_toolkit_html(kit)
    TOOLKIT_OUT.write_text(render_toolkit_md(kit), encoding="utf-8")

    OUT.write_text(
        HTML_SHELL.format(
            updated=html.escape(updated),
            learning_toc=learning_nav,
            projects_toc=projects_nav,
            now_body=now_body,
            checkins_body=checkins_body,
            birthdays_block=birthdays_block,
            activity_block=activity_block,
            quotes_json=quotes_json,
            favicon=favicon,
            projects_body=projects_body,
            ideas_body=ideas_body,
            learning_body=learning_body,
            subscriptions_toc=subscriptions_nav,
            subscriptions_body=subscriptions_body,
            builds_body=builds_body,
            toolkit_toc=toolkit_toc,
            toolkit_body=toolkit_body,
            changelog_body=changelog_body,
            quote_block=quote_block,
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT}  (updated {updated})")


if __name__ == "__main__":
    main()
