import html as html_module
import re
from textwrap import dedent


_CSS = dedent("""
    body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 11pt; line-height: 1.5; margin: 0.75in; color: #1a1a1a; }
    h1 { font-size: 18pt; margin-bottom: 4pt; }
    h2 { font-size: 13pt; border-bottom: 1px solid #333; padding-bottom: 3pt; margin-top: 16pt; margin-bottom: 6pt; }
    h3 { font-size: 11pt; font-weight: bold; margin-top: 8pt; }
    ul { margin: 4pt 0; padding-left: 18pt; }
    li { margin-bottom: 2pt; }
    p { margin: 4pt 0; }
    .section { margin-bottom: 12pt; }
""")


def _text_to_html(text: str) -> str:
    """Convert plain resume text to basic HTML for PDF rendering."""
    cleaned_text = text.strip()
    if '"skills"' in cleaned_text and '"projects"' in cleaned_text:
        from app.utils.llm import extract_json

        parsed = extract_json(cleaned_text)
        s_val = None
        p_val = None
        if isinstance(parsed, dict):
            s_val = parsed.get("skills")
            p_val = parsed.get("projects")
        if not s_val or not p_val:
            m_s = re.search(r'"skills"\s*:\s*"(.*?)(?=",\s*"projects"|"\s*\})', cleaned_text, re.DOTALL)
            m_p = re.search(r'"projects"\s*:\s*"(.*?)(?="\s*\}|\Z)', cleaned_text, re.DOTALL)
            if m_s:
                s_val = m_s.group(1).replace(r"\"", '"').replace(r"\n", "\n")
            if m_p:
                p_val = m_p.group(1).replace(r"\"", '"').replace(r"\n", "\n")
        if s_val is not None and p_val is not None:
            cleaned_text = f"## Skills\n\n{str(s_val).strip()}\n\n## Projects\n\n{str(p_val).strip()}"

    cleaned_text = re.sub(r"(?i)\n*##\s*projects\s*$", "", cleaned_text.strip())
    if not re.search(r"(?i)##\s*projects", cleaned_text):
        match = re.search(r"\n(?=###\s+)", cleaned_text)
        if match:
            idx = match.start()
            cleaned_text = cleaned_text[:idx] + "\n\n## Projects\n" + cleaned_text[idx:]

    lines = cleaned_text.split("\n")
    parts: list[str] = []
    in_ul = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append("<br>")
            continue

        if stripped.startswith("# "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<h1>{html_module.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<h2>{html_module.escape(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<h3>{html_module.escape(stripped[4:])}</h3>")
        elif stripped.startswith(("- ", "• ", "* ", "•", "-")):
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            content = stripped.lstrip("•-* ").strip()
            parts.append(f"<li>{html_module.escape(content)}</li>")
        else:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<p>{html_module.escape(stripped)}</p>")

    if in_ul:
        parts.append("</ul>")

    return "\n".join(parts)


def _build_html(resume_html: str, css: str | None = None) -> str:
    css_block = css if css is not None else _CSS
    return dedent(f"""\
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            {css_block}
          </style>
        </head>
        <body>
          {resume_html}
        </body>
        </html>
    """)


def render_resume_to_pdf(resume_text: str) -> bytes:
    """Render resume_text to PDF bytes via WeasyPrint preserving CSS."""
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise RuntimeError("weasyprint not installed") from e
    resume_html = _text_to_html(resume_text)
    html_content = _build_html(resume_html)
    return HTML(string=html_content).write_pdf()


def render_resume_to_pdf_with_css(resume_text: str, css: str | None = None) -> bytes:
    """Render resume_text to PDF bytes with optional custom CSS."""
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise RuntimeError("weasyprint not installed") from e
    resume_html = _text_to_html(resume_text)
    html_content = _build_html(resume_html, css=css)
    return HTML(string=html_content).write_pdf()
