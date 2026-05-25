#!/usr/bin/env python3
from __future__ import annotations

import base64
import datetime as dt
import html
import json
import os
import re
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


USER = "RAMMLS"
MAX_PINNED_REPOS = 5
HOT_WINDOW_DAYS = 30
README_PIN_START = "<!-- PIN-CARDS:START -->"
README_PIN_END = "<!-- PIN-CARDS:END -->"
LANGUAGE_COLORS = {
    "TypeScript": "#3178C6",
    "JavaScript": "#F7DF1E",
    "Python": "#3776AB",
    "Go": "#00ADD8",
    "Shell": "#89E051",
    "C++": "#F34B7D",
    "C": "#555555",
    "Rust": "#DEA584",
    "Jupyter Notebook": "#DA5B0B",
}
ROOT = Path(__file__).resolve().parents[2]
README_PATH = ROOT / "README.md"
ASSETS_DIR = ROOT / ".github" / "assets" / "generated"
FONTS_DIR = ROOT / ".github" / "assets" / "fonts"
ACCENT_COLORS = ["#E0A96D", "#D66B6B", "#7EB6FF", "#66C6B4", "#B89CFF", "#F1C75B"]
BG_BASE = "#0C1015"
BG_ELEVATED = "#131922"
BG_PANEL = "#181F29"
BG_SOFT = "#1F2834"
BORDER_SOFT = "#2D3745"
GRID_LINE = "#2A3442"
TEXT_PRIMARY = "#F5EFE7"
TEXT_SECONDARY = "#C8C0B7"
TEXT_MUTED = "#938B84"
ACCENT_PRIMARY = "#E0A96D"
ACCENT_SECONDARY = "#A86C3D"
ACCENT_GLOW = "#F6C28B"
API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "RAMMLS-profile-generator",
}
DISPLAY_FONT = "'BenzinBold', 'Arial Black', Helvetica, Arial, sans-serif"
UI_FONT = "'BenzinMedium', 'SFMono-Regular', Consolas, monospace"
BODY_FONT = "'BenzinMedium', 'Segoe UI', Helvetica, Arial, sans-serif"
_EMBEDDED_FONT_STYLE: str | None = None


