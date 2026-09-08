"""
TEST-ONLY FIXTURE — Degraded extractor.

Produces noisy resume JSON matching input schema 3.1 (resume {name,email,phone,work_history,education,skills})
plus degradation_log[] for use in matching-engine tests.

Not a production extractor — do not import in orchestrator, routers, or pdf_extractor.
See notes/milestone-4-context.md 3 and notes/plan-b-degraded-extractor.md.

Profiles: workday_like, legacy_ats_like from backend/app/config/degraded_profiles.json
Reuses: backend/app/config/header_keywords.json (from Component A) for narrow header mode
       and backend/app/config/synonyms.json for no_synonym mode.
Seeded RNG via random.Random(seed) for reproducibility.

Order: column scramble -> dropout -> narrow header -> skills-only -> narrow date -> no_synonym -> character noise
"""
# TEST-ONLY FIXTURE — not for production use

from __future__ import annotations

import copy
import json
import random
import re
from functools import lru_cache
from pathlib import Path
from typing import TypedDict


class DegradationEntry(TypedDict):
    mode: str
    severity: float | int | None
    detail: str
    affected_fields: list[str]


DEGRADED_FLAGS: dict[str, dict[str, object]] = {
    "column_order_scramble": {"default_enabled": False, "default_severity": 1.0},
    "table_dropout": {"default_enabled": False, "default_severity": 0.15},
    "narrow_header_recognition": {"default_enabled": False, "default_severity": 0.6},
    "skills_section_only": {"default_enabled": False, "default_severity": None},
    "narrow_date_format": {"default_enabled": False, "default_severity": None},
    "no_synonym_resolution": {"default_enabled": False, "default_severity": None},
    "character_noise": {"default_enabled": False, "default_severity": 0.02},
}

_CONFIG_DIR = Path(__file__).parent.parent / "config"
_MON_YYYY_DASH = re.compile(r"^[A-Z][a-z]{2} \d{4} - (?:[A-Z][a-z]{2} \d{4}|present)$", re.IGNORECASE)


