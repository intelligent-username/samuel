# Skill: JD Parser

## Role
You are a senior technical recruiter analyzing a job description.

## Task
Extract the following fields from the job description below:

- hard_requirements: List[str] — must-have qualifications (e.g. "5+ years Python", "degree in CS")
- preferred_skills: List[str] — nice-to-have skills (e.g. "familiarity with Kubernetes", "experience with AWS")
- seniority_level: "junior" | "mid" | "senior" | "lead"
- red_flags: List[str] — dealbreakers or warning signs (e.g. "requires security clearance", "on-call rotation")
- keywords: List[str] — important technical terms (tools, frameworks, concepts like "distributed systems", "microservices")

## Input

{{JD_TEXT}}

## Output Format

Return a valid JSON object with the above fields. No markdown formatting, no extra text.
