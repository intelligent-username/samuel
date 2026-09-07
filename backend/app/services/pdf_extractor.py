import re

import fitz  # PyMuPDF

# Canonical header sets for section detection
SKILLS_HEADERS = {
    "skill", "skills",
    "technical skills", "technical expertise",
    "core competencies", "core skills",
    "key skills", "skills & tools", "skills & abilities",
    "technologies", "technical proficiencies", "programming skills",
    "skills summary",
}

PROJECTS_HEADERS = {
    "project", "projects",
    "personal projects", "selected projects",
    "side projects", "academic projects", "key projects",
    "open source", "open-source", "project experience",
    "notable projects", "recent projects",
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
    __slots__ = ("font_raw", "font", "font_obj", "size", "color", "x", "flags")

    def __init__(self, font_raw: str, font_name: str, font_obj: fitz.Font, size: float, color: int, x: float, flags: int = 0):
        self.font_raw = font_raw
        self.font = font_name
        self.font_obj = font_obj
        self.size = size
        self.color = _color_int_to_tuple(color)
        self.x = x
        self.flags = flags

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & (1 << 4)) or "bold" in self.font_raw.lower()


def _setup_page_fonts(doc, page) -> dict[str, tuple[str, fitz.Font]]:
    """Extract and register embedded fonts from the PDF on the page so PyMuPDF writes with the true font."""
    font_registry: dict[str, tuple[str, fitz.Font]] = {}
    if not doc:
        return font_registry

    try:
        page_fonts = page.get_fonts()
        for idx, f_info in enumerate(page_fonts):
            xref = f_info[0]
            basefont = f_info[3]
            clean_name = re.sub(r"^[A-Z]{6}\+", "", basefont)

            try:
                fname, ext, ftype, buffer = doc.extract_font(xref)
                if buffer and len(buffer) > 0:
                    reg_name = f"emb_{xref}_{idx}"
                    try:
                        font_obj = fitz.Font(fontname=reg_name, fontbuffer=buffer)
                        page.insert_font(fontname=reg_name, fontbuffer=buffer)

                        val = (reg_name, font_obj)
                        font_registry[basefont] = val
                        font_registry[clean_name] = val
                        font_registry[clean_name.lower()] = val
                        font_registry[clean_name.lower().replace("-", "").replace(" ", "")] = val
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

    return font_registry


def _resolve_font(font_registry: dict[str, tuple[str, fitz.Font]], font_raw: str, is_bold: bool = False) -> tuple[str, fitz.Font]:
    """Resolve font name to registered embedded font, system font, or closest base-14 font."""
    clean = re.sub(r"^[A-Z]{6}\+", "", font_raw)
    key = clean.lower().replace("-", "").replace(" ", "")

    # 1. Check direct matches in embedded font registry
    for candidate in (font_raw, clean, clean.lower(), key):
        if candidate in font_registry:
            return font_registry[candidate]

    # 2. Check partial matches in embedded registry
    for reg_key, val in font_registry.items():
        if key in reg_key or reg_key in key:
            if is_bold and ("bold" in reg_key or "bd" in reg_key):
                return val
            elif not is_bold and "bold" not in reg_key:
                return val
    if font_registry:
        for reg_key, val in font_registry.items():
            if key in reg_key or reg_key in key:
                return val

    # 3. Check Windows system fonts if available
    from pathlib import Path
    win_fonts = Path("C:/Windows/Fonts")
    if win_fonts.exists():
        candidates = []
        if is_bold:
            candidates.extend([f"{key}bd.ttf", f"{key}b.ttf", f"{key}-bold.ttf", f"{key}bold.ttf"])
        candidates.extend([f"{key}.ttf", f"{key}.otf", f"{clean.lower()}.ttf"])
        for cand in candidates:
            p = win_fonts / cand
            if p.exists():
                try:
                    buf = p.read_bytes()
                    reg = f"sys_{key}_{'b' if is_bold else 'r'}"
                    font_obj = fitz.Font(fontname=reg, fontbuffer=buf)
                    return (reg, font_obj)
                except Exception:
                    pass

    # 4. Standard base-14 fallback
    b14 = _map_font(font_raw)
    if is_bold and b14 == "helv":
        b14 = "hebo"
    elif is_bold and b14 == "tiro":
        b14 = "tibo"
    return (b14, fitz.Font(b14))


def _wrap_to_pixel_width(text: str, font_obj: fitz.Font, font_size: float, max_w: float) -> list[str]:
    """Wrap words to fill line width precisely up to max_w points using real glyph metrics."""
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    curr: list[str] = []
    for w in words:
        trial = " ".join(curr + [w])
        try:
            width = font_obj.text_length(trial, fontsize=font_size)
        except Exception:
            width = len(trial) * font_size * 0.50
        if width <= max_w:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
                curr = [w]
            else:
                lines.append(w)
                curr = []
    if curr:
        lines.append(" ".join(curr))
    return lines


