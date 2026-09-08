from app.utils.pdf_fonts import wrap_to_pixel_width


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
