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


def extract_sections(text: str) -> dict[str, str]:
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
