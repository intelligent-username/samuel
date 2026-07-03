import re

import fitz  # PyMuPDF

# Any uppercase/title-case line that could be the next section boundary
_ANY_HEADER = re.compile(
    r"^(?:experience|education|work|employment|certifications?|awards?|publications?|languages?|summary|objective|about|contact|references?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def extract_text_from_pdf(content: bytes) -> str:
    """Extract all text from a PDF document."""
    doc = fitz.open(stream=content, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def extract_sections(text: str) -> dict[str, str]:
    """Return {'skills': ..., 'projects': ...} pulled from resume text."""
    skills_text = _extract_section(text, {"skill", "skills", "technical skills", "core competencies"})
    projects_text = _extract_section(text, {"project", "projects", "personal projects", "side projects", "open source", "open-source"})
    return {"skills": skills_text, "projects": projects_text}


def _extract_section(text: str, target_names: set[str]) -> str:
    """Extract the content of a named section from resume text."""
    lines = text.splitlines()
    result: list[str] = []
    capturing = False

    for line in lines:
        stripped = line.strip()
        normalized = stripped.lower().rstrip(":")

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
