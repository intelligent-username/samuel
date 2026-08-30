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
    """Extract text along with visual metadata (spans with bbox, size, font, color, page dimensions)."""
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
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        page_dict["spans"].append({
                            "text": span.get("text", ""),
                            "bbox": span.get("bbox"),  # (x0, y0, x1, y1)
                            "size": span.get("size", 10),
                            "font": span.get("font", "helv"),
                            "color": span.get("color", 0),
                            "flags": span.get("flags", 0),
                        })
        pages_layout.append(page_dict)
    doc.close()
    return {"pages": pages_layout}


def rewrite_pdf_layout(
    original_pdf_bytes: bytes,
    rewritten_text: str,
) -> bytes:
    """Naive spatial writer: redacts target sections on original PDF and writes rewritten text in place."""
    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        return original_pdf_bytes

    page = doc[0]
    
    # 1. Locate bounding area for skills/projects by scanning words/spans
    text_dict = page.get_text("dict")
    skills_bbox = None
    projects_bbox = None
    last_bbox = None
    base_font_size = 10.0
    
    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    t = span.get("text", "").strip().lower()
                    if any(h in t for h in SKILLS_HEADERS) and not skills_bbox:
                        skills_bbox = span.get("bbox")
                    if any(h in t for h in PROJECTS_HEADERS) and not projects_bbox:
                        projects_bbox = span.get("bbox")
                    last_bbox = span.get("bbox")
                    if span.get("size"):
                        base_font_size = span.get("size")

    # Determine redaction/replacement zone
    y_start = (skills_bbox or projects_bbox or (50, 200, 500, 220))[1]
    y_end = (last_bbox or (50, 700, 500, 750))[3] + 40
    
    # Bounding rectangle for the rewrite zone
    zone_rect = fitz.Rect(page.rect.x0 + 40, y_start, page.rect.x1 - 40, min(y_end, page.rect.y1 - 40))
    
    # Redact the old content area (white-out)
    page.draw_rect(zone_rect, color=None, fill=(1, 1, 1), overlay=True)
    
    # 2. Write new text into the exact location
    clean_text = rewritten_text.replace("## ", "").replace("### ", "").replace("# ", "")
    page.insert_textbox(
        zone_rect,
        clean_text,
        fontsize=base_font_size,
        fontname="helv",
        color=(0.1, 0.1, 0.1),
        align=fitz.TEXT_ALIGN_LEFT,
    )
    
    output_bytes = doc.tobytes()
    doc.close()
    return output_bytes


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