def _profile_section(page, headers: set[str], doc=None) -> dict | None:
    """Profile a resume section, extracting styles, exact margins, and embedded fonts.

    Returns None if section isn't found. Otherwise returns profile dict.
    """
    doc = doc or getattr(page, "parent", None)
    font_registry = _setup_page_fonts(doc, page)
    text_dict = page.get_text("dict")

    # ── Page-wide margins from existing ruling lines and text blocks ───
    page_width = page.rect.width
    ruling_xs = []
    try:
        for d in page.get_drawings():
            r = d.get("rect")
            if r and r.width > 50 and abs(r.height) <= 6.0:
                ruling_xs.append((r.x0, r.x1))
    except Exception:
        pass

    if ruling_xs:
        page_left_margin = min(rx[0] for rx in ruling_xs)
        page_right_margin = max(rx[1] for rx in ruling_xs)
    else:
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[4].strip()]
        page_left_margin = min((b[0] for b in text_blocks), default=36.0)
        page_right_margin = max((b[2] for b in text_blocks), default=page_width - 36.0)

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
        if norm in headers or (len(norm) < 40 and any(h in norm for h in headers)):
            header_idx = idx
            header_size = ln["max_size"]
            break

    if header_idx == -1:
        return None

    header_line = all_lines[header_idx]
    header_bbox = header_line["bbox"]
    y_top = header_bbox[1]

    # Profile header style
    header_span = next((s for s in header_line["spans"] if s.get("text", "").strip()), header_line["spans"][0])
    h_font_raw = header_span.get("font", "helv")
    h_font_name, h_font_obj = _resolve_font(font_registry, h_font_raw, is_bold=True)
    header_style = _SpanStyle(
        font_raw=h_font_raw,
        font_name=h_font_name,
        font_obj=h_font_obj,
        size=header_span.get("size", 12.0),
        color=header_span.get("color", 0),
        x=header_span["bbox"][0],
        flags=header_span.get("flags", 0),
    )

    # ── Find the next section header (boundary) ─────────────────────────
    y_bottom = page.rect.height - 20.0
    for idx in range(header_idx + 1, len(all_lines)):
        ln = all_lines[idx]
        norm = _normalize_header(ln["text"])
        if not norm:
            continue
        is_next = bool(_ANY_HEADER.match(ln["text"])) or (
            ln["max_size"] >= header_size - 1.0
            and len(ln["text"].split()) <= 4
            and ln["bbox"][1] > y_top + 15.0
        )
        if is_next:
            y_bottom = ln["bbox"][1] - 2.0
            break

    if y_bottom <= y_top + 10:
        return None

    # ── Collect all body lines ──────────────────────────────────────────
    body_lines = []
    for idx in range(header_idx + 1, len(all_lines)):
        ln = all_lines[idx]
        if ln["bbox"][1] >= y_bottom:
            break
        body_lines.append(ln)

    if not body_lines:
        return None

    all_body_spans = []
    for ln in body_lines:
        for s in ln["spans"]:
            if s.get("text", "").strip():
                all_body_spans.append(s)

    # Dominant body font + size
    font_size_counts: dict[tuple[str, float], int] = {}
    for s in all_body_spans:
        key = (s.get("font", ""), round(s.get("size", 10), 1))
        font_size_counts[key] = font_size_counts.get(key, 0) + len(s.get("text", ""))

    dominant_key = max(font_size_counts, key=font_size_counts.get) if font_size_counts else ("helv", 10.0)
    dominant_font, dominant_size = dominant_key

    body_spans = [s for s in all_body_spans
                  if s.get("font", "") == dominant_font and abs(s.get("size", 10) - dominant_size) < 0.5]
    body_color = body_spans[0].get("color", 0) if body_spans else 0

    body_font_name, body_font_obj = _resolve_font(font_registry, dominant_font, is_bold=False)
    body_style = _SpanStyle(
        font_raw=dominant_font,
        font_name=body_font_name,
        font_obj=body_font_obj,
        size=dominant_size,
        color=body_color,
        x=page_left_margin,
        flags=body_spans[0].get("flags", 0) if body_spans else 0,
    )

    # Sub-header style (bold / project title)
    subheader_spans = [s for s in all_body_spans
                       if s.get("font", "") != dominant_font or abs(s.get("size", 10) - dominant_size) >= 0.5
                       or (s.get("flags", 0) & (1 << 4) and not (body_spans[0].get("flags", 0) & (1 << 4)) if body_spans else False)]

    if not subheader_spans:
        for ln in body_lines:
            text = ln["text"]
            if ("|" in text or ":" in text) and len(text.split()) <= 15:
                for s in ln["spans"]:
                    if s.get("text", "").strip():
                        subheader_spans.append(s)

    if subheader_spans:
        sh_ref = subheader_spans[0]
        sh_font_raw = sh_ref.get("font", dominant_font)
        sh_font_name, sh_font_obj = _resolve_font(font_registry, sh_font_raw, is_bold=True)
        subheader_style = _SpanStyle(
            font_raw=sh_font_raw,
            font_name=sh_font_name,
            font_obj=sh_font_obj,
            size=sh_ref.get("size", dominant_size),
            color=sh_ref.get("color", body_color),
            x=page_left_margin,
            flags=sh_ref.get("flags", 0),
        )
    else:
        sh_font_name, sh_font_obj = _resolve_font(font_registry, dominant_font, is_bold=True)
        subheader_style = _SpanStyle(
            font_raw=dominant_font,
            font_name=sh_font_name,
            font_obj=sh_font_obj,
            size=dominant_size,
            color=body_color,
            x=page_left_margin,
            flags=body_spans[0].get("flags", 0) | (1 << 4) if body_spans else (1 << 4),
        )

    # ── Bullet character and positions ──────────────────────────────────
    bullet_char = "•"
    bullet_x = page_left_margin
    text_x = page_left_margin + 12.0

    for ln in body_lines:
        for s in ln["spans"]:
            txt = s.get("text", "").strip()
            if txt in ("•", "–", "-", "▪", "►", "●", "◦", "‣", "·", "*"):
                bullet_char = txt
                bullet_x = s["bbox"][0]
                spans_after = [sp for sp in ln["spans"] if sp.get("text", "").strip() and sp["bbox"][0] > s["bbox"][0] + 1]
                if spans_after:
                    text_x = min(sp["bbox"][0] for sp in spans_after)
                break
        else:
            continue
        break

    # Look across page if not found in section
    if bullet_x == page_left_margin and text_x == page_left_margin + 12.0:
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for s in line.get("spans", []):
                    txt = s.get("text", "").strip()
                    if txt in ("•", "–", "-", "▪", "►", "●", "◦", "‣", "·", "*"):
                        bullet_char = txt
                        bullet_x = s["bbox"][0]
                        spans_after = [sp for sp in line.get("spans", []) if sp.get("text", "").strip() and sp["bbox"][0] > s["bbox"][0] + 1]
                        if spans_after:
                            text_x = min(sp["bbox"][0] for sp in spans_after)
                        break
                else:
                    continue
                break

    # ── Line spacing ────────────────────────────────────────────────────
    body_ys = sorted(set(
        round(s["origin"][1], 1) for s in body_spans if "origin" in s
    ))
    if len(body_ys) >= 2:
        gaps = [body_ys[i+1] - body_ys[i] for i in range(len(body_ys) - 1) if body_ys[i+1] - body_ys[i] > 1]
        line_spacing = (sum(gaps) / len(gaps)) if gaps else dominant_size * 1.35
    else:
        line_spacing = dominant_size * 1.35

    first_baseline = body_ys[0] if body_ys else (header_bbox[3] + line_spacing)
    y_body_start = first_baseline

    return {
        "y_top": y_top,
        "y_body_start": y_body_start,
        "y_bottom": y_bottom,
        "left_margin": page_left_margin,
        "right_margin": page_right_margin,
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
    """Remove q BT...ET Q blocks whose TD y falls in [y_top, y_bottom] (PyMuPDF top-down coords)."""
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
    """Write replacement text line-by-line, filling margins precisely with true font metrics."""
    sub = profile["subheader_style"]
    body = profile["body_style"]
    bullet_char = profile["bullet_char"]
    bullet_x = profile["bullet_x"]
    text_x = profile["text_x"]
    line_spacing = profile["line_spacing"]

    left_margin = profile.get("left_margin", 36.0)
    right_margin = profile.get("right_margin", page.rect.width - 36.0)

    current_y = profile["y_body_start"]
    y_limit = profile["y_bottom"]

    sub_avail = max(100.0, right_margin - left_margin)
    body_avail = max(100.0, right_margin - left_margin)
    bullet_avail = max(100.0, right_margin - text_x)

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if current_y > y_limit:
            break

        if not stripped:
            current_y += line_spacing * 0.5
            continue

        # ── Sub-header (project title) ──────────────────────────────────
        is_subheader = stripped.startswith(("### ", "## "))
        is_pipe_title = ("|" in stripped and len(stripped.split()) <= 15 and not stripped.startswith(("- ", "• ", "* ", "– ")))

        if is_subheader or is_pipe_title:
            label = stripped.lstrip("#").strip().strip("*")
            wrapped_lines = _wrap_to_pixel_width(label, sub.font_obj, sub.size, sub_avail)
            for wrapped in wrapped_lines:
                if current_y > y_limit:
                    break
                page.insert_text(
                    (left_margin, current_y), wrapped,
                    fontsize=sub.size, fontname=sub.font, color=sub.color,
                )
                current_y += line_spacing
            continue

        # ── Bullet line ─────────────────────────────────────────────────
        is_bullet = stripped.startswith(("- ", "• ", "* ", "– ", "▪ "))
        if is_bullet:
            bullet_content = stripped[2:].strip()

            # Write bullet symbol
            page.insert_text(
                (bullet_x, current_y), bullet_char,
                fontsize=body.size, fontname=body.font, color=body.color,
            )

            # Wrap content precisely to the right margin using exact glyph metrics
            wrapped_lines = _wrap_to_pixel_width(bullet_content, body.font_obj, body.size, bullet_avail)
            for wrapped in wrapped_lines:
                if current_y > y_limit:
                    break
                page.insert_text(
                    (text_x, current_y), wrapped,
                    fontsize=body.size, fontname=body.font, color=body.color,
                )
                current_y += line_spacing
            continue

        # ── Regular text line (e.g. Skills: Languages: Python, ...) ─────
        wrapped_lines = _wrap_to_pixel_width(stripped, body.font_obj, body.size, body_avail)
        for wrapped in wrapped_lines:
            if current_y > y_limit:
                break
            page.insert_text(
                (left_margin, current_y), wrapped,
                fontsize=body.size, fontname=body.font, color=body.color,
            )
            current_y += line_spacing


# ── Public API ──────────────────────────────────────────────────────────────

def _find_section_y_bounds(page, headers: set[str]) -> tuple[float, float] | None:
    """Find (y_body_start, y_bottom) bounding the body of a section on a page."""
    text_dict = page.get_text("dict")
    all_lines = []
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
                "max_size": max_size,
            })

    if not all_lines:
        return None

    # 1. Find header line
    header_idx = -1
    header_size = 0.0
    for idx, ln in enumerate(all_lines):
        norm = _normalize_header(ln["text"])
        if not norm:
            continue
        if norm in headers or (len(norm) < 40 and any(h in norm for h in headers)):
            header_idx = idx
            header_size = ln["max_size"]
            break

    if header_idx == -1:
        return None

    header_line = all_lines[header_idx]
    y_top = header_line["bbox"][1]
    header_bottom = header_line["bbox"][3]

    # Detect horizontal ruling line under the header to ensure we NEVER crop it out
    line_bottom = header_bottom
    try:
        drawings = page.get_drawings()
        for d in drawings:
            r = d.get("rect")
            if r and abs(r.height) <= 6.0 and r.width > 30:
                # Ruling line sits directly beneath the header text
                if header_line["bbox"][1] <= r.y0 <= header_bottom + 25.0:
                    stroke_w = d.get("width", 1.0) or 1.0
                    r_bottom = max(r.y1, r.y0) + stroke_w
                    if r_bottom > line_bottom:
                        line_bottom = r_bottom
    except Exception:
        pass

    # Body starts strictly below the ruling line and below the header
    first_body_top = None
    if header_idx + 1 < len(all_lines):
        first_body_top = all_lines[header_idx + 1]["bbox"][1]

    if first_body_top is not None and first_body_top > line_bottom + 1.0:
        y_body_start = max(line_bottom + 1.0, (line_bottom + first_body_top) / 2.0)
    else:
        y_body_start = line_bottom + 2.0

    # 2. Find next section boundary
    y_bottom = page.rect.height - 20.0
    for idx in range(header_idx + 1, len(all_lines)):
        ln = all_lines[idx]
        norm = _normalize_header(ln["text"])
        if not norm:
            continue
        is_next = bool(_ANY_HEADER.match(ln["text"])) or (
            ln["max_size"] >= header_size - 1.0
            and len(ln["text"].split()) <= 4
            and ln["bbox"][1] > y_top + 15.0
        )
        if is_next:
            y_bottom = ln["bbox"][1] - 2.0
            break

    if y_bottom <= y_body_start:
        return None

    return (y_body_start, y_bottom)


