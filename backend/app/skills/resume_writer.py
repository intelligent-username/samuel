import json
import logging
import re
from pathlib import Path

from app.schemas import RewrittenResumeSections
from app.utils.llm import LLMClient, extract_json

logger = logging.getLogger(__name__)

SKILL_FILE = Path(__file__).parent / "resume_writer.md"


class ResumeWriterSkill:
    """Rewrite the skills and projects sections of a resume to align with a job description."""

    async def run(
        self,
        skills_section: str,
        projects_section: str,
        jd_requirements: dict,
        ranked_projects: list[dict],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> dict:
        """Generate rewritten skills and projects sections optimized for the job.

        Args:
            skills_section: The original skills section text from the resume.
            projects_section: The original projects section text from the resume.
            jd_requirements: Structured requirements from JD Parser.
            ranked_projects: Ranked repositories from Project Matcher.
            llm: An initialized LLM client.
            debug_dir: Optional directory for debug output.

        Returns:
            A dict with 'skills' and 'projects' rewritten strings.
        """
        prompt = (
            SKILL_FILE.read_text()
            .replace("{{SKILLS_SECTION}}", skills_section)
            .replace("{{PROJECTS_SECTION}}", projects_section)
            .replace("{{JD_REQUIREMENTS}}", json.dumps(jd_requirements, indent=2))
            .replace("{{RANKED_PROJECTS}}", json.dumps(ranked_projects, indent=2))
        )
        result = await llm.complete(prompt, response_model=RewrittenResumeSections)

        skills_text = ""
        projects_text = ""

        if isinstance(result, RewrittenResumeSections):
            skills_text = result.skills or ""
            projects_text = result.projects or ""
        elif isinstance(result, dict):
            skills_text = str(result.get("skills", ""))
            projects_text = str(result.get("projects", ""))
        elif isinstance(result, str):
            parsed = extract_json(result)
            if isinstance(parsed, dict):
                skills_text = str(parsed.get("skills", ""))
                projects_text = str(parsed.get("projects", ""))
            else:
                # Raw text fallback: try regex extraction for "skills" and "projects" keys from raw JSON string
                m_s = re.search(r'"skills"\s*:\s*"(.*?)(?=",\s*"projects"|"\s*\})', result, re.DOTALL)
                m_p = re.search(r'"projects"\s*:\s*"(.*?)(?="\s*\}|\Z)', result, re.DOTALL)
                if m_s and m_p:
                    skills_text = m_s.group(1).replace(r'\"', '"').replace(r'\n', '\n')
                    projects_text = m_p.group(1).replace(r'\"', '"').replace(r'\n', '\n')
                elif re.search(r"(?i)\n*#+\s*projects\b", result):
                    split = re.split(r"(?i)\n*#+\s*projects\b[:\s]*", result, maxsplit=1)
                    skills_text = split[0]
                    projects_text = split[1] if len(split) > 1 else ""
                else:
                    skills_text = result
                    projects_text = ""

        # Recovery: if skills_text still contains unparsed JSON with "projects"
        if '"projects"' in skills_text and ('"skills"' in skills_text or '```json' in skills_text):
            m_s = re.search(r'"skills"\s*:\s*"(.*?)(?=",\s*"projects"|"\s*\})', skills_text, re.DOTALL)
            m_p = re.search(r'"projects"\s*:\s*"(.*?)(?="\s*\}|\Z)', skills_text, re.DOTALL)
            if m_s:
                skills_text = m_s.group(1).replace(r'\"', '"').replace(r'\n', '\n')
            if m_p:
                projects_text = m_p.group(1).replace(r'\"', '"').replace(r'\n', '\n')

        # Safety check: if projects_text is empty or near-empty, but skills_text contains the projects section
        if (not projects_text.strip() or len(projects_text.strip()) < 15) and re.search(r"(?i)\n*#+\s*projects\b", skills_text):
            split = re.split(r"(?i)\n*#+\s*projects\b[:\s]*", skills_text, maxsplit=1)
            skills_text = split[0]
            projects_text = split[1] if len(split) > 1 else ""

        # Clean up any leftover JSON wrapper syntax
        skills_text = re.sub(r"^```(?:json)?\s*\{\s*", "", skills_text.strip())
        skills_text = re.sub(r'^\s*"skills"\s*:\s*"', "", skills_text).rstrip('"').strip()
        projects_text = re.sub(r'\s*\}\s*```\s*$', "", projects_text.strip())
        projects_text = re.sub(r'^\s*"projects"\s*:\s*"', "", projects_text).rstrip('"').strip()

        # Strip any redundant headers from within the section bodies
        skills_text = re.sub(r"(?i)^\s*#+\s*skills\b[:\s]*\n*", "", skills_text).strip()
        projects_text = re.sub(r"(?i)^\s*#+\s*projects\b[:\s]*\n*", "", projects_text).strip()

        output = {"skills": skills_text, "projects": projects_text}

        if debug_dir:
            debug_path = Path(debug_dir) / "step3_resume_writer.txt"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(f"PROMPT:\n{prompt}\n\nRESPONSE:\n{output}")

        return output
