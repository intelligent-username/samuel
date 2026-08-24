from fastapi.testclient import TestClient
import pytest
from app.main import app

client = TestClient(app)

def test_jd_too_long_returns_422(client, auth_headers, resume_id):
    """Test that job description > 8000 chars returns 422"""
    jd = "a" * 8001
    res = client.post("/generate/", json={"resume_id": str(resume_id), "job_description": jd}, headers=auth_headers)
    assert res.status_code == 422
    assert "too long" in res.text and "8000" in res.text

def test_jd_exact_8000_succeeds(client, auth_headers, resume_id):
    """Test that job description exactly 8000 chars succeeds"""
    jd = "a" * 8000  # ensure >=10
    res = client.post("/generate/", json={"resume_id": str(resume_id), "job_description": jd}, headers=auth_headers)
    assert res.status_code in (200, 201)  # creates Generation

def test_jd_whitespace_only_rejected(client, auth_headers, resume_id):
    """Test that whitespace-only job description is rejected"""
    res = client.post("/generate/", json={"resume_id": str(resume_id), "job_description": "          "}, headers=auth_headers)
    assert res.status_code == 422
    assert "Please paste" in res.text or "too short" in res.text

def test_jd_10_chars_boundary(client, auth_headers, resume_id):
    """Test that 10-char job description succeeds"""
    res = client.post("/generate/", json={"resume_id": str(resume_id), "job_description": "1234567890"}, headers=auth_headers)
    assert res.status_code in (200, 201)

def test_jd_9_chars_too_short(client, auth_headers, resume_id):
    """Test that 9-char job description is rejected"""
    res = client.post("/generate/", json={"resume_id": str(resume_id), "job_description": "123456789"}, headers=auth_headers)
    assert res.status_code == 422
    assert "too short" in res.text