def crop_sections_blank(original_pdf_bytes: bytes) -> bytes:
    """Crop out Skills and Projects sections in the original PDF and replace them with blank white.

    1. Saves all vector ruling lines under headers before blanking.
    2. Blanks out the target section bodies between header ruling line and next header.
    3. Re-draws the ruling lines to guarantee they are never removed or obscured.
    """
    if not original_pdf_bytes:
        return b""

    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        return original_pdf_bytes

    for page in doc:
        # Collect all horizontal ruling lines on the page so we can restore any affected ones
        saved_lines = []
        try:
            for d in page.get_drawings():
                r = d.get("rect")
                if r and abs(r.height) <= 6.0 and r.width > 30:
                    for it in d.get("items", []):
                        if it[0] == "l":
                            saved_lines.append({
                                "type": "line",
                                "p1": it[1],
                                "p2": it[2],
                                "color": d.get("color", (0, 0, 0)),
                                "width": d.get("width", 0.5),
                            })
                        elif it[0] == "re":
                            saved_lines.append({
                                "type": "rect",
                                "rect": it[1],
                                "color": d.get("fill") or d.get("color", (0, 0, 0)),
                            })
        except Exception:
            pass

        for headers in (SKILLS_HEADERS, PROJECTS_HEADERS):
            bounds = _find_section_y_bounds(page, headers)
            if not bounds:
                continue

            y_start, y_end = bounds
            rect = fitz.Rect(0, y_start, page.rect.width, y_end)

            # PyMuPDF native redaction purges body text/graphics
            try:
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
            except Exception:
                pass

            # Fill white to ensure clean background
            try:
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            except Exception:
                pass

        # Re-draw all saved ruling lines to ensure they remain 100% visible and untouched
        for item in saved_lines:
            try:
                if item["type"] == "line":
                    page.draw_line(item["p1"], item["p2"], color=item["color"], width=item["width"])
                elif item["type"] == "rect":
                    page.draw_rect(item["rect"], color=item["color"], fill=item["color"], width=0)
            except Exception:
                pass

    output_bytes = doc.tobytes()
    doc.close()
    return output_bytes



