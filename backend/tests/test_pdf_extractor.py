import pytest
from app.services.pdf_extractor import extract_sections, _normalize_header, _extract_section


def test_core_competencies_header():
    """Test that 'Core Competencies' header is recognized and extracted."""
    text = "Core Competencies:\nPython, FastAPI, React\n\nExperience\nSoftware Engineer at Tech Corp"
    sections = extract_sections(text)
    assert isinstance(sections["skills"], str)
    assert "Python" in sections["skills"]
    assert sections["skills"] != ""


def test_technical_skills_colon():
    """Test that 'Technical Skills:' with colon is normalized and extracted."""
    text = "Technical Skills:\n- Python\n- FastAPI\n\nEXPERIENCE\nDeveloper at Startup"
    sections = extract_sections(text)
    assert isinstance(sections["skills"], str)
    assert sections["skills"] != ""
    assert "Python" in sections["skills"]


def test_personal_projects_header():
    """Test that 'Personal Projects' header is recognized."""
    text = "Personal Projects:\n- Web App React/Node\n- Mobile App Flutter\n\nSKILLS\nJavaScript, Python"
    sections = extract_sections(text)
    assert isinstance(sections["projects"], str)
    assert sections["projects"] != ""
    assert "Web App" in sections["projects"]


def test_case_insensitive_and_whitespace():
    """Test that header matching is case-insensitive and handles extra whitespace."""
    text = "  technical   expertise  :\nGo, Rust, TypeScript\n\nProjects\n- Project 1\n- Project 2"
    sections = extract_sections(text)
    assert isinstance(sections["skills"], str)
    assert sections["skills"] != ""
    assert "Go" in sections["skills"]
    assert isinstance(sections["projects"], str)
    assert sections["projects"] != ""


def test_normalize_header():
    """Test header normalization function."""
    assert _normalize_header("Technical Skills:") == "technical skills"
    assert _normalize_header("  Core Competencies  ") == "core competencies"
    assert _normalize_header("Open-Source Projects") == "open-source projects"
    assert _normalize_header("KEY SKILLS") == "key skills"


def test_fallback_when_empty():
    """Test fallback to full text when no sections detected."""
    text = "Jane Doe\nSoftware Engineer\n5+ years experience\nPython, FastAPI, React"
    sections = extract_sections(text)
    # Should have fallback content in skills
    assert isinstance(sections["skills"], str)
    assert sections["skills"] != ""
    assert sections.get("_fallback") is True
    assert "Jane Doe" in sections["skills"]
    # Projects should be empty
    assert sections["projects"] == ""


def test_fallback_truncated():
    """Test that fallback text is truncated to ~4000 chars."""
    long_text = "A" * 5000  # Create text longer than 4000 chars
    sections = extract_sections(long_text)
    assert isinstance(sections["skills"], str)
    assert len(sections["skills"]) <= 4000
    assert sections.get("_fallback") is True


def test_extract_section_with_target_names():
    """Test _extract_section function directly with target names."""
    text = "Skills:\nPython, FastAPI\n\nExperience:\nDeveloper at Corp"
    skills = _extract_section(text, {"skills", "technical skills"})
    assert isinstance(skills, str)
    assert "Python" in skills
    assert "Developer at Corp" not in skills  # Should stop at Experience


def test_mixed_headers():
    """Test extraction with mixed header styles."""
    text = """SKILLS
Python, React, Node.js

PROJECTS
- E-commerce platform
- Task management app

EDUCATION
BS Computer Science"""
    sections = extract_sections(text)
    assert isinstance(sections["skills"], str)
    assert sections["skills"] != ""
    assert isinstance(sections["projects"], str)
    assert sections["projects"] != ""
    assert "E-commerce" in sections["projects"]
    assert "Python" in sections["skills"]


def test_no_headers_body_only():
    """Test extraction with no headers - should trigger fallback."""
    text = """Experienced Software Engineer with 8+ years in full-stack development.
Proficient in Python, FastAPI, React, and cloud technologies.
Led development of scalable web applications serving 100K+ users.
Passionate about clean code and system architecture."""
    sections = extract_sections(text)
    assert sections.get("_fallback") is True
    assert isinstance(sections["skills"], str)
    assert sections["skills"] != ""  # Should contain fallback text
    assert sections["projects"] == ""


def test_stop_at_next_section():
    """Test that extraction stops at the next section header."""
    text = """Technical Skills:
Python, FastAPI, React

Experience:
Software Engineer at Tech Corp
- Developed web applications"""
    skills = _extract_section(text, {"technical skills", "skills"})
    assert isinstance(skills, str)
    assert "Python" in skills
    assert "Software Engineer at Tech Corp" not in skills  # Should be excluded


def test_empty_languages_still_works():
    """Test that empty languages dict doesn't break extraction."""
    # This is more of an integration test to ensure the service handles edge cases
    text = "Skills:\nPython\n\nProjects:\n- Web App"
    sections = extract_sections(text)
    assert isinstance(sections["skills"], str)
    assert sections["skills"] != ""
    assert isinstance(sections["projects"], str)
    assert sections["projects"] != ""