def api_request(url: str) -> dict | list:
    request = urllib.request.Request(url, headers=API_HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def escape(value: str) -> str:
    return html.escape(value, quote=False)


def truncate(value: str, limit: int) -> str:
    value = " ".join((value or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def wrap_lines(value: str, width: int, lines: int) -> list[str]:
    clean = truncate(value or "No description available yet.", width * lines)
    wrapped = textwrap.wrap(clean, width=width, break_long_words=False)
    return (wrapped + [""])[:lines]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def format_date(value: str | None) -> str:
    if not value:
        return "unknown"
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.strftime("%Y-%m-%d")


def language_color(name: str | None) -> str:
    if not name:
        return "#6B7280"
    return LANGUAGE_COLORS.get(name, "#8B5CF6")


def title_font_size(name: str) -> int:
    if len(name) > 24:
        return 24
    if len(name) > 18:
        return 27
    return 31


def font_data_uri(file_path: Path) -> str | None:
    if not file_path.exists():
        return None
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:font/otf;base64,{encoded}"


def svg_font_style() -> str:
    global _EMBEDDED_FONT_STYLE
    if _EMBEDDED_FONT_STYLE is not None:
        return _EMBEDDED_FONT_STYLE

    rules: list[str] = []
    for family, file_name in (
        ("BenzinBold", "benzin-bold.otf"),
        ("BenzinMedium", "benzin-medium.otf"),
    ):
        data_uri = font_data_uri(FONTS_DIR / file_name)
        if data_uri:
            rules.append(
                f"@font-face{{font-family:'{family}';src:url('{data_uri}') format('opentype');font-weight:normal;font-style:normal;}}"
            )
    if not rules:
        _EMBEDDED_FONT_STYLE = ""
        return _EMBEDDED_FONT_STYLE

    rules.append("text{font-kerning:normal;text-rendering:geometricPrecision;}")
    _EMBEDDED_FONT_STYLE = f"<style><![CDATA[{''.join(rules)}]]></style>"
    return _EMBEDDED_FONT_STYLE


def repo_hotness(repo: dict, now: dt.datetime) -> tuple[float, int]:
    pushed_at = dt.datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
    days_since_push = max(0, (now - pushed_at).days)
    freshness = max(0.0, (HOT_WINDOW_DAYS - min(days_since_push, HOT_WINDOW_DAYS)) / HOT_WINDOW_DAYS)
    score = (
        freshness * 100
        + repo.get("stargazers_count", 0) * 4
        + repo.get("forks_count", 0) * 3
        + min(repo.get("open_issues_count", 0), 5)
    )
    return round(score, 2), days_since_push


def repo_card(repo: dict, rank: int) -> str:
    name = repo["name"]
    description = repo.get("description") or "No description available yet."
    language = repo.get("language") or "Mixed"
    stars = repo.get("stargazers_count", 0)
    hotness = repo["hotness_score"]
    days_since_push = repo["days_since_push"]
    lines = wrap_lines(description, width=54, lines=1)
    line1 = lines[0] if lines else ""
    dot = language_color(language)
    name_size = title_font_size(name)
    freshness_label = "today" if days_since_push == 0 else f"{days_since_push}d ago"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="560" height="140" viewBox="0 0 560 140" role="img" aria-labelledby="title desc">
  <title>{escape(name)} pin card</title>
  <desc>{escape(description)}</desc>
  {svg_font_style()}
  <defs>
    <linearGradient id="card-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BG_ELEVATED}"/>
      <stop offset="58%" stop-color="{BG_PANEL}"/>
      <stop offset="100%" stop-color="{BG_BASE}"/>
    </linearGradient>
    <linearGradient id="stroke" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#314053"/>
      <stop offset="52%" stop-color="{ACCENT_PRIMARY}"/>
      <stop offset="100%" stop-color="{ACCENT_SECONDARY}"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="12" flood-color="#000000" flood-opacity="0.3"/>
    </filter>
    <linearGradient id="shine" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{ACCENT_GLOW}" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="560" height="140" rx="22" fill="url(#card-bg)" filter="url(#shadow)"/>
  <rect x="10" y="10" width="540" height="120" rx="16" fill="{BG_PANEL}" fill-opacity="0.88" stroke="url(#stroke)" stroke-width="1.6"/>
  <circle cx="492" cy="40" r="50" fill="{ACCENT_PRIMARY}" opacity="0.12"/>
  <circle cx="458" cy="100" r="60" fill="#66C6B4" opacity="0.08"/>
  <path d="M420 0 L560 0 L560 64 Q480 64 420 0Z" fill="url(#shine)" opacity="0.62"/>
  <rect x="440" y="20" width="94" height="28" rx="14" fill="{BG_SOFT}" stroke="{ACCENT_PRIMARY}" stroke-width="1.1"/>
  <text x="456" y="39" fill="{ACCENT_GLOW}" font-family="{UI_FONT}" font-size="13" letter-spacing="1">TOP #{rank}</text>
  <text x="34" y="40" fill="{TEXT_MUTED}" font-family="{UI_FONT}" font-size="13" letter-spacing="1.4">SCORE {hotness:.1f}</text>
  <text x="34" y="74" fill="{TEXT_PRIMARY}" font-family="{DISPLAY_FONT}" font-size="{name_size}" letter-spacing="0.2">{escape(name)}</text>
  <text x="34" y="100" fill="{TEXT_SECONDARY}" font-family="{BODY_FONT}" font-size="14">{escape(line1)}</text>
  <circle cx="38" cy="118" r="5" fill="{dot}"/>
  <text x="52" y="122" fill="{TEXT_SECONDARY}" font-family="{UI_FONT}" font-size="13">{escape(language)}</text>
  <text x="236" y="122" fill="{TEXT_MUTED}" font-family="{UI_FONT}" font-size="13">Stars {stars}</text>
  <text x="336" y="122" fill="{ACCENT_GLOW}" font-family="{UI_FONT}" font-size="13">Push {freshness_label}</text>
</svg>
"""


def header_banner() -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="280" viewBox="0 0 1280 280" role="img" aria-label="Profile header">
  {svg_font_style()}
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BG_ELEVATED}"/>
      <stop offset="55%" stop-color="{BG_PANEL}"/>
      <stop offset="100%" stop-color="{BG_BASE}"/>
    </linearGradient>
    <linearGradient id="line" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#314053"/>
      <stop offset="55%" stop-color="{ACCENT_PRIMARY}"/>
      <stop offset="100%" stop-color="{ACCENT_SECONDARY}"/>
    </linearGradient>
    <radialGradient id="glow-a" cx="82%" cy="18%" r="52%">
      <stop offset="0%" stop-color="{ACCENT_PRIMARY}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="{ACCENT_PRIMARY}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow-b" cx="92%" cy="78%" r="60%">
      <stop offset="0%" stop-color="#66C6B4" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#66C6B4" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M24 0H0V24" fill="none" stroke="{GRID_LINE}" stroke-width="1"/>
    </pattern>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>
  <rect width="1280" height="280" rx="28" fill="url(#bg)" filter="url(#shadow)"/>
  <rect x="20" y="20" width="1240" height="240" rx="24" fill="{BG_PANEL}" opacity="0.92" stroke="{BORDER_SOFT}" stroke-width="1.4"/>
  <rect x="20" y="20" width="1240" height="240" rx="24" fill="url(#grid)" opacity="0.18"/>
  <rect x="20" y="20" width="1240" height="240" rx="24" fill="url(#glow-a)"/>
  <rect x="20" y="20" width="1240" height="240" rx="24" fill="url(#glow-b)"/>
  <circle cx="1080" cy="76" r="86" fill="{ACCENT_PRIMARY}" opacity="0.14"/>
  <circle cx="1160" cy="170" r="110" fill="#66C6B4" opacity="0.07"/>
  <path d="M70 205 H610" stroke="url(#line)" stroke-width="4" stroke-linecap="round"/>
  <path d="M930 30 C1090 60 1180 118 1220 214" fill="none" stroke="{ACCENT_PRIMARY}" stroke-opacity="0.28" stroke-width="2"/>
  <path d="M890 54 C1040 82 1132 144 1168 222" fill="none" stroke="#66C6B4" stroke-opacity="0.16" stroke-width="1.5"/>
  <circle cx="948" cy="43" r="4" fill="{ACCENT_GLOW}"/>
  <text x="72" y="86" fill="{ACCENT_GLOW}" font-family="{UI_FONT}" font-size="18" letter-spacing="2.2">RAMMLS</text>
  <text x="72" y="136" fill="{TEXT_PRIMARY}" font-family="{DISPLAY_FONT}" font-size="42" letter-spacing="0.2">TeamLead product builder</text>
  <text x="72" y="176" fill="{TEXT_SECONDARY}" font-family="{BODY_FONT}" font-size="24">Go-to-market, автоматизация, ML-прототипы, инфраструктура</text>
  <text x="72" y="226" fill="{TEXT_MUTED}" font-family="{UI_FONT}" font-size="18">превращаю технические решения в выручку и понятный продуктовый вектор</text>
</svg>
"""


def stats_summary_card(user: dict, repositories: list[dict]) -> str:
    followers = user.get("followers", 0)
    public_repos = user.get("public_repos", len(repositories))
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repositories)
    recent_projects = sum(1 for repo in repositories if repo["days_since_push"] <= HOT_WINDOW_DAYS)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="610" height="220" viewBox="0 0 610 220" role="img" aria-label="GitHub summary">
  {svg_font_style()}
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BG_ELEVATED}"/>
      <stop offset="100%" stop-color="{BG_BASE}"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#000000" flood-opacity="0.34"/>
    </filter>
  </defs>
  <rect width="610" height="220" rx="24" fill="url(#bg)" filter="url(#shadow)"/>
  <rect x="16" y="16" width="578" height="188" rx="18" fill="{BG_PANEL}" fill-opacity="0.9" stroke="{BORDER_SOFT}" stroke-width="1.5"/>
  <text x="32" y="48" fill="{ACCENT_GLOW}" font-family="{UI_FONT}" font-size="14" letter-spacing="1.2">GITHUB SNAPSHOT</text>
  <text x="32" y="86" fill="{TEXT_PRIMARY}" font-family="{DISPLAY_FONT}" font-size="28">GitHub core</text>
  <text x="42" y="138" fill="{TEXT_MUTED}" font-family="{UI_FONT}" font-size="16">Repos</text>
  <text x="42" y="178" fill="{TEXT_PRIMARY}" font-family="{DISPLAY_FONT}" font-size="28">{public_repos}</text>
  <text x="190" y="138" fill="{TEXT_MUTED}" font-family="{UI_FONT}" font-size="16">Followers</text>
  <text x="190" y="178" fill="{TEXT_PRIMARY}" font-family="{DISPLAY_FONT}" font-size="28">{followers}</text>
  <text x="348" y="138" fill="{TEXT_MUTED}" font-family="{UI_FONT}" font-size="16">Stars</text>
  <text x="348" y="178" fill="{TEXT_PRIMARY}" font-family="{DISPLAY_FONT}" font-size="28">{total_stars}</text>
  <text x="468" y="138" fill="{TEXT_MUTED}" font-family="{UI_FONT}" font-size="16">Hot 30d</text>
  <text x="468" y="178" fill="{TEXT_PRIMARY}" font-family="{DISPLAY_FONT}" font-size="28">{recent_projects}</text>
</svg>
"""


def top_languages(repositories: list[dict]) -> list[tuple[str, int]]:
    totals: dict[str, int] = {}
    for repo in repositories[:12]:
        repo_name = repo.get("name")
        if not repo_name:
            continue
        try:
            language_bytes = api_request(
                f"https://api.github.com/repos/{USER}/{repo_name}/languages"
            )
        except urllib.error.HTTPError:
            continue
        if not isinstance(language_bytes, dict):
            continue
        for language, value in language_bytes.items():
            totals[language] = totals.get(language, 0) + int(value)
    items = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return items[:5]


def language_overview_card(repositories: list[dict]) -> str:
    items = top_languages(repositories)
    maximum = max((value for _, value in items), default=1)
    bars = []
    for index, (language, value) in enumerate(items):
        y = 74 + index * 28
        width = int((value / maximum) * 270)
        color = ACCENT_COLORS[index % len(ACCENT_COLORS)]
        bars.append(
            f'<text x="34" y="{y}" fill="{TEXT_SECONDARY}" font-family="{BODY_FONT}" font-size="15">{escape(language)}</text>'
            f'<rect x="170" y="{y - 12}" width="270" height="14" rx="7" fill="{BG_SOFT}"/>'
            f'<rect x="170" y="{y - 12}" width="{width}" height="14" rx="7" fill="{color}"/>'
        )
    bars_markup = "".join(bars) if bars else f'<text x="34" y="100" fill="{TEXT_SECONDARY}" font-family="{BODY_FONT}" font-size="16">Не удалось собрать языковую сводку.</text>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="610" height="220" viewBox="0 0 610 220" role="img" aria-label="Language overview">
  {svg_font_style()}
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BG_ELEVATED}"/>
      <stop offset="100%" stop-color="{BG_BASE}"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#000000" flood-opacity="0.34"/>
    </filter>
  </defs>
  <rect width="610" height="220" rx="24" fill="url(#bg)" filter="url(#shadow)"/>
  <rect x="16" y="16" width="578" height="188" rx="18" fill="{BG_PANEL}" fill-opacity="0.9" stroke="{BORDER_SOFT}" stroke-width="1.5"/>
  <text x="32" y="48" fill="{ACCENT_GLOW}" font-family="{UI_FONT}" font-size="14" letter-spacing="1.2">LANGUAGE OVERVIEW</text>
  <text x="32" y="198" fill="{TEXT_MUTED}" font-family="{UI_FONT}" font-size="14">по активным репозиториям и последним рабочим проектам</text>
  {bars_markup}
</svg>
"""


def commit_ticker(entries: list[str]) -> str:
    content = "   //   ".join(entries) or "No public push events yet."
    width = max(2600, len(content) * 12)
    safe_content = escape(content)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="120" viewBox="0 0 1600 120" role="img" aria-label="Recent commit ticker">
  {svg_font_style()}
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{BG_ELEVATED}"/>
      <stop offset="100%" stop-color="{BG_BASE}"/>
    </linearGradient>
    <linearGradient id="stroke" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#314053"/>
      <stop offset="50%" stop-color="{ACCENT_PRIMARY}"/>
      <stop offset="100%" stop-color="{ACCENT_SECONDARY}"/>
    </linearGradient>
    <mask id="fade">
      <linearGradient id="fade-grad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="black"/>
        <stop offset="6%" stop-color="white"/>
        <stop offset="94%" stop-color="white"/>
        <stop offset="100%" stop-color="black"/>
      </linearGradient>
      <rect width="1600" height="120" fill="url(#fade-grad)"/>
    </mask>
  </defs>
  <rect width="1600" height="120" rx="26" fill="url(#bg)"/>
  <rect x="10" y="10" width="1580" height="100" rx="20" fill="{BG_PANEL}" fill-opacity="0.92" stroke="url(#stroke)" stroke-width="1.8"/>
  <text x="28" y="34" fill="{ACCENT_GLOW}" font-family="{UI_FONT}" font-size="15" letter-spacing="1.2">RECENT COMMITS</text>
  <g mask="url(#fade)">
    <text x="1600" y="77" fill="{TEXT_SECONDARY}" font-family="{UI_FONT}" font-size="22" textLength="{width}" lengthAdjust="spacingAndGlyphs">{safe_content}
      <animate attributeName="x" values="1600;-{width}" dur="38s" repeatCount="indefinite"/>
    </text>
  </g>
</svg>
"""


def fetch_all_repositories() -> list[dict]:
    repositories: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"sort": "updated", "per_page": 100, "page": page}
        )
        batch = api_request(f"https://api.github.com/users/{USER}/repos?{query}")
        if not isinstance(batch, list) or not batch:
            break
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repositories


def ranked_repositories() -> list[dict]:
    now = dt.datetime.now(dt.timezone.utc)
    fresh: list[dict] = []
    for repo in fetch_all_repositories():
        if repo.get("fork") or repo.get("archived") or repo.get("name") == USER:
            continue
        score, days_since_push = repo_hotness(repo, now)
        repo["hotness_score"] = score
        repo["days_since_push"] = days_since_push
        if days_since_push <= HOT_WINDOW_DAYS:
            fresh.append(repo)
    
    fresh.sort(
        key=lambda repo: (
            repo["hotness_score"],
            -repo["days_since_push"],
            repo.get("stargazers_count", 0),
        ),
        reverse=True,
    )
    return fresh[:MAX_PINNED_REPOS]


def latest_push_entries(repositories: list[dict]) -> list[str]:
    items: list[str] = []
    for repo in repositories:
        repo_name = repo.get("name")
        if not repo_name:
            continue
        try:
            commits = api_request(
                f"https://api.github.com/repos/{USER}/{repo_name}/commits?per_page=1"
            )
        except urllib.error.HTTPError:
            continue
        if not commits:
            continue
        commit = commits[0]
        message = truncate(commit.get("commit", {}).get("message", "update"), 48)
        items.append(f"{repo_name}: {message}")
    return items


def sync_readme_text() -> None:
    content = README_PATH.read_text(encoding="utf-8")
    replacements = {
        '<h1 align="center">RAMMLS // Neon Dashboard</h1>': '<h1 align="center">RAMMLS</h1>',
        '  Собираю инструменты и интерфейсы, которые убирают рутину: от Linux-автоматизации и developer tooling до CTF-практики и прикладного ML.<br>\n  Сейчас в фокусе <b>self-host платформа для автоматической проверки лабораторных</b> — чтобы преподаватели тратили время на разбор работ, а не на ручную проверку.\n': '  Веду команды и продуктовые направления, где важно не только сделать, но и нормально продать решение: automation, developer tooling, ML-прототипы и инфраструктурные сервисы.<br>\n  Сейчас основной фокус — <b>self-host платформа для автоматической проверки лабораторных работ</b> с внятным UX, нормальной эксплуатацией и понятной ценностью для пользователей.\n',
        '  Разрабатываю продукты и внутренние инструменты, которые ускоряют работу команд: automation, developer tooling, ML-прототипы и инфраструктурные сервисы.<br>\n  Сейчас основной фокус — <b>self-host платформа для автоматической проверки лабораторных работ</b> с нормальным UX и предсказуемой эксплуатацией.\n': '  Веду команды и продуктовые направления, где важно не только сделать, но и нормально продать решение: automation, developer tooling, ML-прототипы и инфраструктурные сервисы.<br>\n  Сейчас основной фокус — <b>self-host платформа для автоматической проверки лабораторных работ</b> с внятным UX, нормальной эксплуатацией и понятной ценностью для пользователей.\n',
        '## Skill Grid': '## Stack',
        '## Stats Core': '## GitHub Snapshot',
        '## Signal Feed': '## Contribution Map',
        '## Activity Stream': '## Recent Activity',
        '  В галерею попадают только самые актуальные репозитории. `hotness-score` считает свежесть последнего push за 120 дней и добавляет бонус за `stars`, `forks` и активные `issues`, поэтому живые проекты поднимаются вверх, а старые постепенно исчезают из топа.\n': '  В галерее только активные проекты. `hotness-score` считает свежесть последнего push за последний месяц и добавляет бонус за `stars`, `forks` и открытые `issues`, поэтому наверху оказываются именно те репозитории, над которыми я реально работаю сейчас.\n',
        '  В галерее только активные проекты. `hotness-score` считает свежесть последнего push за последний месяц и добавляет бонус за `stars`, `forks` и открытые `issues`, поэтому наверху оказываются именно те репозитории, над которыми я реально работаю сейчас.\n': '  В галерее только активные проекты. `hotness-score` считает свежесть последнего push за последний месяц и добавляет бонус за `stars`, `forks` и открытые `issues`, поэтому наверху оказываются именно те репозитории, над которыми я реально работаю сейчас.\n',
        '  Сначала показываю самые живые проекты за последний месяц. Если их меньше пяти, добираю сильными репозиториями из общего пула, чтобы галерея всегда оставалась полной и шла сверху вниз по реальному приоритету.\n': '  В галерее только активные проекты. `hotness-score` считает свежесть последнего push за последний месяц и добавляет бонус за `stars`, `forks` и открытые `issues`, поэтому наверху оказываются именно те репозитории, над которыми я реально работаю сейчас.\n',
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    README_PATH.write_text(content, encoding="utf-8")


def pin_file_name(repo_name: str) -> str:
    return f"pin-{slugify(repo_name)}.svg"


def build_pin_gallery_markup(repositories: list[dict]) -> str:
    rows: list[str] = ['<table align="center">']
    for repo in repositories[:MAX_PINNED_REPOS]:
        rows.append("  <tr>")
        rows.extend(
            [
                '    <td align="center">',
                f'      <a href="{repo["html_url"]}">',
                f'        <img src=".github/assets/generated/{pin_file_name(repo["name"])}" width="480" alt="{escape(repo["name"])} pin" />',
                "      </a>",
                "    </td>",
            ]
        )
        rows.append("  </tr>")
    rows.append("</table>")
    return "\n".join(rows)


def update_readme_pin_block(repositories: list[dict]) -> None:
    content = README_PATH.read_text(encoding="utf-8")
    new_block = (
        f"{README_PIN_START}\n"
        f"{build_pin_gallery_markup(repositories)}\n"
        f"{README_PIN_END}"
    )
    pattern = re.compile(
        rf"{re.escape(README_PIN_START)}.*?{re.escape(README_PIN_END)}",
        re.DOTALL,
    )
    updated = pattern.sub(new_block, content)
    README_PATH.write_text(updated, encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def cleanup_generated_pins() -> None:
    for file_path in ASSETS_DIR.glob("pin-*.svg"):
        file_path.unlink(missing_ok=True)
    (ASSETS_DIR / "spotify-placeholder.svg").unlink(missing_ok=True)
    (ASSETS_DIR / "matrix-grid.svg").unlink(missing_ok=True)
    (ASSETS_DIR / "terminal-header.svg").unlink(missing_ok=True)


def generate() -> None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("PROFILE_GITHUB_TOKEN")
    if token:
        API_HEADERS["Authorization"] = f"Bearer {token}"

    repositories = ranked_repositories()
    user_data = api_request(f"https://api.github.com/users/{USER}")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_generated_pins()

    write(ASSETS_DIR / "header-banner.svg", header_banner())
    write(ASSETS_DIR / "stats-summary.svg", stats_summary_card(user_data, repositories))
    write(ASSETS_DIR / "languages-overview.svg", language_overview_card(repositories))

    for rank, repository in enumerate(repositories, start=1):
        write(
            ASSETS_DIR / pin_file_name(repository["name"]),
            repo_card(repository, rank),
        )

    write(ASSETS_DIR / "commit-ticker.svg", commit_ticker(latest_push_entries(repositories)))
    sync_readme_text()
    update_readme_pin_block(repositories)


if __name__ == "__main__":
    generate()
