import difflib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.utils.ats_normalize import normalize_skill, stem_token

_DEFAULT_WEIGHTS: dict[str, float] = {
    "keyword_coverage": 0.7,
    "section_presence": 0.2,
    "format_hygiene": 0.1,
}
_WEIGHTS_PATH = Path(__file__).resolve().parents[1] / "config" / "ats_weights.json"
_FUZZY_CUTOFF = 0.8
_PASS_THRESHOLD = 70.0


def _load_weights() -> dict[str, float]:
    weights = dict(_DEFAULT_WEIGHTS)
    try:
        raw = json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return weights
    if not isinstance(raw, dict):
        return weights
    for key in weights:
        try:
            val = float(raw.get(key, weights[key]))
        except (TypeError, ValueError):
            continue
        if 0.0 <= val <= 1.0:
            weights[key] = val
    return weights


def _exact_match(text_lower: str, kw_clean: str) -> bool:
    escaped = re.escape(kw_clean.lower())
    if re.search(r"[+#.]", kw_clean):
        pattern = rf"(?:^|[\s,;|/()]){escaped}(?:$|[\s,;|/()])"
    else:
        pattern = rf"\b{escaped}\b"
    return re.search(pattern, text_lower) is not None


def _tokenize_resume(resume_text: str) -> tuple[set[str], str]:
    raw_tokens = re.findall(r"[a-z0-9+#./-]{2,}", resume_text.lower())
    normed: set[str] = set()
    for tok in raw_tokens:
        norm = normalize_skill(tok)
        if norm:
            normed.add(norm)
    norm_text = " ".join(sorted(normed))
    return normed, norm_text


def _fuzzy_credit(target_norm: str, tokens: set[str]) -> float:
    best = 0.0
    for tok in sorted(tokens):
        ratio = difflib.SequenceMatcher(None, target_norm, tok).ratio()
        if ratio > best:
            best = ratio
    if best >= 0.92:
        return 0.8
    if best >= 0.85:
        return 0.7
    if best >= _FUZZY_CUTOFF:
        return 0.6
    return 0.0


def _credit_for_target(
    kw_clean: str,
    target_norm: str,
    text_lower: str,
    tokens: set[str],
    norm_text: str,
) -> float:
    if _exact_match(text_lower, kw_clean):
        return 1.0
    if not target_norm:
        return 0.0
    if target_norm in tokens or target_norm in norm_text:
        return 0.9
    stemmed = stem_token(target_norm)
    for tok in tokens:
        if stem_token(tok) == stemmed:
            return 0.9
    return _fuzzy_credit(target_norm, tokens)


