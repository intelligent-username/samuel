import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


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


class ATSCriterion(ABC):
    """Abstract base class for deterministic ATS ranking criteria."""

    name: str = "base_criterion"
    weight: float = 1.0

    @abstractmethod
    def evaluate(self, resume_text: str, context: ATSContext) -> CriterionResult:
        """Evaluate resume text against this criterion."""
        pass


class KeywordMatchCriterion(ATSCriterion):
    """Deterministic keyword coverage criterion.

    Checks resume text for occurrences of target keywords extracted from the job description.
    Handles exact word boundaries, common programming language symbols (C++, C#, .NET),
    and case-insensitivity.
    """

    name: str = "keyword_coverage"
    weight: float = 1.0

    def evaluate(self, resume_text: str, context: ATSContext) -> CriterionResult:
        target_keywords = list(dict.fromkeys(context.keywords or []))
        if not target_keywords and context.hard_requirements:
            target_keywords = list(dict.fromkeys(context.hard_requirements + context.preferred_skills))

        if not target_keywords:
            return CriterionResult(
                criterion_name=self.name,
                score=100.0,
                passed=True,
                details={"matched": [], "missing": [], "total_keywords": 0},
            )

        matched: list[str] = []
        missing: list[str] = []
        text_lower = resume_text.lower()

        for kw in target_keywords:
            kw_clean = kw.strip()
            if not kw_clean:
                continue

            # Handle special symbols like C++, C#, .NET
            escaped = re.escape(kw_clean.lower())
            if re.search(r"[+#.]", kw_clean):
                # Symbol-heavy term: match with non-alphanumeric boundary
                pattern = rf"(?:^|[\s,;|/()]){escaped}(?:$|[\s,;|/()])"
            else:
                pattern = rf"\b{escaped}\b"

            if re.search(pattern, text_lower):
                matched.append(kw_clean)
            else:
                missing.append(kw_clean)

        total = len(matched) + len(missing)
        score = (len(matched) / total * 100.0) if total > 0 else 100.0

        issues: list[str] = []
        warnings: list[str] = []

        # Categorize missing keywords as issues (hard requirements) or warnings (preferred/general)
        hard_reqs_lower = {h.strip().lower() for h in context.hard_requirements if h.strip()}
        for miss in missing:
            if miss.lower() in hard_reqs_lower:
                issues.append(f"Missing core required skill: '{miss}'")
            else:
                warnings.append(f"Missing recommended keyword: '{miss}'")

        return CriterionResult(
            criterion_name=self.name,
            score=round(score, 1),
            passed=score >= 70.0,
            issues=issues,
            warnings=warnings,
            details={
                "matched": matched,
                "missing": missing,
                "match_count": len(matched),
                "total_count": total,
            },
        )


class SectionHeaderCriterion(ATSCriterion):
    """Checks for standard, ATS-parseable section headers (future expansion stub)."""

    name: str = "section_headers"
    weight: float = 0.5

    def evaluate(self, resume_text: str, context: ATSContext) -> CriterionResult:
        standard_headers = {"experience", "education", "skills", "projects"}
        found_headers = set()
        text_lower = resume_text.lower()

        for h in standard_headers:
            if re.search(rf"(?m)^\s*(?:##\s*)?{h}\b", text_lower):
                found_headers.add(h)

        missing = list(standard_headers - found_headers)
        score = (len(found_headers) / len(standard_headers)) * 100.0
        warnings = [f"Standard section header '{m.title()}' not clearly detected" for m in missing]

        return CriterionResult(
            criterion_name=self.name,
            score=round(score, 1),
            passed=len(missing) == 0,
            warnings=warnings,
            details={"found": list(found_headers), "missing": missing},
        )


class ATS:
    """Deterministic, algorithmic ATS evaluation engine.

    Supports pluggable criteria evaluated with configurable weights.
    """

    def __init__(self, criteria: list[ATSCriterion] | None = None):
        if criteria is not None:
            self.criteria = list(criteria)
        else:
            # Active criteria suite: currently integrated with KeywordMatchCriterion
            self.criteria = [KeywordMatchCriterion()]

    def add_criterion(self, criterion: ATSCriterion) -> "ATS":
        """Register an additional ATS criterion."""
        self.criteria.append(criterion)
        return self

    def evaluate(
        self,
        resume_text: str,
        context: ATSContext | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate resume text across all registered criteria deterministically.

        Returns:
            Dictionary matching the ATS report contract:
            - score (int: 0-100)
            - issues (list[str])
            - warnings (list[str])
            - missing_keywords (list[str])
            - breakdown (dict of criterion-level results)
        """
        if not isinstance(context, ATSContext):
            ctx = ATSContext.from_dict(context)
        else:
            ctx = context

        if not self.criteria:
            return {
                "score": 100,
                "issues": [],
                "warnings": [],
                "missing_keywords": [],
                "breakdown": {},
            }

        total_weight = 0.0
        weighted_score_sum = 0.0
        all_issues: list[str] = []
        all_warnings: list[str] = []
        missing_keywords: list[str] = []
        breakdown: dict[str, Any] = {}

        for criterion in self.criteria:
            res = criterion.evaluate(resume_text, ctx)
            w = max(0.0, criterion.weight)
            total_weight += w
            weighted_score_sum += res.score * w

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

        final_score = int(round(weighted_score_sum / total_weight)) if total_weight > 0 else 100
        final_score = max(0, min(100, final_score))

        return {
            "score": final_score,
            "issues": list(dict.fromkeys(all_issues)),
            "warnings": list(dict.fromkeys(all_warnings)),
            "missing_keywords": list(dict.fromkeys(missing_keywords)),
            "breakdown": breakdown,
        }
