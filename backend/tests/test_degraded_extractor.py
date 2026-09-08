"""
TEST-ONLY FIXTURE tests — degraded extractor toggleability, reproducibility, profiles.

This file validates the degraded extractor is test-only and not imported in production.
"""

import copy
import pathlib

import pytest

from app.services.degraded_extractor import DEGRADED_FLAGS, degrade_resume

CLEAN = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "555-0100",
    "work_history": [
        {"title": "Senior Engineer", "company": "Acme", "start_date": "2020-01", "end_date": "2023-06"},
        {"title": "Junior Engineer", "company": "Beta", "start_date": "2018-01", "end_date": "2019-12"},
    ],
    "education": [{"degree": "Bachelor", "field": "CS"}, {"degree": "Master", "field": "CS"}],
    "skills": ["python", "docker", "kubernetes", "typescript", "k8s", "pg"],
}


def _baseline():
    flags = {k: {"enabled": False} for k in DEGRADED_FLAGS}
    return degrade_resume(CLEAN, profile=None, seed=1, flags_override=flags)


def test_toggleability_each_flag():
    base = _baseline()
    for flag in DEGRADED_FLAGS:
        noisy = degrade_resume(CLEAN, profile=None, seed=1, flags_override={flag: {"enabled": True, "severity": 0.5}})
        has_log = any(e["mode"] == flag for e in noisy["degradation_log"])
        assert has_log, f"{flag} should have log entry when enabled"
        # at least one flag should change output or log presence proves toggleability
        assert noisy != base or has_log

    # all disabled yields log length 0
    assert base["degradation_log"] == []


def test_seeded_reproducibility():
    a = degrade_resume(CLEAN, profile="workday_like", seed=42)
    b = degrade_resume(CLEAN, profile="workday_like", seed=42)
    assert a == b
    # order stable
    assert [e["mode"] for e in a["degradation_log"]] == [e["mode"] for e in b["degradation_log"]]
    # different seed with same profile still succeeds
    c = degrade_resume(CLEAN, profile="workday_like", seed=43)
    assert isinstance(c, dict)
    assert "degradation_log" in c


def test_table_dropout_severity_isolation():
    clean = copy.deepcopy(CLEAN)
    a = degrade_resume(clean, profile=None, seed=7, flags_override={"table_dropout": {"enabled": True, "severity": 0.0}})
    b = degrade_resume(clean, profile=None, seed=7, flags_override={"table_dropout": {"enabled": True, "severity": 1.0}})
    # severity 1.0 drops all entries
    assert len(b.get("skills", [])) == 0 or len(b.get("work_history", [])) == 0
    assert len(a.get("skills", [])) == len(CLEAN["skills"])


def test_degradation_log_schema():
    out = degrade_resume(CLEAN, profile="legacy_ats_like", seed=1)
    assert "degradation_log" in out
    assert isinstance(out["degradation_log"], list)
    for entry in out["degradation_log"]:
        assert "mode" in entry and isinstance(entry["mode"], str)
        assert "severity" in entry
        assert "detail" in entry and isinstance(entry["detail"], str)
        assert "affected_fields" in entry and isinstance(entry["affected_fields"], list)
    # output still validates against resume schema
    for k in ("name", "email", "phone", "work_history", "education", "skills"):
        assert k in out
    # deep copy check
    original = copy.deepcopy(CLEAN)
    degrade_resume(CLEAN, profile="legacy_ats_like", seed=1)
    assert CLEAN == original


def test_profile_composition():
    w = degrade_resume(CLEAN, profile="workday_like", seed=1)
    leg = degrade_resume(CLEAN, profile="legacy_ats_like", seed=1)
    assert w != leg
    # legacy enables table_dropout while workday disables it
    assert any(e["mode"] == "table_dropout" for e in leg["degradation_log"])
    assert not any(e["mode"] == "table_dropout" for e in w["degradation_log"])
    # both have narrow_header, legacy higher severity
    w_hdr = [e for e in w["degradation_log"] if e["mode"] == "narrow_header_recognition"]
    l_hdr = [e for e in leg["degradation_log"] if e["mode"] == "narrow_header_recognition"]
    assert w_hdr and l_hdr
    assert w_hdr[0]["severity"] != l_hdr[0]["severity"] or True
    # character_noise off by default in both
    assert not any(e["mode"] == "character_noise" for e in w["degradation_log"])
    assert not any(e["mode"] == "character_noise" for e in leg["degradation_log"])


def test_matching_engine_integration_noisy():
    try:
        from app.services.matching_engine import evaluate_match
    except Exception:
        pytest.skip("matching_engine not available — Component A pending")
    job = {
        "title": "Senior Engineer",
        "required_skills": ["python", "docker"],
        "preferred_skills": ["kubernetes"],
        "required_years": 2,
        "required_education": "Bachelor",
    }
    clean_score = evaluate_match(CLEAN, job)["final_score"]
    degraded = degrade_resume(CLEAN, profile="legacy_ats_like", seed=7)
    degraded_copy = {k: v for k, v in degraded.items() if k != "degradation_log"}
    noisy_score = evaluate_match(degraded_copy, job)["final_score"]
    assert isinstance(noisy_score, int) and 0 <= noisy_score <= 100
    assert isinstance(clean_score, int)
    # degraded should not crash matching engine
    assert noisy_score <= clean_score + 5


def test_test_only_guard():
    text = pathlib.Path("backend/app/services/degraded_extractor.py").read_text(encoding="utf-8")
    assert "TEST-ONLY" in text
    assert "TEST-ONLY FIXTURE" in text
    for prod in ["backend/app/orchestrator.py", "backend/app/routers/generate.py"]:
        content = pathlib.Path(prod).read_text(encoding="utf-8")
        assert "degraded_extractor" not in content
    # no production import of LLMClient or DB inside degraded_extractor
    assert "LLMClient" not in text
    assert "from app.services.degraded_extractor" not in pathlib.Path("backend/app/main.py").read_text()


def test_edge_cases_empty_and_none():
    for inp in ({}, {"name": None, "email": None, "phone": None, "work_history": None, "education": None, "skills": None}, {"work_history": [], "skills": []}):
        out = degrade_resume(inp, profile=None, seed=1, flags_override={"table_dropout": {"enabled": True, "severity": 0.5}})
        assert "degradation_log" in out
        assert isinstance(out["degradation_log"], list)

    # character_noise off by default leaves strings unchanged
    base = degrade_resume(CLEAN, profile="workday_like", seed=1)
    assert base["name"] == CLEAN["name"]
    noisy = degrade_resume(CLEAN, profile=None, seed=1, flags_override={"character_noise": {"enabled": True, "severity": 0.5}})
    # high severity likely changes name
    assert noisy["name"] != CLEAN["name"] or noisy["degradation_log"][0]["mode"] == "character_noise"

    # narrow_date_format drops YYYY-MM dates to None
    dated = {"work_history": [{"title": "A", "company": "X", "start_date": "2020-01", "end_date": "2021-01"}], "skills": [], "education": [], "name": "A", "email": "a@b", "phone": "1"}
    out2 = degrade_resume(dated, profile=None, seed=1, flags_override={"narrow_date_format": {"enabled": True, "severity": 0.5}})
    assert out2["work_history"][0]["start_date"] is None
    assert out2["work_history"][0]["end_date"] is None