@dataclass
class ATSContext:
    """Contextual data passed to ATS criteria for evaluation."""

    keywords: list[str] = field(default_factory=list)
    hard_requirements: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    job_description_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ATSContext":
        if not data:
            return cls()
        return cls(
            keywords=list(data.get("keywords") or []),
            hard_requirements=list(data.get("hard_requirements") or []),
            preferred_skills=list(data.get("preferred_skills") or []),
            job_description_text=str(data.get("job_description_text") or ""),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class CriterionResult:
    """Evaluation result for an individual ATS criterion."""

    criterion_name: str
    score: float  # 0.0 to 100.0
    passed: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def _targets_from_context(context: ATSContext) -> list[str]:
    targets = list(dict.fromkeys(context.keywords or []))
    if not targets and context.hard_requirements:
        combined = list(context.hard_requirements) + list(context.preferred_skills or [])
        targets = list(dict.fromkeys(combined))
    return [t for t in (k.strip() for k in targets) if t]


class ATSCriterion(ABC):
    """Abstract base class for deterministic ATS ranking criteria."""

    name: str = "base_criterion"
    weight: float = 1.0

    @abstractmethod
    def evaluate(self, resume_text: str, context: ATSContext) -> CriterionResult:
        """Evaluate resume text against this criterion."""
        pass


class KeywordMatchCriterion(ATSCriterion):
    """Keyword coverage with partial credit for equivalents."""

    name: str = "keyword_coverage"
    weight: float = 1.0

    def evaluate(self, resume_text: str, context: ATSContext) -> CriterionResult:
        targets = _targets_from_context(context)
        if not targets:
            return CriterionResult(
                criterion_name=self.name,
                score=100.0,
                passed=True,
                details={"matched": [], "missing": [], "total_keywords": 0},
            )
        return self._score_targets(resume_text, context, targets)

    def _score_targets(
        self, resume_text: str, context: ATSContext, targets: list[str]
    ) -> CriterionResult:
        text_lower = resume_text.lower()
        tokens, norm_text = _tokenize_resume(resume_text)
        credits: dict[str, float] = {}
        matched: list[str] = []
        missing: list[str] = []
        for kw in targets:
            credit = _credit_for_target(kw, normalize_skill(kw), text_lower, tokens, norm_text)
            credits[kw] = credit
            (matched if credit > 0.0 else missing).append(kw)
        return self._build_result(context, targets, matched, missing, credits)

    def _build_result(
        self,
        context: ATSContext,
        targets: list[str],
        matched: list[str],
        missing: list[str],
        credits: dict[str, float],
    ) -> CriterionResult:
        total = len(targets)
        avg = sum(credits.values()) / total if total else 1.0
        score = round(avg * 100.0, 1)
        hard_lower = {h.strip().lower() for h in context.hard_requirements if h.strip()}
        issues = [f"Missing core required skill: '{m}'" for m in missing if m.lower() in hard_lower]
        warnings = [
            f"Missing recommended keyword: '{m}'" for m in missing if m.lower() not in hard_lower
        ]
        return CriterionResult(
            criterion_name=self.name,
            score=score,
            passed=score >= _PASS_THRESHOLD,
            issues=issues,
            warnings=warnings,
            details={
                "matched": matched,
                "missing": missing,
                "match_count": len(matched),
                "total_count": total,
                "total_keywords": total,
                "credits": credits,
            },
        )


class SectionPresenceCriterion(ATSCriterion):
    """Check standard resume sections exist."""

    name: str = "section_presence"
    weight: float = 0.2

    _patterns: dict[str, str] = {
        "skills": r"(skills?|tech stack|stack|expertise|tooling|what i know)",
        "projects": r"(projects?|portfolio|selected work)",
        "experience": r"(experience|employment|work history|professional experience)",
        "education": r"(education|academic|degree|university|college|school)",
    }

    def evaluate(self, resume_text: str, context: ATSContext) -> CriterionResult:
        present = [s for s, pat in self._patterns.items() if re.search(pat, resume_text, re.I)]
        missing = [s for s in self._patterns if s not in present]
        score = round(len(present) / len(self._patterns) * 100.0, 1)
        issues = [f"Missing resume section: {s}" for s in missing if s in ("skills", "projects")]
        warnings = [
            f"Missing resume section: {s}" for s in missing if s not in ("skills", "projects")
        ]
        return CriterionResult(
            criterion_name=self.name,
            score=score,
            passed=score >= _PASS_THRESHOLD,
            issues=issues,
            warnings=warnings,
            details={"present": present, "missing": missing, "total_sections": 4},
        )


class FormatHygieneCriterion(ATSCriterion):
    """Deterministic resume format hygiene heuristics."""

    name: str = "format_hygiene"
    weight: float = 0.1

    def evaluate(self, resume_text: str, context: ATSContext) -> CriterionResult:
        checks = self._run_checks(resume_text)
        deductions = [pen for ok, pen, _ in checks.values() if not ok]
        score = round(max(0.0, 100.0 - sum(deductions)), 1)
        issues = [m for ok, _, m in checks.values() if not ok and m and "short" in m]
        warnings = [m for ok, _, m in checks.values() if not ok and m and "short" not in m]
        return CriterionResult(
            criterion_name=self.name,
            score=score,
            passed=score >= _PASS_THRESHOLD,
            issues=issues,
            warnings=warnings,
            details={"checks": {k: v[0] for k, v in checks.items()}, "deductions": deductions},
        )

    def _run_checks(self, resume_text: str) -> dict[str, tuple[bool, float, str]]:
        text = resume_text or ""
        low = text.lower()
        has_email = re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", low) is not None
        has_phone = re.search(r"\+?\d[\d\s().-]{7,}\d", text) is not None
        has_bullets = re.search(r"(?m)^\s*[-*\u2022\u00b7]\s+", text) is not None
        length = len(text)
        if length < 500:
            length_check = (False, 20.0, "Resume too short")
        elif length > 12000:
            length_check = (False, 10.0, "Resume too long")
        else:
            length_check = (True, 0.0, "")
        return {
            "has_email": (has_email, 20.0, "Missing contact email"),
            "has_phone": (has_phone, 10.0, "Missing contact phone"),
            "has_bullets": (has_bullets, 15.0, "No bullet points found"),
            "length_ok": length_check,
        }


class ATS:
    """Deterministic, algorithmic ATS evaluation engine."""

    def __init__(self, criteria: list[ATSCriterion] | None = None):
        if criteria is not None:
            self.criteria = list(criteria)
        else:
            weights = _load_weights()
            keyword = KeywordMatchCriterion()
            keyword.weight = weights["keyword_coverage"]
            section = SectionPresenceCriterion()
            section.weight = weights["section_presence"]
            hygiene = FormatHygieneCriterion()
            hygiene.weight = weights["format_hygiene"]
            self.criteria = [keyword, section, hygiene]

    def add_criterion(self, criterion: ATSCriterion) -> "ATS":
        """Register an additional ATS criterion."""
        self.criteria.append(criterion)
        return self

    def evaluate(
        self,
        resume_text: str,
        context: ATSContext | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate resume text across all registered criteria deterministically."""
        ctx = context if isinstance(context, ATSContext) else ATSContext.from_dict(context)
        if not self.criteria:
            return {
                "score": 100,
                "passed": True,
                "issues": [],
                "warnings": [],
                "missing_keywords": [],
                "breakdown": {},
            }
        return self._aggregate(resume_text, ctx)

    def _aggregate(self, resume_text: str, ctx: ATSContext) -> dict[str, Any]:
        results = [(c, c.evaluate(resume_text, ctx)) for c in self.criteria]
        return self._summarize(results)

    def _summarize(self, results: list[tuple[ATSCriterion, CriterionResult]]) -> dict[str, Any]:
        total_weight = 0.0
        weighted_sum = 0.0
        all_issues: list[str] = []
        all_warnings: list[str] = []
        missing_keywords: list[str] = []
        breakdown: dict[str, Any] = {}
        for criterion, res in results:
            w = self._fold(criterion, res, all_issues, all_warnings, missing_keywords, breakdown)
            total_weight += w
            weighted_sum += res.score * w
        return self._finalize(
            total_weight, weighted_sum, all_issues, all_warnings, missing_keywords, breakdown
        )

    def _fold(
        self,
        criterion: ATSCriterion,
        res: CriterionResult,
        all_issues: list[str],
        all_warnings: list[str],
        missing_keywords: list[str],
        breakdown: dict[str, Any],
    ) -> float:
        all_issues.extend(res.issues)
        all_warnings.extend(res.warnings)
        if criterion.name == "keyword_coverage":
            missing_keywords.extend(res.details.get("missing", []))
        breakdown[criterion.name] = {
            "score": res.score,
            "passed": res.passed,
            "issues": res.issues,
            "warnings": res.warnings,
            "details": res.details,
        }
        return max(0.0, criterion.weight)

    def _finalize(
        self,
        total_weight: float,
        weighted_sum: float,
        all_issues: list[str],
        all_warnings: list[str],
        missing_keywords: list[str],
        breakdown: dict[str, Any],
    ) -> dict[str, Any]:
        final_score = int(round(weighted_sum / total_weight)) if total_weight > 0 else 100
        final_score = max(0, min(100, final_score))
        return {
            "score": final_score,
            "passed": final_score >= 70,
            "issues": list(dict.fromkeys(all_issues)),
            "warnings": list(dict.fromkeys(all_warnings)),
            "missing_keywords": list(dict.fromkeys(missing_keywords)),
            "breakdown": breakdown,
        }
