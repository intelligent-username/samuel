import re

ALIAS_MAP: dict[str, str] = {
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "k8": "kubernetes",
    "postgres": "postgresql",
    "pg": "postgresql",
    "psql": "postgresql",
    "js": "javascript",
    "ts": "typescript",
    "golang": "go",
    "gopher": "go",
    "py": "python",
    "python3": "python",
    "reactjs": "react",
    "react.js": "react",
    "nextjs": "next.js",
    "next": "next.js",
    "node": "node.js",
    "nodejs": "node.js",
    "tf": "terraform",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "amazon web services": "aws",
    "azure cloud": "azure",
    "ml": "machine learning",
    "ai": "machine learning",
    "ci": "ci/cd",
    "cd": "ci/cd",
    "cicd": "ci/cd",
    "gh actions": "github actions",
    "github action": "github actions",
}

STOPWORDS: set[str] = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "by", "at", "from", "as",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "will", "would", "should", "could", "must", "may", "might", "can", "shall",
    "you", "your", "yours", "we", "our", "ours", "us", "they", "their", "theirs", "them",
    "he", "she", "it", "its", "this", "that", "these", "those", "i", "me", "my", "mine",
    "him", "her", "his", "hers", "who", "whom", "whose", "which", "what", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "about", "into", "through", "during",
    "before", "after", "above", "below", "up", "down", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "if", "else", "while", "because", "until", "against", "between",
    "among", "per", "via", "etc", "eg", "ie", "including", "include", "includes", "like", "well", "also",
    "within", "without", "across", "along", "around", "seeking", "sought", "hiring", "hire",
    "join", "joins", "joining", "joined", "looking", "team", "teams", "company", "wanted", "want",
    "need", "needs", "needing", "required", "requirement", "requirements", "preferred", "prefer",
    "strong", "excellent", "good", "great", "ability", "able", "familiarity", "familiar", "knowledge",
    "experience", "experienced", "years", "year", "yrs", "yr", "months", "month", "degree", "background",
    "passion", "passionate", "opportunity", "opportunities", "role", "roles", "responsibility",
    "responsibilities", "qualification", "qualifications", "plus",
    "using", "used", "use",
}

_SINGLE_OK: set[str] = {"r", "c"}

_PHRASES: list[str] = sorted(
    [k for k in ALIAS_MAP if " " in k] + [v for v in ALIAS_MAP.values() if " " in v] + ["data engineering"],
    key=len,
    reverse=True,
)

_CHUNK_SPLIT_RE = re.compile(r"\s+and\s+|\s+or\s+|/|[&|;,]+")


def resolve_alias(token: str) -> str:
    t = token.strip().lower()
    return ALIAS_MAP.get(t, t)


def stem_token(token: str) -> str:
    """Stem English plural. Test: stem_token('microservices') == 'microservice'."""
    t = token.strip().lower()
    if not t or len(t) <= 3:
        return t
    if " " in t:
        return " ".join(stem_token(p) for p in t.split())
    if re.search(r"[^a-z0-9-]", t):
        return t
    if t in ALIAS_MAP.values():
        return t
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    if t.endswith(("sses", "xes", "zes", "ches", "shes")):
        return t[:-2]
    if t.endswith("s") and not t.endswith(("ss", "us")):
        return t[:-1]
    return t


def normalize_skill(s: str) -> str:
    if not s:
        return ""
    t = re.sub(r"[^a-z0-9+#./\s-]", " ", s.strip().lower())
    t = re.sub(r"\s+", " ", t).strip().rstrip(".").strip()
    if not t:
        return ""
    t = resolve_alias(t)
    if " " not in t:
        t = resolve_alias(stem_token(t))
    return t


def _is_numeric_noise(token: str) -> bool:
    """True for pure numbers/versions with no letters (5+, 2026, 33.33). Keeps s3, route53, oauth2."""
    t = token.strip().strip("+-.,%$").lower()
    if not t:
        return True
    if re.fullmatch(r"\d+(\.\d+)*", t):
        return True
    if re.fullmatch(r"\d+(st|nd|rd|th)", t):
        return True
    return re.search(r"[a-z]", t) is None


def _collect_phrases(cleaned: str, out: list[str], seen: set[str]) -> str:
    for phrase in _PHRASES:
        if phrase in cleaned:
            norm = normalize_skill(phrase)
            if norm and norm not in seen:
                seen.add(norm)
                out.append(norm)
            cleaned = cleaned.replace(phrase, " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def _add_token(part: str, out: list[str], seen: set[str]) -> None:
    token = part.strip().rstrip(".").strip()
    if not token or token in STOPWORDS:
        return
    if _is_numeric_noise(token) and token not in ALIAS_MAP:
        return
    if len(token) < 2 and token not in ALIAS_MAP and token not in _SINGLE_OK:
        return
    norm = normalize_skill(token)
    if not norm or norm in STOPWORDS or norm in seen:
        return
    if len(norm) < 2 and norm not in _SINGLE_OK:
        return
    seen.add(norm)
    out.append(norm)


def _emit_chunk(chunk: str, out: list[str], seen: set[str]) -> None:
    words = [w.strip(".-").strip() for w in chunk.split(" ")]
    words = [w for w in words if w and not _is_numeric_noise(w)]
    words = [w for w in words if len(w) >= 2 or w in ALIAS_MAP or w in _SINGLE_OK]
    while words and words[0] in STOPWORDS:
        words.pop(0)
    while words and words[-1] in STOPWORDS:
        words.pop()
    if not words:
        return
    whole = " ".join(words)
    if whole in STOPWORDS:
        return
    canon = resolve_alias(whole)
    if canon != whole:
        _add_token(canon, out, seen)
        return
    if len(words) <= 3:
        _add_token(whole, out, seen)
        return
    for w in words:
        _add_token(w, out, seen)


def normalize_list(items: list[str] | None) -> list[str]:
    """Normalize phrase list to atomic skills. Test: normalize_list(['5+ years Python']) == ['python']."""
    if not items:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        if not raw or not str(raw).strip():
            continue
        cleaned = re.sub(r"[^a-z0-9+#./\s-]", " ", str(raw).strip().lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            continue
        cleaned = re.sub(r"\bci/cd\b", "cicd", cleaned)
        cleaned = _collect_phrases(cleaned, out, seen)
        if not cleaned:
            continue
        for chunk in _CHUNK_SPLIT_RE.split(cleaned):
            if chunk.strip():
                _emit_chunk(chunk, out, seen)
    return out
