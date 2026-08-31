import re

import fitz  # PyMuPDF

# Canonical header sets for section detection
SKILLS_HEADERS = {
    "skill", "skills",
    "technical skills", "technical expertise",
    "core competencies",
    "key skills",
}

PROJECTS_HEADERS = {
    "project", "projects",
    "personal projects", "selected projects",
    "side projects",
    "open source", "open-source",
}

# Any uppercase/title-case line that could be the next section boundary
_ANY_HEADER = re.compile(
    r"^(?:"
    r"experience|work\s+experience|employment|work\s+history|"
    r"education|certifications?|awards?|publications?|languages?|"
    r"summary|objective|about|contact|references?|"
    r"skills?|technical\s+skills|technical\s+expertise|core\s+competencies|key\s+skills|"
    r"projects?|personal\s+projects|selected\s+projects|side\s+projects|open[-\s]?source"
    r")\s*:?\s*$",
    re.IGNORECASE,
)


def _normalize_header(line: str) -> str:
    """Normalize a header line for comparison: strip whitespace, trailing colons, collapse inner whitespace, lower."""
    s = line.strip()
    s = s.rstrip(":").strip()  # handle "Technical Skills:" and "Skills :"
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def extract_text_from_pdf(content: bytes) -> str:
    """Extract all text from a PDF document."""
    doc = fitz.open(stream=content, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def extract_layout_from_pdf(content: bytes) -> dict:
    """Extract text with visual metadata (spans with bbox, size, font, color, page dimensions)."""
    doc = fitz.open(stream=content, filetype="pdf")
    pages_layout = []
    for page_num, page in enumerate(doc):
        rect = page.rect
        page_dict = {
            "page": page_num,
            "width": rect.width,
            "height": rect.height,
            "spans": [],
        }
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        page_dict["spans"].append({
                            "text": span.get("text", ""),
                            "bbox": span.get("bbox"),
                            "size": span.get("size", 10),
                            "font": span.get("font", "helv"),
                            "color": span.get("color", 0),
                            "origin": span.get("origin"),
                        })
        pages_layout.append(page_dict)
    doc.close()
    return {"pages": pages_layout}


# ── Font mapping ────────────────────────────────────────────────────────────

_FONT_MAP = {
    "helvetica": "helv", "arial": "helv", "calibri": "helv",
    "helvetica-bold": "hebo", "arial-bold": "hebo", "calibri-bold": "hebo",
    "helvetica-oblique": "heit", "arial-italic": "heit",
    "helvetica-boldoblique": "hebi", "arial-bolditalic": "hebi",
    "times": "tiro", "timesnewroman": "tiro", "timesnewromanpsmt": "tiro",
    "times-bold": "tibo", "timesnewroman-bold": "tibo", "timesnewromanps-boldmt": "tibo",
    "times-italic": "tiit", "timesnewroman-italic": "tiit", "timesnewromanps-italicmt": "tiit",
    "times-bolditalic": "tibi",
    "courier": "cour", "couriernew": "cour",
    "courier-bold": "cobo", "couriernew-bold": "cobo",
    "garamond": "tiro", "georgia": "tiro", "palatino": "tiro",
    "cambria": "tiro", "bookantiqua": "tiro",
}


def _map_font(pdf_font_name: str) -> str:
    """Map a PDF font name to the closest base14 font PyMuPDF can write with."""
    if not pdf_font_name:
        return "helv"
    name = re.sub(r"^[A-Z]{6}\+", "", pdf_font_name)
    key = name.lower().replace(" ", "").replace("-", "")

    if key in _FONT_MAP:
        return _FONT_MAP[key]
    for map_key, base14 in _FONT_MAP.items():
        if map_key in key or key in map_key:
            return base14

    base14_names = {"helv", "hebo", "heit", "hebi", "tiro", "tibo", "tiit", "tibi",
                    "cour", "cobo", "coob", "cobi", "symb", "zadb"}
    if pdf_font_name.lower() in base14_names:
        return pdf_font_name
    return "helv"


def _color_int_to_tuple(c: int) -> tuple[float, float, float]:
    return (((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0)


# ── Style extraction: build a per-element-type profile from the PDF ─────────

class _SpanStyle:
    """Style properties for one type of text element."""
    __slots__ = ("font_raw", "font", "size", "color", "x", "flags")

    def __init__(self, font_raw: str, size: float, color: int, x: float, flags: int = 0):
        self.font_raw = font_raw
        self.font = _map_font(font_raw)
        self.size = size
        self.color = _color_int_to_tuple(color)
        self.x = x
        self.flags = flags

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & (1 << 4)) or "bold" in self.font_raw.lower()


def _profile_section(page, headers: set[str]) -> dict | None:
    """Profile a resume section, extracting separate styles for the header, sub-headers, and body/bullets.

    Returns None if the section isn't found. Otherwise returns:
        y_top:        top of the header line (for stream deletion boundary)
        y_body_start: where body text begins (below header)
        y_bottom:     bottom of section (above next header)
        header_style: _SpanStyle for the section title
        subheader_style: _SpanStyle for project name lines (bold / larger than body)
        body_style:   _SpanStyle for regular body & bullet text
        bullet_char:  the actual bullet character used (e.g. '•', '–', '-')
        bullet_x:     x-position of the bullet character
        text_x:       x-position of bullet continuation text
        line_spacing:  measured vertical gap between body lines
        lines:        list of parsed line dicts for reference
    """
    text_dict = page.get_text("dict")

    # Flatten all lines with their spans
    all_lines: list[dict] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_text = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
            if not line_text:
                continue
            max_size = max((s.get("size", 0) for s in line.get("spans", [])), default=0)
            all_lines.append({
                "text": line_text,
                "bbox": line.get("bbox"),
                "spans": line.get("spans", []),
                "max_size": max_size,
            })

    # ── Find the header line ────────────────────────────────────────────
    header_idx = -1
    header_size = 0.0
    for idx, ln in enumerate(all_lines):
        norm = _normalize_header(ln["text"])
        if not norm:
            continue
        if norm in headers or (len(norm) < 35 and any(h in norm for h in headers)):
            header_idx = idx
            header_size = ln["max_size"]
            break

    if header_idx == -1:
        return None

    header_line = all_lines[header_idx]
    header_bbox = header_line["bbox"]
    y_top = header_bbox[1]

    # Profile the header style from its first non-empty span
    header_span = next((s for s in header_line["spans"] if s.get("text", "").strip()), header_line["spans"][0])
    header_style = _SpanStyle(
        font_raw=header_span.get("font", "helv"),
        size=header_span.get("size", 12.0),
        color=header_span.get("color", 0),
        x=header_span["bbox"][0],
        flags=header_span.get("flags", 0),
    )

    # ── Find the next section header (boundary) ─────────────────────────
    y_bottom = page.rect.height - 20
    for idx in range(header_idx + 1, len(all_lines)):
        ln = all_lines[idx]
        norm = _normalize_header(ln["text"])
        if not norm:
            continue
        is_next = bool(_ANY_HEADER.match(ln["text"])) or (
            ln["max_size"] >= header_size - 1.0
            and len(ln["text"].split()) <= 4
            and ln["bbox"][1] > y_top + 15
        )
        if is_next:
            y_bottom = ln["bbox"][1] - 2
            break

    if y_bottom <= y_top + 10:
        return None

    # ── Collect all body lines (between header and next section) ────────
    body_lines = []
    for idx in range(header_idx + 1, len(all_lines)):
        ln = all_lines[idx]
        if ln["bbox"][1] >= y_bottom:
            break
        body_lines.append(ln)

    if not body_lines:
        return None

    # ── Classify each body line as sub-header vs bullet vs plain text ───
    # Strategy: collect all spans, find the dominant body font/size,
    # then anything with a different (larger/bold) font is a sub-header.

    # Gather all body spans
    all_body_spans = []
    for ln in body_lines:
        for s in ln["spans"]:
            if s.get("text", "").strip():
                all_body_spans.append(s)

    # Find dominant body font + size by character count
    font_size_counts: dict[tuple[str, float], int] = {}
    for s in all_body_spans:
        key = (s.get("font", ""), round(s.get("size", 10), 1))
        font_size_counts[key] = font_size_counts.get(key, 0) + len(s.get("text", ""))

    dominant_key = max(font_size_counts, key=font_size_counts.get) if font_size_counts else ("helv", 10.0)
    dominant_font, dominant_size = dominant_key

    # Body style: from spans matching the dominant font/size
    body_spans = [s for s in all_body_spans
                  if s.get("font", "") == dominant_font and abs(s.get("size", 10) - dominant_size) < 0.5]
    body_color = body_spans[0].get("color", 0) if body_spans else 0
    body_x_positions = sorted(s["bbox"][0] for s in body_spans)
    body_x = body_x_positions[0] if body_x_positions else 50.0

    body_style = _SpanStyle(
        font_raw=dominant_font,
        size=dominant_size,
        color=body_color,
        x=body_x,
        flags=body_spans[0].get("flags", 0) if body_spans else 0,
    )

    # Sub-header style: spans that are NOT the dominant font/size (different font OR bigger size OR bold flag)
    subheader_spans = [s for s in all_body_spans
                       if s.get("font", "") != dominant_font or abs(s.get("size", 10) - dominant_size) >= 0.5
                       or (s.get("flags", 0) & (1 << 4) and not (body_spans[0].get("flags", 0) & (1 << 4)) if body_spans else False)]

    # If no distinct sub-header style, check if any lines look like project titles
    # (lines at body_x that start a named project — short, not a bullet)
    if not subheader_spans:
        for ln in body_lines:
            text = ln["text"]
            # Sub-header heuristic: line at x ≈ body_x, short-ish, contains '|' or ':' (common in project titles)
            if ("|" in text or ":" in text) and len(text.split()) <= 15:
                for s in ln["spans"]:
                    if s.get("text", "").strip():
                        subheader_spans.append(s)

    if subheader_spans:
        # Use the first sub-header span as the style reference
        sh_ref = subheader_spans[0]
        subheader_style = _SpanStyle(
            font_raw=sh_ref.get("font", dominant_font),
            size=sh_ref.get("size", dominant_size),
            color=sh_ref.get("color", body_color),
            x=sh_ref["bbox"][0],
            flags=sh_ref.get("flags", 0),
        )
    else:
        # Fallback: same as body but try bold variant
        bold_name = dominant_font
        if "bold" not in dominant_font.lower():
            bold_name = re.sub(r"^([A-Z]{6}\+)?", r"\1", dominant_font).replace("-", "-Bold") if "-" in dominant_font else dominant_font + "-Bold"
        subheader_style = _SpanStyle(
            font_raw=bold_name,
            size=dominant_size,
            color=body_color,
            x=body_x,
            flags=body_spans[0].get("flags", 0) | (1 << 4) if body_spans else (1 << 4),
        )

    # ── Detect bullet character and positions ───────────────────────────
    bullet_char = "•"
    bullet_x = body_x
    text_x = body_x + 10  # default indent for text after bullet

    for ln in body_lines:
        for s in ln["spans"]:
            txt = s.get("text", "").strip()
            if txt in ("•", "–", "-", "▪", "►", "●", "◦", "‣", "·"):
                bullet_char = txt
                bullet_x = s["bbox"][0]
                # Find the next span on the same line for text_x
                spans_on_line = [sp for sp in ln["spans"] if sp.get("text", "").strip() and sp["bbox"][0] > s["bbox"][0]]
                if spans_on_line:
                    text_x = min(sp["bbox"][0] for sp in spans_on_line)
                break
        else:
            continue
        break

    # If no bullet character found, derive text_x from indented lines
    unique_xs = sorted(set(round(x, 1) for x in body_x_positions))
    if len(unique_xs) > 1 and text_x == body_x + 10:
        text_x = unique_xs[1]

    # ── Line spacing ────────────────────────────────────────────────────
    body_ys = sorted(set(
        round(s["origin"][1], 1) for s in body_spans if "origin" in s
    ))
    if len(body_ys) >= 2:
        gaps = [body_ys[i+1] - body_ys[i] for i in range(len(body_ys) - 1) if body_ys[i+1] - body_ys[i] > 1]
        line_spacing = (sum(gaps) / len(gaps)) if gaps else dominant_size * 1.35
    else:
        line_spacing = dominant_size * 1.35

    y_body_start = header_bbox[3] + (line_spacing * 0.4)

    return {
        "y_top": y_top,
        "y_body_start": y_body_start,
        "y_bottom": y_bottom,
        "header_style": header_style,
        "subheader_style": subheader_style,
        "body_style": body_style,
        "bullet_char": bullet_char,
        "bullet_x": bullet_x,
        "text_x": text_x,
        "line_spacing": line_spacing,
    }


# ── Content stream editing ──────────────────────────────────────────────────

def _delete_y_range_from_stream(stream: str, page_height: float, y_top: float, y_bottom: float) -> str:
    """Remove q BT...ET Q blocks whose TD y falls in [y_top, y_bottom] (PyMuPDF top-down coords).

    Preserves ruling lines, graphics, and all non-text operators.
    """
    pdf_y_hi = page_height - y_top + 2
    pdf_y_lo = page_height - y_bottom - 2

    block_re = re.compile(r"q\s+BT.*?ET\s+Q", re.DOTALL)
    td_re = re.compile(r"([\d.e+-]+)\s+([\d.e+-]+)\s+TD")

    def keep(m):
        td = td_re.search(m.group(0))
        if td:
            td_y = float(td.group(2))
            return not (pdf_y_lo <= td_y <= pdf_y_hi)
        return True

    return block_re.sub(lambda m: m.group(0) if keep(m) else "", stream)


# ── Write replacement text using profiled styles ────────────────────────────

def _insert_section_text(page, profile: dict, text: str):
    """Write replacement text line-by-line, using the individually-profiled styles for each element type."""
    import textwrap

    sub = profile["subheader_style"]
    body = profile["body_style"]
    bullet_char = profile["bullet_char"]
    bullet_x = profile["bullet_x"]
    text_x = profile["text_x"]
    line_spacing = profile["line_spacing"]

    current_y = profile["y_body_start"]
    y_limit = profile["y_bottom"]

    right_margin = page.rect.width - 36
    body_avail = right_margin - body.x
    body_char_w = body.size * 0.52
    body_wrap = max(20, int(body_avail / body_char_w))

    bullet_avail = right_margin - text_x
    bullet_wrap = max(15, int(bullet_avail / body_char_w))

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if current_y > y_limit:
            break

        if not stripped:
            current_y += line_spacing * 0.5
            continue

        # ── Sub-header (project title) ──────────────────────────────────
        is_subheader = stripped.startswith(("### ", "## "))
        if is_subheader:
            label = stripped.lstrip("#").strip().strip("*")
            page.insert_text(
                (sub.x, current_y), label,
                fontsize=sub.size, fontname=sub.font, color=sub.color,
            )
            current_y += line_spacing
            continue

        # Also detect "ProjectName | Tech, Stack" pattern (no markdown prefix)
        if "|" in stripped and len(stripped.split()) <= 15 and not stripped.startswith(("- ", "• ", "* ", "– ")):
            page.insert_text(
                (sub.x, current_y), stripped,
                fontsize=sub.size, fontname=sub.font, color=sub.color,
            )
            current_y += line_spacing
            continue

        # ── Bullet line ─────────────────────────────────────────────────
        is_bullet = stripped.startswith(("- ", "• ", "* ", "– ", "▪ "))
        if is_bullet:
            bullet_content = stripped[2:].strip()

            # Write bullet character at the original bullet x-position
            page.insert_text(
                (bullet_x, current_y), bullet_char,
                fontsize=body.size, fontname=body.font, color=body.color,
            )

            # Word-wrap and write content at the original text indentation
            for wrapped in textwrap.wrap(bullet_content, width=bullet_wrap):
                if current_y > y_limit:
                    break
                page.insert_text(
                    (text_x, current_y), wrapped,
                    fontsize=body.size, fontname=body.font, color=body.color,
                )
                current_y += line_spacing
            continue

        # ── Regular text line ───────────────────────────────────────────
        for wrapped in textwrap.wrap(stripped, width=body_wrap):
            if current_y > y_limit:
                break
            page.insert_text(
                (body.x, current_y), wrapped,
                fontsize=body.size, fontname=body.font, color=body.color,
            )
            current_y += line_spacing


# ── Public API ──────────────────────────────────────────────────────────────

def rewrite_pdf_layout(
    original_pdf_bytes: bytes,
    rewritten_text: str,
) -> bytes:
    """Replace Skills and Projects sections in the original PDF in-place.

    1. Profiles each section to extract individual styles for headers, sub-headers, and body text.
    2. Crops out the body text rectangle using content stream editing (preserves ruling lines, graphics).
    3. Writes replacement text back at the original positions using the profiled styles.
    """
    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        return original_pdf_bytes

    skills_text, projects_text = _split_rewritten_sections(rewritten_text)

    for headers, replacement_text in [
        (SKILLS_HEADERS, skills_text),
        (PROJECTS_HEADERS, projects_text),
    ]:
        if not replacement_text.strip():
            continue

        for page in doc:
            profile = _profile_section(page, headers)
            if not profile:
                continue

            # 1) Read the raw content stream
            page.clean_contents()
            xref = page.get_contents()[0]
            stream = doc.xref_stream(xref).decode("latin-1")

            # 2) Crop out ONLY the body text (below header, above next section)
            cleaned = _delete_y_range_from_stream(
                stream, page.rect.height,
                profile["y_body_start"] - 2,
                profile["y_bottom"],
            )
            doc.update_stream(xref, cleaned.encode("latin-1"))

            # 3) Write replacement text using the profiled styles
            _insert_section_text(page, profile, replacement_text)

            break  # section found on this page, move to next section

    output_bytes = doc.tobytes()
    doc.close()
    return output_bytes



def replace_sections_in_text(original_text: str, new_skills: str, new_projects: str) -> str:
    """Replace skills and projects sections in original extracted resume text, preserving all other sections."""
    lines = original_text.splitlines()
    output_lines: list[str] = []
    capturing_skills = False
    capturing_projects = False
    skills_inserted = False
    projects_inserted = False

    for line in lines:
        stripped = line.strip()
        norm = _normalize_header(stripped)

        # Check section boundaries
        is_skills_header = norm in SKILLS_HEADERS or (len(norm) < 30 and any(h in norm for h in SKILLS_HEADERS))
        is_projects_header = norm in PROJECTS_HEADERS or (len(norm) < 30 and any(h in norm for h in PROJECTS_HEADERS))
        is_other_header = bool(_ANY_HEADER.match(stripped)) and not is_skills_header and not is_projects_header

        if is_skills_header:
            capturing_skills = True
            capturing_projects = False
            output_lines.append(line)  # keep original header
            output_lines.append("")
            output_lines.append(new_skills.strip())
            output_lines.append("")
            skills_inserted = True
            continue

        if is_projects_header:
            capturing_projects = True
            capturing_skills = False
            output_lines.append(line)  # keep original header
            output_lines.append("")
            output_lines.append(new_projects.strip())
            output_lines.append("")
            projects_inserted = True
            continue

        if is_other_header:
            capturing_skills = False
            capturing_projects = False
            output_lines.append(line)
            continue

        if capturing_skills or capturing_projects:
            # Skip old section body lines
            continue

        # Keep everything else (Contact, Summary, Experience, Education)
        output_lines.append(line)

    # If skills or projects weren't in the original text, append them
    if not skills_inserted and new_skills.strip():
        output_lines.append("\n\n## Skills\n" + new_skills.strip())
    if not projects_inserted and new_projects.strip():
        output_lines.append("\n\n## Projects\n" + new_projects.strip())

    return "\n".join(output_lines).strip()


def _split_rewritten_sections(text: str) -> tuple[str, str]:
    """Split '## Skills\\n...\\n## Projects\\n...' into (skills_text, projects_text)."""
    skills = ""
    projects = ""

    # Normalize markdown headers
    cleaned = text.strip()
    skills_match = re.search(r"(?i)##\s*skills?\s*\n", cleaned)
    projects_match = re.search(r"(?i)##\s*projects?\s*\n", cleaned)

    if skills_match and projects_match:
        if skills_match.start() < projects_match.start():
            skills = cleaned[skills_match.end():projects_match.start()].strip()
            projects = cleaned[projects_match.end():].strip()
        else:
            projects = cleaned[projects_match.end():skills_match.start()].strip()
            skills = cleaned[skills_match.end():].strip()
    elif skills_match:
        skills = cleaned[skills_match.end():].strip()
    elif projects_match:
        projects = cleaned[projects_match.end():].strip()
    else:
        skills = cleaned

    return skills, projects


def extract_sections(text: str) -> dict[str, str | bool]:
    """Return {'skills': ..., 'projects': ...} pulled from resume text."""
    skills_text = _extract_section(text, SKILLS_HEADERS)
    projects_text = _extract_section(text, PROJECTS_HEADERS)
    
    # Fallback: if both sections empty, use full text slice with warning
    if not skills_text and not projects_text:
        fallback = text.strip()[:4000]
        return {
            "skills": fallback, 
            "projects": "", 
            "_fallback": True, 
            "_warning": "Could not detect Skills/Projects sections — using full resume text"
        }
    
    return {"skills": skills_text, "projects": projects_text}


def _extract_section(text: str, target_names: set[str]) -> str:
    """Extract the content of a named section from resume text."""
    lines = text.splitlines()
    result: list[str] = []
    capturing = False

    for line in lines:
        stripped = line.strip()
        normalized = _normalize_header(stripped)

        if normalized in target_names:
            capturing = True
            result = []
            continue

        if capturing:
            # Stop at the next recognizable section header
            if _ANY_HEADER.match(stripped) or (stripped.isupper() and len(stripped) > 3 and len(stripped.split()) <= 4):
                break
            result.append(line)

    return "\n".join(result).strip()