@lru_cache(maxsize=1)
def _load_profiles() -> dict:
    try:
        return json.loads((_CONFIG_DIR / "degraded_profiles.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "workday_like": {},
            "legacy_ats_like": {},
        }


@lru_cache(maxsize=1)
def _load_header_keywords() -> dict:
    try:
        return json.loads((_CONFIG_DIR / "header_keywords.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "experience": ["experience", "work experience"],
            "education": ["education"],
            "skills": ["skills", "technical skills"],
            "projects": ["projects"],
        }


@lru_cache(maxsize=1)
def _load_synonyms() -> dict[str, str]:
    try:
        data = json.loads((_CONFIG_DIR / "synonyms.json").read_text(encoding="utf-8"))
        return {k.strip().lower(): v.strip().lower() for k, v in data.items()}
    except FileNotFoundError:
        return {}


def _resolve_flags(
    profile: str | dict | None,
    flags_override: dict | None,
) -> dict[str, dict]:
    resolved: dict[str, dict] = {}
    for flag, meta in DEGRADED_FLAGS.items():
        resolved[flag] = {"enabled": bool(meta["default_enabled"]), "severity": meta["default_severity"]}

    # profile string
    if isinstance(profile, str) and profile:
        profiles = _load_profiles()
        p = profiles.get(profile)
        if p and isinstance(p, dict):
            for flag, cfg in p.items():
                if flag in DEGRADED_FLAGS and isinstance(cfg, dict):
                    resolved[flag] = {"enabled": bool(cfg.get("enabled", False)), "severity": cfg.get("severity")}
    elif isinstance(profile, dict):
        for flag, cfg in profile.items():
            if flag in DEGRADED_FLAGS and isinstance(cfg, dict):
                resolved[flag] = {"enabled": bool(cfg.get("enabled", False)), "severity": cfg.get("severity")}
            elif flag in DEGRADED_FLAGS:
                resolved[flag] = {"enabled": bool(cfg), "severity": None}

    # flags_override wins
    if flags_override:
        for flag, cfg in flags_override.items():
            if flag not in DEGRADED_FLAGS:
                continue
            if isinstance(cfg, dict):
                resolved[flag] = {"enabled": bool(cfg.get("enabled", False)), "severity": cfg.get("severity")}
            else:
                resolved[flag] = {"enabled": bool(cfg), "severity": None}

    return resolved


def _apply_column_order_scramble(resume: dict, rng: random.Random, severity, log: list[DegradationEntry]) -> dict:
    affected: list[str] = []
    wh = resume.get("work_history")
    if isinstance(wh, list) and len(wh) > 1 and severity:
        if severity >= 1.0 or rng.random() < float(severity):
            rng.shuffle(wh)
            affected.append("work_history")
            # also reorder keys within each entry
            for e in wh:
                if isinstance(e, dict):
                    keys = list(e.keys())
                    rng.shuffle(keys)
                    reordered = {k: e[k] for k in keys}
                    e.clear()
                    e.update(reordered)
    log.append({"mode": "column_order_scramble", "severity": severity, "detail": "shuffled" if affected else "no work_history to scramble", "affected_fields": affected})
    return resume


def _apply_table_dropout(resume: dict, rng: random.Random, severity, log: list[DegradationEntry]) -> dict:
    p = float(severity) if severity is not None else 0.0
    dropped: list[str] = []
    wh = resume.get("work_history")
    if isinstance(wh, list) and p > 0:
        keep = []
        for idx, e in enumerate(wh):
            if rng.random() < p:
                dropped.append(f"work_history[{idx}]")
            else:
                keep.append(e)
        resume["work_history"] = keep
    ed = resume.get("education")
    if isinstance(ed, list) and p > 0:
        keep = []
        for idx, e in enumerate(ed):
            if rng.random() < p:
                dropped.append(f"education[{idx}]")
            else:
                keep.append(e)
        resume["education"] = keep
    sk = resume.get("skills")
    if isinstance(sk, list) and p > 0:
        keep = []
        for idx, s in enumerate(sk):
            if rng.random() < p:
                dropped.append(f"skills[{idx}]")
            else:
                keep.append(s)
        resume["skills"] = keep
    log.append({"mode": "table_dropout", "severity": severity, "detail": f"dropped {len(dropped)} entries", "affected_fields": dropped})
    return resume


def _apply_narrow_header(resume: dict, rng: random.Random, severity, log: list[DegradationEntry]) -> dict:
    hdr = _load_header_keywords()
    affected: list[str] = []
    # truncate to small list when severity >0.5
    all_keys = [k for k in hdr.keys() if not k.startswith("_")]
    keep_n = 2 if (severity and float(severity) > 0.5) else len(all_keys)
    kept = set(all_keys[:keep_n])
    # for JSON fixture, drop education if not kept, drop phone/email if contact not kept
    if "education" not in kept and resume.get("education"):
        affected.append("education")
        # drop with probability severity
        if rng.random() < (float(severity) if severity else 0.6):
            resume["education"] = []
    if "contact" not in kept:
        # simulate narrow header missing contact
        if resume.get("phone") and rng.random() < 0.3:
            affected.append("phone")
            resume["phone"] = None
    log.append({"mode": "narrow_header_recognition", "severity": severity, "detail": f"kept headers {sorted(kept)}", "affected_fields": affected})
    return resume


def _apply_skills_section_only(resume: dict, rng: random.Random, severity, log: list[DegradationEntry]) -> dict:
    sk = resume.get("skills")
    affected: list[str] = []
    if isinstance(sk, list) and len(sk) > 1:
        # truncate to keep only first N or drop 30%
        if severity is not None:
            try:
                sev = float(severity)
                keep = max(1, int(len(sk) * (1 - sev)))
            except Exception:
                keep = max(1, len(sk) - 1)
        else:
            # default drop last 30%
            keep = max(1, int(len(sk) * 0.7))
        if keep < len(sk):
            dropped = sk[keep:]
            resume["skills"] = sk[:keep]
            affected = [f"skills[{i}]" for i in range(keep, len(sk))]
            log.append({"mode": "skills_section_only", "severity": severity, "detail": f"dropped {len(dropped)} skills outside section", "affected_fields": affected})
            return resume
    log.append({"mode": "skills_section_only", "severity": severity, "detail": "no skills to filter", "affected_fields": affected})
    return resume


def _apply_narrow_date(resume: dict, rng: random.Random, severity, log: list[DegradationEntry]) -> dict:
    affected: list[str] = []
    for idx, entry in enumerate(resume.get("work_history") or []):
        if not isinstance(entry, dict):
            continue
        for key in ("start_date", "end_date"):
            val = entry.get(key)
            if val is None or (isinstance(val, str) and val.lower() == "present"):
                continue
            if not isinstance(val, str) or not _MON_YYYY_DASH.match(val.strip()):
                # drop YYYY-MM etc to None
                if isinstance(val, str) and val.strip():
                    entry[key] = None
                    affected.append(f"work_history[{idx}].{key}")
    log.append({"mode": "narrow_date_format", "severity": severity, "detail": f"dropped {len(affected)} non-Mon YYYY dates", "affected_fields": affected})
    return resume


def _apply_no_synonym(resume: dict, rng: random.Random, severity, log: list[DegradationEntry]) -> dict:
    # when enabled, leave skills as-is without normalizing; when disabled, apply synonyms normalization
    # For fixture we log whether mapping was skipped; disabled path normalizes, enabled leaves unchanged
    enabled = bool(severity is not None or True)  # caller already checked enabled; just log
    # Actually severity param presence indicates enabled; we don't transform here beyond logging
    # If disabled, this helper wouldn't be called, so if called it means enabled -> skip normalization
    # To make disabled vs enabled differ, we apply normalization when this mode is NOT enabled (handled outside)
    # Here we keep as-is and log
    sk = resume.get("skills")
    affected: list[str] = []
    if isinstance(sk, list) and sk:
        syn = _load_synonyms()
        for s in sk:
            if isinstance(s, str) and s.strip().lower() in syn:
                affected.append(s)
    detail = "skipped synonym resolution" if affected else "no synonyms to skip"
    log.append({"mode": "no_synonym_resolution", "severity": severity, "detail": detail, "affected_fields": affected})
    return resume


def _apply_character_noise(resume: dict, rng: random.Random, severity, log: list[DegradationEntry]) -> dict:
    p = float(severity) if severity is not None else 0.0
    if p <= 0:
        log.append({"mode": "character_noise", "severity": severity, "detail": "disabled", "affected_fields": []})
        return resume
    affected: list[str] = []
    for field in ("name", "email", "phone"):
        val = resume.get(field)
        if isinstance(val, str) and val:
            chars = list(val)
            noisy: list[str] = []
            changed = False
            for ch in chars:
                if rng.random() < p:
                    op = rng.choice(["dup", "drop", "swap"])
                    if op == "dup":
                        noisy.append(ch)
                        noisy.append(ch)
                        changed = True
                    elif op == "drop":
                        changed = True
                        continue
                    elif op == "swap" and noisy:
                        noisy.append(rng.choice("xyz"))
                        changed = True
                    else:
                        noisy.append(ch)
                else:
                    noisy.append(ch)
            if changed:
                resume[field] = "".join(noisy)
                affected.append(field)
    sk = resume.get("skills")
    if isinstance(sk, list):
        for idx, s in enumerate(sk):
            if isinstance(s, str) and s and rng.random() < p:
                # simple typo: duplicate char
                if len(s) > 1:
                    pos = rng.randrange(len(s))
                    sk[idx] = s[:pos] + s[pos] + s[pos:]
                    if f"skills[{idx}]" not in affected:
                        affected.append(f"skills[{idx}]")
    log.append({"mode": "character_noise", "severity": severity, "detail": f"noised {len(affected)} fields", "affected_fields": affected})
    return resume


def _normalize_input(clean_resume: dict | str) -> dict:
    if isinstance(clean_resume, str):
        try:
            data = json.loads(clean_resume)
            if isinstance(data, dict):
                return copy.deepcopy(data)
            return {"skills": [], "work_history": [], "education": [], "name": None, "email": None, "phone": None}
        except Exception:
            return {"skills": [], "work_history": [], "education": [], "name": None, "email": None, "phone": None}
    if isinstance(clean_resume, dict):
        return copy.deepcopy(clean_resume)
    return {"skills": [], "work_history": [], "education": [], "name": None, "email": None, "phone": None}


def degrade_resume(
    clean_resume: dict | str,
    profile: str | dict | None = None,
    seed: int | None = None,
    flags_override: dict | None = None,
) -> dict:
    rng = random.Random(seed)
    resume = _normalize_input(clean_resume)
    # ensure keys exist
    for k in ("name", "email", "phone", "work_history", "education", "skills"):
        if k not in resume:
            resume[k] = [] if k in ("work_history", "education", "skills") else None
    # normalize work_history/education/skills types
    if resume.get("work_history") is None:
        resume["work_history"] = []
    if resume.get("education") is None:
        resume["education"] = []
    if resume.get("skills") is None:
        resume["skills"] = []

    flags = _resolve_flags(profile, flags_override)
    log: list[DegradationEntry] = []

    # apply in order, only if enabled
    if flags["column_order_scramble"]["enabled"]:
        _apply_column_order_scramble(resume, rng, flags["column_order_scramble"]["severity"], log)
    else:
        # still log disabled? spec says log length equals enabled flags, so only log enabled
        pass

    if flags["table_dropout"]["enabled"]:
        _apply_table_dropout(resume, rng, flags["table_dropout"]["severity"], log)

    if flags["narrow_header_recognition"]["enabled"]:
        _apply_narrow_header(resume, rng, flags["narrow_header_recognition"]["severity"], log)

    if flags["skills_section_only"]["enabled"]:
        _apply_skills_section_only(resume, rng, flags["skills_section_only"]["severity"], log)

    if flags["narrow_date_format"]["enabled"]:
        _apply_narrow_date(resume, rng, flags["narrow_date_format"]["severity"], log)

    if flags["no_synonym_resolution"]["enabled"]:
        _apply_no_synonym(resume, rng, flags["no_synonym_resolution"]["severity"], log)

    if flags["character_noise"]["enabled"]:
        _apply_character_noise(resume, rng, flags["character_noise"]["severity"], log)
    else:
        # character_noise off by default still log if explicitly disabled? ensure toggleability: don't log when disabled
        # but to make disabled vs enabled distinguishable, we only log when enabled
        pass

    # ensure degradation_log present
    resume["degradation_log"] = log
    return resume


def degrade_resume_json(
    clean_json: str,
    profile: str | dict | None = None,
    seed: int | None = None,
    flags_override: dict | None = None,
) -> str:
    return json.dumps(degrade_resume(clean_json, profile, seed, flags_override))
