import re

ALIAS_MAP: dict[str, str] = {
    "k8s": "kubernetes",
    "k8s.": "kubernetes",
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
    "gcp": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "aws": "aws",
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
}

_PHRASES: list[str] = sorted(
    [k for k in ALIAS_MAP if " " in k] + [v for v in ALIAS_MAP.values() if " " in v] + ["data engineering"],
    key=len,
    reverse=True,
)


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


def _collect_phrases(cleaned: str, out: list[str], seen: set[str]) -> str:
    for phrase in _PHRASES:
        if phrase in cleaned:
            norm = normalize_skill(phrase)
            if norm and norm not in seen:
                seen.add(norm)
                out.append(norm)
            cleaned = cleaned.replace(phrase, " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def _append_token(part: str, out: list[str], seen: set[str]) -> None:
    token = part.strip().rstrip(".").strip()
    if not token or token in STOPWORDS:
        return
    if token not in ALIAS_MAP and re.search(r"\d", token):
        return
    if len(token) < 2 and token not in ALIAS_MAP:
        return
    norm = normalize_skill(token)
    if not norm or norm in STOPWORDS or norm in seen or len(norm) < 2:
        return
    seen.add(norm)
    out.append(norm)


def normalize_list(items: list[str] | None) -> list[str]:
    """Normalize phrase list to atomic skills. Test: normalize_list(['5+ years Python']) == ['python']."""
    if not items:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        if not raw or not raw.strip():
            continue
        cleaned = re.sub(r"[^a-z0-9+#./\s-]", " ", raw.strip().lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = _collect_phrases(cleaned, out, seen)
        for part in cleaned.split(" "):
            _append_token(part, out, seen)
    return out
