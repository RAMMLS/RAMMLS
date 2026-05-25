#!/usr/bin/env python3
from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
README_PATH = ROOT / "README.md"
PREVIEW_PATH = ROOT / ".github" / "assets" / "generated" / "readme-preview.html"
FONT_DIR = ROOT / ".github" / "assets" / "fonts"


def render_markdown(markdown_text: str) -> str:
    html_parts: list[str] = []
    paragraph_buffer: list[str] = []
    raw_block_tag: str | None = None
    raw_block_lines: list[str] = []

    def preserve_inline_html(text: str) -> str:
        escaped = html.escape(text)
        replacements = {
            "&lt;br&gt;": "<br>",
            "&lt;b&gt;": "<b>",
            "&lt;/b&gt;": "</b>",
            "&lt;strong&gt;": "<strong>",
            "&lt;/strong&gt;": "</strong>",
            "&lt;code&gt;": "<code>",
            "&lt;/code&gt;": "</code>",
        }
        for old, new in replacements.items():
            escaped = escaped.replace(old, new)
        return escaped

    def flush_paragraph() -> None:
        if not paragraph_buffer:
            return
        text = " ".join(line.strip() for line in paragraph_buffer)
        html_parts.append(f"<p>{preserve_inline_html(text)}</p>")
        paragraph_buffer.clear()

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if raw_block_tag:
            raw_block_lines.append(preserve_inline_html(line) if not stripped.startswith("<") else line)
            if stripped == f"</{raw_block_tag}>":
                html_parts.append("\n".join(raw_block_lines))
                raw_block_tag = None
                raw_block_lines.clear()
            continue
        if not stripped:
            flush_paragraph()
            continue
        if stripped == "---":
            flush_paragraph()
            html_parts.append("<hr />")
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            html_parts.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            html_parts.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            flush_paragraph()
            html_parts.append(stripped)
            continue
        if re.match(r"<(p|div)\b", stripped) and not re.search(r"</(p|div)>$", stripped):
            flush_paragraph()
            raw_block_tag = "p" if stripped.startswith("<p") else "div"
            raw_block_lines.append(line)
            continue
        if stripped.startswith("<"):
            flush_paragraph()
            html_parts.append(line)
            continue
        paragraph_buffer.append(line)

    flush_paragraph()
    rendered = "\n".join(html_parts)
    rendered = re.sub(r"\n{2,}", "\n", rendered)
    return rendered


def build_preview_page(rendered_html: str) -> str:
    font_css = ""
    if (FONT_DIR / "benzin-bold.otf").exists():
        font_css += """
    @font-face {
      font-family: "BenzinBold";
      src: url("../fonts/benzin-bold.otf") format("opentype");
      font-display: swap;
    }
"""
    if (FONT_DIR / "benzin-medium.otf").exists():
        font_css += """
    @font-face {
      font-family: "BenzinMedium";
      src: url("../fonts/benzin-medium.otf") format("opentype");
      font-display: swap;
    }
"""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RAMMLS README Preview</title>
  <base href="../../../" />
  <style>
    {font_css}
    :root {{
      color-scheme: dark;
    }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at 82% 12%, rgba(224, 169, 109, 0.16), transparent 20%),
        radial-gradient(circle at 88% 78%, rgba(102, 198, 180, 0.10), transparent 24%),
        linear-gradient(180deg, #0b0f14 0%, #121821 100%);
      color: #f5efe7;
      font: 16px/1.7 "BenzinMedium", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(42, 52, 66, 0.16) 1px, transparent 1px),
        linear-gradient(90deg, rgba(42, 52, 66, 0.16) 1px, transparent 1px);
      background-size: 28px 28px;
      mask-image: radial-gradient(circle at center, black 40%, transparent 95%);
      opacity: 0.5;
    }}
    .shell {{
      position: relative;
      max-width: 1180px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }}
    .markdown-body {{
      box-sizing: border-box;
      min-width: 200px;
      max-width: 100%;
      margin: 0 auto;
      padding: 28px;
      border: 1px solid #2d3745;
      border-radius: 28px;
      background: rgba(19, 25, 34, 0.88);
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
    }}
    .markdown-body img {{
      max-width: 100%;
      background-color: transparent;
    }}
    .markdown-body table {{
      width: 100%;
      table-layout: fixed;
      border-collapse: collapse;
    }}
    .markdown-body td,
    .markdown-body th {{
      border: none;
      vertical-align: top;
    }}
    .markdown-body hr {{
      border: 0;
      border-top: 1px solid #2d3745;
      margin: 32px 0;
    }}
    .markdown-body h1,
    .markdown-body h2,
    .markdown-body h3 {{
      color: #f5efe7;
      font-family: "BenzinBold", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      letter-spacing: 0.02em;
    }}
    .markdown-body p,
    .markdown-body li {{
      color: #c8c0b7;
    }}
    .markdown-body code {{
      background: rgba(31, 40, 52, 0.92);
      color: #f6c28b;
      padding: 0.15em 0.35em;
      border-radius: 6px;
      font-family: "BenzinMedium", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .markdown-body a {{
      color: #f6c28b;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <article class="markdown-body">{rendered_html}</article>
  </main>
</body>
</html>
"""


def main() -> None:
    markdown_text = README_PATH.read_text(encoding="utf-8")
    rendered_html = render_markdown(markdown_text)
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_PATH.write_text(build_preview_page(rendered_html), encoding="utf-8")
    print(PREVIEW_PATH)


if __name__ == "__main__":
    main()
