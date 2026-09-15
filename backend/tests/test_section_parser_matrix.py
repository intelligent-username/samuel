"""Parser header matrix, fallback-empty, and writer inference tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas import RewrittenResumeSections
from app.services.pdf_extractor import extract_sections, replace_sections_in_text
from app.skills.resume_writer import ResumeWriterSkill

EMPLOYER = "Acme Corp"
DATE_START = "Jun 2023"
DATE_END = "Aug 2023"


def test_tech_stack_header():
    text = "Tech Stack\nPython, SQL, Docker\n\nExperience\nSoftware Engineer at Foo"
    sections = extract_sections(text)
    assert "Python" in str(sections["skills"])
    assert "Software Engineer" not in str(sections["skills"])


def test_stack_colon_header():
    text = "STACK:\nPython, Kubernetes\n\nExperience\nDevOps Engineer"
    sections = extract_sections(text)
    assert "Python" in str(sections["skills"])
    assert "DevOps" not in str(sections["skills"])


def test_expertise_header():
    text = "Expertise\nPython, SQL, ETL\n\nProjects\n- ETL pipeline"
    sections = extract_sections(text)
    assert "Python" in str(sections["skills"])
    assert "ETL pipeline" in str(sections["projects"])


def test_employment_boundary():
    text = "Skills:\nPython, SQL\n\nEmployment\nSoftware Engineer at Acme (2021-2023)"
    sections = extract_sections(text)
    assert "Python" in str(sections["skills"])
    assert "Acme" not in str(sections["skills"])


def test_fallback_empty():
    sections = extract_sections("no headers here")
    assert sections["_fallback"] is True
    assert sections["skills"] == ""
    assert sections["projects"] == ""


def test_replace_sections_no_duplication():
    original = "## Skills\nOld\n\n## Projects\nOldP\n\n## Experience\nWork"
    replaced = replace_sections_in_text(original, "New", "NewP")
    assert replaced.count("## Skills") == 1
    assert "New" in replaced
    again = replace_sections_in_text(replaced, "New", "NewP")
    assert again.count("## Skills") == 1
    assert again.count("## Projects") == 1


@pytest.mark.asyncio
async def test_writer_infers_with_evidence():
    skills_section = "Python, Git"
    projects_section = (
        f"Data Engineering Intern at {EMPLOYER} ({DATE_START} - {DATE_END})\n"
        "- Built ETL pipelines processing sales data\n"
        "- Created dashboards for business metrics\n"
        "- Wrote queries for reporting"
    )
    jd_requirements = {
        "keywords": ["python", "sql", "pandas"],
        "hard_requirements": ["sql"],
        "preferred_skills": ["pandas"],
    }
    ranked = [{"name": "etl-pipeline", "description": "ETL sales pipeline"}]
    inferred_skills = "Python, SQL, pandas, ETL, Data Analysis"
    inferred_projects = (
        f"Data Engineering Intern at {EMPLOYER} ({DATE_START} - {DATE_END})\n"
        "- Built ETL pipelines with SQL queries over sales data\n"
        "- Used pandas for data analysis and dashboards"
    )
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(
        return_value=RewrittenResumeSections(skills=inferred_skills, projects=inferred_projects)
    )
    result = await ResumeWriterSkill().run(
        skills_section=skills_section,
        projects_section=projects_section,
        jd_requirements=jd_requirements,
        ranked_projects=ranked,
        llm=mock_llm,
        debug_dir=None,
    )
    skills_low = result["skills"].lower()
    assert "sql" in skills_low
    assert "pandas" in skills_low
    assert "python" in skills_low
    assert EMPLOYER in result["projects"]
    assert DATE_START in result["projects"]
    assert DATE_END in result["projects"]
    assert "Google" not in result["projects"]
    assert mock_llm.complete.await_count == 1
