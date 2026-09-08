from app.constants import ANY_HEADER_RE
from app.utils.pdf_fonts import (
    SpanStyle,
    resolve_font,
    setup_page_fonts,
    wrap_to_pixel_width,
)


def normalize_header(line: str) -> str:
    """Normalize a header line: strip whitespace, trailing colons, collapse spaces, lowercase."""
    s = line.strip()
    s = s.rstrip(":").strip()
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def collect_ruling_lines(page) -> list[dict]:
    """Collect all horizontal ruling lines on the page to restore after redaction."""
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
    return saved_lines


def restore_ruling_lines(page, saved_lines: list[dict]) -> None:
    """Re-draw all saved ruling lines to ensure they remain 100% visible and untouched."""
    for item in saved_lines:
        try:
            if item["type"] == "line":
                page.draw_line(item["p1"], item["p2"], color=item["color"], width=item["width"])
            elif item["type"] == "rect":
                page.draw_rect(item["rect"], color=item["color"], fill=item["color"], width=0)
        except Exception:
            pass


def profile_section(
    page,
    headers: set[str],
    doc=None,
    normalize_fn=normalize_header,
    any_header_re=ANY_HEADER_RE,
) -> dict | None:
    """Profile a resume section, extracting styles, exact margins, ruling bounds, and embedded fonts."""
    doc = doc or getattr(page, "parent", None)
    font_registry = setup_page_fonts(doc, page)
    text_dict = page.get_text("dict")

    # 1. Margins from existing ruling lines or text blocks
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

    # 2. Flatten all lines with their spans
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

    # 3. Find the header line
    header_idx = -1
    header_size = 0.0
    for idx, ln in enumerate(all_lines):
        norm = normalize_fn(ln["text"])
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
    header_bottom = header_bbox[3]

    # Detect horizontal ruling line directly below header to never crop it out
    line_bottom = header_bottom
    try:
        for d in page.get_drawings():
            r = d.get("rect")
            if r and abs(r.height) <= 6.0 and r.width > 30:
                if header_line["bbox"][1] <= r.y0 <= header_bottom + 25.0:
                    stroke_w = d.get("width", 1.0) or 1.0
                    r_bottom = max(r.y1, r.y0) + stroke_w
                    if r_bottom > line_bottom:
                        line_bottom = r_bottom
    except Exception:
        pass

    first_body_top = None
    if header_idx + 1 < len(all_lines):
        first_body_top = all_lines[header_idx + 1]["bbox"][1]

    if first_body_top is not None and first_body_top > line_bottom + 1.0:
        y_clear_start = max(line_bottom + 1.0, (line_bottom + first_body_top) / 2.0)
    else:
        y_clear_start = line_bottom + 2.0

    # 4. Profile header style
    header_span = next((s for s in header_line["spans"] if s.get("text", "").strip()), header_line["spans"][0])
    h_font_raw = header_span.get("font", "helv")
    h_font_name, h_font_obj = resolve_font(font_registry, h_font_raw, is_bold=True)
    header_style = SpanStyle(
        font_raw=h_font_raw,
        font_name=h_font_name,
        font_obj=h_font_obj,
        size=header_span.get("size", 12.0),
        color=header_span.get("color", 0),
        x=header_span["bbox"][0],
        flags=header_span.get("flags", 0),
    )

    # 5. Find the next section boundary
    y_bottom = page.rect.height - 20.0
    for idx in range(header_idx + 1, len(all_lines)):
        ln = all_lines[idx]
        norm = normalize_fn(ln["text"])
        if not norm:
            continue
        is_next = bool(any_header_re.match(ln["text"])) or (
            ln["max_size"] >= header_size - 1.0
            and len(ln["text"].split()) <= 4
            and ln["bbox"][1] > y_top + 15.0
        )
        if is_next:
            y_bottom = ln["bbox"][1] - 2.0
            break

    if y_bottom <= y_clear_start:
        return None

    # 6. Collect body lines
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

    body_spans = [
        s for s in all_body_spans
        if s.get("font", "") == dominant_font and abs(s.get("size", 10) - dominant_size) < 0.5
    ]
    body_color = body_spans[0].get("color", 0) if body_spans else 0

    body_font_name, body_font_obj = resolve_font(font_registry, dominant_font, is_bold=False)
    body_style = SpanStyle(
        font_raw=dominant_font,
        font_name=body_font_name,
        font_obj=body_font_obj,
        size=dominant_size,
        color=body_color,
        x=page_left_margin,
        flags=body_spans[0].get("flags", 0) if body_spans else 0,
    )

    # Sub-header style (project title)
    subheader_spans = [
        s for s in all_body_spans
        if s.get("font", "") != dominant_font
        or abs(s.get("size", 10) - dominant_size) >= 0.5
        or (s.get("flags", 0) & (1 << 4) and not (body_spans[0].get("flags", 0) & (1 << 4)) if body_spans else False)
    ]

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
        sh_font_name, sh_font_obj = resolve_font(font_registry, sh_font_raw, is_bold=True)
        subheader_style = SpanStyle(
            font_raw=sh_font_raw,
            font_name=sh_font_name,
            font_obj=sh_font_obj,
            size=sh_ref.get("size", dominant_size),
            color=sh_ref.get("color", body_color),
            x=page_left_margin,
            flags=sh_ref.get("flags", 0),
        )
    else:
        sh_font_name, sh_font_obj = resolve_font(font_registry, dominant_font, is_bold=True)
        subheader_style = SpanStyle(
            font_raw=dominant_font,
            font_name=sh_font_name,
            font_obj=sh_font_obj,
            size=dominant_size,
            color=body_color,
            x=page_left_margin,
            flags=body_spans[0].get("flags", 0) | (1 << 4) if body_spans else (1 << 4),
        )

    # Bullet character and indentation positions
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

    # Line spacing
    body_ys = sorted(set(
        round(s["origin"][1], 1) for s in body_spans if "origin" in s
    ))
    if len(body_ys) >= 2:
        gaps = [body_ys[i+1] - body_ys[i] for i in range(len(body_ys) - 1) if body_ys[i+1] - body_ys[i] > 1]
        line_spacing = (sum(gaps) / len(gaps)) if gaps else dominant_size * 1.35
    else:
        line_spacing = dominant_size * 1.35

    first_baseline = body_ys[0] if body_ys else (header_bottom + line_spacing)
    y_body_start = max(first_baseline, y_clear_start + 2.0)

    return {
        "y_top": y_top,
        "y_clear_start": y_clear_start,
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


def insert_section_text(page, profile: dict, text: str) -> None:
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

        # Sub-header (project title)
        is_subheader = stripped.startswith(("### ", "## "))
        is_pipe_title = ("|" in stripped and len(stripped.split()) <= 15 and not stripped.startswith(("- ", "• ", "* ", "– ")))

        if is_subheader or is_pipe_title:
            label = stripped.lstrip("#").strip().strip("*")
            wrapped_lines = wrap_to_pixel_width(label, sub.font_obj, sub.size, sub_avail)
            for wrapped in wrapped_lines:
                if current_y > y_limit:
                    break
                page.insert_text(
                    (left_margin, current_y), wrapped,
                    fontsize=sub.size, fontname=sub.font, color=sub.color,
                )
                current_y += line_spacing
            continue

        # Bullet line
        is_bullet = stripped.startswith(("- ", "• ", "* ", "– ", "▪ "))
        if is_bullet:
            bullet_content = stripped[2:].strip()

            page.insert_text(
                (bullet_x, current_y), bullet_char,
                fontsize=body.size, fontname=body.font, color=body.color,
            )

            wrapped_lines = wrap_to_pixel_width(bullet_content, body.font_obj, body.size, bullet_avail)
            for wrapped in wrapped_lines:
                if current_y > y_limit:
                    break
                page.insert_text(
                    (text_x, current_y), wrapped,
                    fontsize=body.size, fontname=body.font, color=body.color,
                )
                current_y += line_spacing
            continue

        # Regular text line (e.g. Skills: Languages: Python, ...)
        wrapped_lines = wrap_to_pixel_width(stripped, body.font_obj, body.size, body_avail)
        for wrapped in wrapped_lines:
            if current_y > y_limit:
                break
            page.insert_text(
                (left_margin, current_y), wrapped,
                fontsize=body.size, fontname=body.font, color=body.color,
            )
            current_y += line_spacing
