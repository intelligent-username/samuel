"""Threshold config validation tests."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import GenerateRequest


def test_threshold_101_raises():
    with pytest.raises(ValidationError) as exc:
        GenerateRequest(resume_id=uuid.uuid4(), job_description="valid job description text", ats_threshold=101)
    assert "less than or equal to 100" in str(exc.value) or "le" in str(exc.value).lower()


def test_threshold_minus1_raises():
    with pytest.raises(ValidationError):
        GenerateRequest(resume_id=uuid.uuid4(), job_description="valid job description text", ats_threshold=-1)


def test_threshold_0_and_none_single_pass():
    r = GenerateRequest(resume_id=uuid.uuid4(), job_description="valid job description text", ats_threshold=0)
    assert r.ats_threshold == 0
    r2 = GenerateRequest(resume_id=uuid.uuid4(), job_description="valid job description text", ats_threshold=None)
    assert r2.ats_threshold is None
    r3 = GenerateRequest(resume_id=uuid.uuid4(), job_description="valid job description text")
    assert r3.ats_threshold is None


def test_max_iterations_validation_clamp_or_422():
    # spec allows either 422 or clamp for 4 and 8; our schema raises 422
    for bad in (4, 8, 10, 100):
        with pytest.raises(ValidationError) as exc:
            GenerateRequest(resume_id=uuid.uuid4(), job_description="valid job description text", ats_max_iterations=bad)
        assert "between 5 and 7" in str(exc.value) or "ats_max_iterations" in str(exc.value)

    for good in (5, 6, 7):
        r = GenerateRequest(resume_id=uuid.uuid4(), job_description="valid job description text", ats_max_iterations=good)
        assert r.ats_max_iterations == good


def test_settings_max_iterations_clamp():
    from app.config import Settings

    s = Settings(ats_max_iterations=10)  # type: ignore[call-arg]
    assert s.ats_max_iterations == 7
    s2 = Settings(ats_max_iterations=4)  # type: ignore[call-arg]
    assert s2.ats_max_iterations == 5
    s3 = Settings(ats_max_iterations=6)  # type: ignore[call-arg]
    assert s3.ats_max_iterations == 6


def test_single_pass_validation_allows_none_threshold():
    # when threshold None, max_iterations may be None too
    r = GenerateRequest(resume_id=uuid.uuid4(), job_description="valid job description text here", ats_threshold=None, ats_max_iterations=None)
    assert r.ats_threshold is None
    assert r.ats_max_iterations is None