def rewrite_pdf_layout(
    original_pdf_bytes: bytes,
    rewritten_text: str,
) -> bytes:
    """Replace Skills and Projects sections in the original PDF in-place.

    1. Profiles each section to extract individual styles for headers, sub-headers, and body text.
    2. Blanks out the body text rectangle to white, preserving and restoring all ruling lines.
    3. Writes replacement text back into the blanked areas using the profiled styles.
    """
    if not original_pdf_bytes:
        return b""

    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        return original_pdf_bytes

    skills_text, projects_text = _split_rewritten_sections(rewritten_text)

    for page in doc:
        # Collect all horizontal ruling lines on the page so we can restore any affected ones
        saved_lines = []
        try:
            for d in page.get_drawings():
                r = d.get("rect")
                if r and abs(r.height) <= 6.0 and r.width > 30:
                    for it in d.get("items", []):
                        if it[0] == "l":
                            saved_lines.append({
                                "type": "line",
                                "p1": it[1],
                                "p2": it[2],
                                "color": d.get("color", (0, 0, 0)),
                                "width": d.get("width", 0.5),
                            })
                        elif it[0] == "re":
                            saved_lines.append({
                                "type": "rect",
                                "rect": it[1],
                                "color": d.get("fill") or d.get("color", (0, 0, 0)),
                            })
        except Exception:
            pass

        for headers, replacement_text in [
            (SKILLS_HEADERS, skills_text),
            (PROJECTS_HEADERS, projects_text),
        ]:
            if not replacement_text.strip():
                continue

            profile = _profile_section(page, headers, doc=doc)
            bounds = _find_section_y_bounds(page, headers)
            if not bounds:
                continue

            y_start, y_end = bounds
            rect = fitz.Rect(0, y_start, page.rect.width, y_end)

            # PyMuPDF native redaction purges body text/graphics
            try:
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
            except Exception:
                pass

            # Fill white to ensure clean background
            try:
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            except Exception:
                pass

            # Insert replacement text using profiled styles
            if profile:
                # Ensure profile body start matches safe bound
                profile["y_body_start"] = max(profile["y_body_start"], y_start + 2.0)
                profile["y_bottom"] = y_end
                _insert_section_text(page, profile, replacement_text)

        # Re-draw all saved ruling lines to ensure they remain 100% visible and untouched
        for item in saved_lines:
            try:
                if item["type"] == "line":
                    page.draw_line(item["p1"], item["p2"], color=item["color"], width=item["width"])
                elif item["type"] == "rect":
                    page.draw_rect(item["rect"], color=item["color"], fill=item["color"], width=0)
            except Exception:
                pass

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
