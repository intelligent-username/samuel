from __future__ import annotations

import re
from datetime import datetime, timezone

from app.services.ats_config_loader import (
    load_ats_weights,
    load_degree_map,
    load_seniority_map,
    load_synonyms,
)


def _norm(s: str) -> str:
    return s.strip().lower()


def _norm_skill(s: str, synonyms: dict[str, str]) -> str:
    n = _norm(s)
    return synonyms.get(n, n)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _parse_ym(value: str | None, warnings: list[str]) -> tuple[int, int] | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.lower() == "present":
        now = datetime.now(timezone.utc)
        return (now.year, now.month)
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return (y, mo)
        warnings.append(f"malformed date '{s}'")
        return None
    warnings.append(f"malformed date '{s}'")
    return None


def _months_index(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged: list[tuple[int, int]] = [ranges[0]]
    for s, e in ranges[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


def _skill_score(
    required: list[str] | None,
    preferred: list[str] | None,
    have: list[str] | None,
    synonyms: dict[str, str],
    warnings: list[str],
) -> tuple[float, list[str], list[str], list[str]]:
    req_raw = required or []
    pref_raw = preferred or []
    have_raw = have or []

    have_norm = {_norm_skill(s, synonyms) for s in have_raw if s and str(s).strip()}
    req_norm = _dedupe([_norm_skill(str(s), synonyms) for s in req_raw if s and str(s).strip()])
    pref_norm = _dedupe([_norm_skill(str(s), synonyms) for s in pref_raw if s and str(s).strip()])

    # warn on dedupe
    if len(req_raw) != len(req_norm) or len(pref_raw) != len(pref_norm):
        warnings.append("duplicate skills deduped case-insensitive")

    if not req_norm and not pref_norm:
        return 100.0, [], [], []
    if not req_norm:
        # only preferred present — treat as required? spec says if total_req==0 ->100
        return 100.0, [], [], [p for p in pref_norm if p in have_norm]

    matched_req = [r for r in req_norm if r in have_norm]
    matched_pref = [p for p in pref_norm if p in have_norm]
    missing_req = [r for r in req_norm if r not in have_norm]

    if not pref_norm:
        score = (len(matched_req) / len(req_norm)) * 100 if req_norm else 100.0
    else:
        score_req = (len(matched_req) / len(req_norm)) * 85 if req_norm else 0
        score_pref = (len(matched_pref) / len(pref_norm)) * 15 if pref_norm else 0
        score = score_req + score_pref

    # empty have with required non-empty -> 0 already
    score = max(0.0, min(100.0, round(score, 1)))
    return score, matched_req, missing_req, matched_pref


def _experience_score(
    work_history: list[dict] | None,
    required_years: float | int | None,
    warnings: list[str],
) -> tuple[float, float]:
    if required_years is None or (isinstance(required_years, str) and not str(required_years).strip()):
        # try coerce string numeric
        req: float | None = None
        if isinstance(required_years, str):
            try:
                req = float(required_years)
            except ValueError:
                req = None
        else:
            req = None
        if req is None and required_years is not None:
            try:
                req = float(required_years)  # type: ignore[arg-type]
            except Exception:
                req = None
        if req is None:
            # treat as no requirement
            # still compute candidate years for breakdown
            pass
        if req is None:
            # null -> 100
            cand = _candidate_years(work_history, warnings)
            return 100.0, cand

    try:
        req_val: float | None = None
        if required_years is not None:
            req_val = float(required_years)  # type: ignore[arg-type]
    except Exception:
        warnings.append(f"malformed required_years '{required_years}'")
        req_val = None

    if req_val is None:
        cand = _candidate_years(work_history, warnings)
        return 100.0, cand

    cand = _candidate_years(work_history, warnings)
    if cand >= req_val:
        return 100.0, cand
    if req_val == 0:
        return 100.0, cand
    score = (cand / req_val) * 100 if req_val else 100.0
    return max(0.0, min(100.0, round(score, 1))), cand


def _candidate_years(work_history: list[dict] | None, warnings: list[str]) -> float:
    if not work_history:
        return 0.0
    ranges: list[tuple[int, int]] = []
    for entry in work_history:
        if not isinstance(entry, dict):
            continue
        s = _parse_ym(entry.get("start_date"), warnings)
        e = _parse_ym(entry.get("end_date"), warnings)
        if s is None and e is None:
            continue
        if s is None or e is None:
            warnings.append(f"incomplete dates for {entry.get('title') or entry.get('company') or 'entry'}")
            continue
        s_idx = _months_index(s[0], s[1])
        e_idx = _months_index(e[0], e[1])
        if e_idx < s_idx:
            warnings.append(f"end before start for {entry.get('title')}")
            continue
        ranges.append((s_idx, e_idx))
    merged = _merge_ranges(ranges)
    total_months = sum(e - s for s, e in merged)
    return round(total_months / 12.0, 2)


def _education_score(
    education: list[dict] | None,
    required_education: str | None,
    degree_map: dict[str, int],
    warnings: list[str],
) -> tuple[float, int | None, int | None]:
    if required_education is None or not str(required_education).strip():
        return 100.0, None, None
    req_norm = _norm(str(required_education))
    req_level = degree_map.get(req_norm)
    if req_level is None:
        warnings.append(f"unknown required degree '{required_education}'")
        return 100.0, None, None
    cand_level: int | None = None
    if education:
        for ed in education:
            if not isinstance(ed, dict):
                continue
            deg = ed.get("degree")
            if deg is None or not str(deg).strip():
                continue
            lvl = degree_map.get(_norm(str(deg)))
            if lvl is None:
                warnings.append(f"unknown candidate degree '{deg}'")
                continue
            if cand_level is None or lvl > cand_level:
                cand_level = lvl
    if cand_level is None:
        # no education entry -> lowest vs required
        diff = req_level
        score = max(0, 100 - diff * 25)
        return float(score), cand_level, req_level
    if cand_level >= req_level:
        return 100.0, cand_level, req_level
    diff = req_level - cand_level
    return float(max(0, 100 - diff * 25)), cand_level, req_level


def _seniority_from_title(title: str | None, seniority_map: dict[str, int]) -> int:
    if not title or not str(title).strip():
        return 2
    txt = _norm(str(title))
    best = 2
    found = False
    # match any token in map as substring word
    for token, lvl in seniority_map.items():
        # word boundary check
        if re.search(rf"\b{re.escape(token)}\b", txt):
            if not found or lvl > best:
                best = lvl
                found = True
            elif lvl > best:
                best = lvl
    # if multiple matches pick highest
    if not found:
        # also try whole title normalized lower exact match
        if txt in seniority_map:
            return seniority_map[txt]
        return 2
    return best


def _title_score(
    work_history: list[dict] | None,
    job_title: str | None,
    seniority_map: dict[str, int],
) -> tuple[float, int, int]:
    target = _seniority_from_title(job_title, seniority_map)
    cand = 2
    if work_history:
        levels: list[int] = []
        for e in work_history:
            if not isinstance(e, dict):
                continue
            lvl = _seniority_from_title(e.get("title"), seniority_map)
            # if title field missing, _seniority_from_title returns 2 default; only consider if title present
            if e.get("title") and str(e.get("title")).strip():
                levels.append(lvl)
        if levels:
            cand = max(levels)
    diff = abs(cand - target)
    score = max(0, 100 - diff * 20)
    return float(score), cand, target


def _completeness_score(resume: dict, warnings: list[str]) -> tuple[float, int, int]:
    fields_expected = 6
    found = 0
    if resume.get("name") and str(resume.get("name")).strip():
        found += 1
    if resume.get("email") and str(resume.get("email")).strip():
        found += 1
    if resume.get("phone") and str(resume.get("phone")).strip():
        found += 1
    # work_history with both dates
    wh = resume.get("work_history")
    if isinstance(wh, list) and wh:
        has_both = False
        for e in wh:
            if not isinstance(e, dict):
                continue
            s = e.get("start_date")
            en = e.get("end_date")
            if s and str(s).strip() and en and str(en).strip():
                # check not malformed? consider present valid
                has_both = True
                break
        if has_both:
            found += 1
    # education >=1
    ed = resume.get("education")
    if isinstance(ed, list) and len(ed) >= 1:
        # need at least one with degree or field?
        if any(isinstance(x, dict) and (x.get("degree") or x.get("field")) for x in ed):
            found += 1
        elif len(ed) >= 1:
            found += 1
    # skills >=1
    sk = resume.get("skills")
    if isinstance(sk, list) and len([s for s in sk if s and str(s).strip()]) >= 1:
        found += 1
    score = round((found / fields_expected) * 100, 1) if fields_expected else 100.0
    return float(score), found, fields_expected


def evaluate_match(resume: dict, job: dict) -> dict:
    """Pure deterministic matching scorer.

    evaluate_match(resume, job) -> {final_score, breakdown, warnings}
    resume: {name,email,phone,work_history,education,skills}
    job: {title,required_skills,preferred_skills,required_years,required_education}
    """
    warnings: list[str] = []
    if not isinstance(resume, dict):
        resume = {}
    if not isinstance(job, dict):
        job = {}

    synonyms = load_synonyms()
    degree_map = load_degree_map()
    seniority_map = load_seniority_map()
    weights = load_ats_weights()

    skill_score, matched_req, missing_req, matched_pref = _skill_score(
        job.get("required_skills"),
        job.get("preferred_skills"),
        resume.get("skills"),
        synonyms,
        warnings,
    )

    exp_score, cand_years = _experience_score(resume.get("work_history"), job.get("required_years"), warnings)

    edu_score, cand_level, req_level = _education_score(resume.get("education"), job.get("required_education"), degree_map, warnings)

    title_score, cand_sen, target_sen = _title_score(resume.get("work_history"), job.get("title"), seniority_map)

    comp_score, found, expected = _completeness_score(resume, warnings)

    final = round(
        weights.get("skill", 0.40) * skill_score
        + weights.get("experience", 0.20) * exp_score
        + weights.get("education", 0.15) * edu_score
        + weights.get("title", 0.15) * title_score
        + weights.get("completeness", 0.10) * comp_score
    )
    final = max(0, min(100, int(final)))

    return {
        "final_score": final,
        "breakdown": {
            "skill_match": {
                "score": skill_score,
                "matched_required": matched_req,
                "missing_required": missing_req,
                "matched_preferred": matched_pref,
            },
            "experience_match": {
                "score": exp_score,
                "candidate_years": cand_years,
                "required_years": job.get("required_years"),
            },
            "education_match": {
                "score": edu_score,
                "candidate_level": cand_level,
                "required_level": req_level,
            },
            "title_match": {
                "score": title_score,
                "candidate_seniority": cand_sen,
                "target_seniority": target_sen,
            },
            "input_completeness": {
                "score": comp_score,
                "fields_found": found,
                "fields_expected": expected,
            },
        },
        "warnings": warnings,
    }
