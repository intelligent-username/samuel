import re

import fitz  # PyMuPDF

from app.constants import (
    ANY_HEADER_RE,
    PROJECTS_HEADERS,
    SKILLS_HEADERS,
    _ANY_HEADER,
)
from app.utils.pdf_layout import (
    collect_ruling_lines,
    insert_section_text,
    normalize_header,
    profile_section,
    restore_ruling_lines,
)

_normalize_header = normalize_header


def extract_text_from_pdf(content: bytes) -> str:
    """Extract all text from a PDF document."""
    doc = fitz.open(stream=content, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def rewrite_pdf_layout(
    original_pdf_bytes: bytes,
    rewritten_text: str,
) -> bytes:
    """Replace Skills and Projects sections in the original PDF in-place.

    1. Preserves horizontal ruling lines across the page.
    2. Profiles section styles (headers, subheaders, body text, bullets).
    3. Blanks out the target section bodies via PyMuPDF native redaction.
    4. Writes replacement text back into the blanked areas using profiled typography.
    5. Re-draws preserved ruling lines.
    """
    if not original_pdf_bytes:
        return b""

    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        return original_pdf_bytes

    skills_text, projects_text = _split_rewritten_sections(rewritten_text)

    for page in doc:
        saved_lines = collect_ruling_lines(page)

        for headers, replacement_text in [
            (SKILLS_HEADERS, skills_text),
            (PROJECTS_HEADERS, projects_text),
        ]:
            if not replacement_text.strip():
                continue

            profile = profile_section(page, headers, doc=doc)
            if not profile:
                continue

            rect = fitz.Rect(0, profile["y_clear_start"], page.rect.width, profile["y_bottom"])

            try:
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
            except Exception:
                pass

            try:
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            except Exception:
                pass

            insert_section_text(page, profile, replacement_text)

        restore_ruling_lines(page, saved_lines)

    output_bytes = doc.tobytes(garbage=4, deflate=True, clean=True)
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

        is_skills_header = norm in SKILLS_HEADERS or (len(norm) < 30 and any(h in norm for h in SKILLS_HEADERS))
        is_projects_header = norm in PROJECTS_HEADERS or (len(norm) < 30 and any(h in norm for h in PROJECTS_HEADERS))
        is_other_header = bool(_ANY_HEADER.match(stripped)) and not is_skills_header and not is_projects_header

        if is_skills_header:
            capturing_skills = True
            capturing_projects = False
            output_lines.append(line)
            output_lines.append("")
            output_lines.append(new_skills.strip())
            output_lines.append("")
            skills_inserted = True
            continue

        if is_projects_header:
            capturing_projects = True
            capturing_skills = False
            output_lines.append(line)
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
            continue

        output_lines.append(line)

    if not skills_inserted and new_skills.strip():
        output_lines.append("\n\n## Skills\n" + new_skills.strip())
    if not projects_inserted and new_projects.strip():
        output_lines.append("\n\n## Projects\n" + new_projects.strip())

    return "\n".join(output_lines).strip()


def _split_rewritten_sections(text: str) -> tuple[str, str]:
    """Split '## Skills\\n...\\n## Projects\\n...' into (skills_text, projects_text)."""
    skills = ""
    projects = ""

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

    if not skills_text and not projects_text:
        fallback = text.strip()[:4000]
        return {
            "skills": fallback,
            "projects": "",
            "_fallback": True,
            "_warning": "Could not detect Skills/Projects sections — using full resume text",
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
            if _ANY_HEADER.match(stripped) or (stripped.isupper() and len(stripped) > 3 and len(stripped.split()) <= 4):
                break
            result.append(line)

    return "\n".join(result).strip()
