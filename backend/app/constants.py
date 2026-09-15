import re

# Canonical header sets for resume section detection
SKILLS_HEADERS = {
    "skill", "skills",
    "technical skills", "technical expertise",
    "core competencies", "core skills",
    "key skills", "skills & tools", "skills & abilities",
    "technologies", "technical proficiencies", "programming skills",
    "skills summary",
    "tech stack", "technology stack", "technical stack", "stack",
    "expertise", "areas of expertise", "core expertise",
    "tooling", "tools",
    "what i know",
}

PROJECTS_HEADERS = {
    "project", "projects",
    "personal projects", "selected projects",
    "side projects", "academic projects", "key projects",
    "open source", "open-source", "project experience",
    "notable projects", "recent projects",
    "portfolio",
}

# Lag bounds (centralized per lag-08; no behavior change, same values)
JD_MAX_CHARS = 24000
ATS_SCORE_MIN = 70
ATS_SCORE_MAX = 100
ATS_MIN_ITERATIONS = 5
ATS_MAX_ITERATIONS_CAP = 7
LLM_OVERALL_TIMEOUT_S = 90
SSE_BACKOFF_BASE_MS = 1000
SSE_BACKOFF_MAX_MS = 30000
SSE_ZOMBIE_POLL_MS = 2500
COPIED_TOAST_MS = 2000
RENAME_FOCUS_MS = 50
JD_PERSIST_DEBOUNCE_MS = 500

# Regex pattern matching any section boundary header line
ANY_HEADER_RE = re.compile(
    r"^(?:"
    r"experience|work\s+experience|professional\s+experience|"
    r"employment(?:\s+history)?|work\s+history|"
    r"education|certifications?|awards?|publications?|languages?|"
    r"summary|objective|about|contact|references?|"
    r"skills?|technical\s+skills|technical\s+expertise|"
    r"core\s+(?:competencies|skills|expertise)|key\s+skills|"
    r"skills\s*(?:&|and)\s*(?:tools|abilities)|technologies|"
    r"technical\s+proficiencies|programming\s+skills|skills\s+summary|"
    r"tech\s+stack|technology\s+stack|technical\s+stack|stack|"
    r"expertise|areas\s+of\s+expertise|tooling|tools|what\s+i\s+know|"
    r"projects?|personal\s+projects|selected\s+projects|side\s+projects|"
    r"academic\s+projects|key\s+projects|notable\s+projects|"
    r"recent\s+projects|project\s+experience|portfolio|open[-\s]?source"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

_ANY_HEADER = ANY_HEADER_RE
