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


# ── Section boundary detection & in-place layout rewriting ──────────────────

def _locate_section_region(page, headers: set[str]) -> dict | None:
    """Find the bounding box, body font size, and text coordinates for a section on page."""
    text_dict = page.get_text("dict")
    all_lines = []

    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:
            for line in block.get("lines", []):
                line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                max_size = max((span.get("size", 0) for span in line.get("spans", [])), default=0)
                all_lines.append({
                    "text": line_text,
                    "bbox": line.get("bbox"),
                    "spans": line.get("spans", []),
                    "max_size": max_size,
                })

    target_line_idx = -1
    target_line_rect = None
    header_size = 12.0

    for idx, line in enumerate(all_lines):
        norm = _normalize_header(line["text"])
        if not norm:
            continue
        # Direct match or substring in short line (< 35 chars)
        if norm in headers or (len(norm) < 35 and any(h in norm for h in headers)):
            target_line_idx = idx
            target_line_rect = line["bbox"]
            header_size = line["max_size"]
            break

    if target_line_idx == -1 or not target_line_rect:
        return None

    y_top = target_line_rect[3] + 2  # start immediately below header

    # Find the next section boundary
    y_bottom = page.rect.height - 36
    for idx in range(target_line_idx + 1, len(all_lines)):
        line = all_lines[idx]
        norm = _normalize_header(line["text"])
        if not norm:
            continue
        # If line matches any section header or looks like a major header
        is_next_header = bool(_ANY_HEADER.match(line["text"])) or (
            line["max_size"] >= header_size - 1.0 and len(line["text"].split()) <= 4 and line["bbox"][1] > y_top + 10
        )
        if is_next_header:
            y_bottom = line["bbox"][1] - 4
            break

    if y_bottom <= y_top + 10:
        return None

    # Sample body font size from spans currently in that y-range
    body_sizes = []
    x_coords = []
    for idx in range(target_line_idx + 1, len(all_lines)):
        line = all_lines[idx]
        if line["bbox"][1] >= y_bottom:
            break
        for span in line["spans"]:
            if span.get("text", "").strip():
                body_sizes.append(span.get("size", 10.0))
                x_coords.append(span["bbox"][0])

    body_size = (sum(body_sizes) / len(body_sizes)) if body_sizes else 9.5
    body_size = max(8.5, min(11.5, body_size))

    x_left = min(x_coords) if x_coords else (page.rect.x0 + 36)
    x_right = page.rect.width - 36

    content_rect = fitz.Rect(max(page.rect.x0 + 20, x_left - 4), y_top, min(page.rect.width - 20, x_right + 4), y_bottom)
    return {
        "content_rect": content_rect,
        "body_size": body_size,
    }


def _format_for_pdf_insert(text: str) -> str:
    """Format markdown text for clean PDF insertion (normalize bullets, indents, clean dashes)."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        # Convert markdown headers inside section
        if stripped.startswith("### "):
            lines.append("\n" + stripped[4:].strip())
        elif stripped.startswith("## ") or stripped.startswith("# "):
            lines.append("\n" + stripped.lstrip("# ").strip())
        elif stripped.startswith(("- ", "* ", "• ")):
            bullet_content = stripped[2:].strip()
            lines.append(f"  •  {bullet_content}")
        else:
            lines.append(stripped)
    return "\n".join(lines).strip()


# ── Public API ──────────────────────────────────────────────────────────────

def rewrite_pdf_layout(
    original_pdf_bytes: bytes,
    rewritten_text: str,
) -> bytes:
    """Replace Skills and Projects sections in the original PDF with rewritten text.

    Preserves the entire original PDF (header, contact info, experience, education,
    styling, margins, lines) and edits ONLY the Skills and Projects content in place.
    """
    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        return original_pdf_bytes

    skills_text, projects_text = _split_rewritten_sections(rewritten_text)

    sections_to_replace = [
        (SKILLS_HEADERS, skills_text),
        (PROJECTS_HEADERS, projects_text),
    ]

    for headers, replacement_text in sections_to_replace:
        if not replacement_text.strip():
            continue

        for page in doc:
            region = _locate_section_region(page, headers)
            if not region:
                continue

            rect = region["content_rect"]
            body_size = region.get("body_size", 10.0)

            # 1. Redact the old content area (removes all text and paths, fills background with white)
            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

            # 2. Format the replacement text cleanly
            formatted_text = _format_for_pdf_insert(replacement_text)

            # 3. Insert into the exact bounding box at the original font size
            # If text is slightly long, shrink by 0.5pt until it fits cleanly without overflow
            font_size = body_size
            for _ in range(6):
                rc = page.insert_textbox(
                    rect,
                    formatted_text,
                    fontsize=font_size,
                    fontname="helv",
                    color=(0.1, 0.1, 0.1),
                    align=fitz.TEXT_ALIGN_LEFT,
                )
                if rc >= 0:
                    break
                font_size -= 0.5

            break  # section found and replaced, advance to next section

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
