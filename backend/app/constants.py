import re

# Canonical header sets for resume section detection
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

# Regex pattern matching any section boundary header line
ANY_HEADER_RE = re.compile(
    r"^(?:"
    r"experience|work\s+experience|employment|work\s+history|"
    r"education|certifications?|awards?|publications?|languages?|"
    r"summary|objective|about|contact|references?|"
    r"skills?|technical\s+skills|technical\s+expertise|core\s+competencies|key\s+skills|"
    r"projects?|personal\s+projects|selected\s+projects|side\s+projects|open[-\s]?source"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

_ANY_HEADER = ANY_HEADER_RE
