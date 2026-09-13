# What the pipeline does

Samuel rewrites the Skills and Projects sections of a resume to match a job description. It leaves all other sections in place.

## Step 1: Parse the job description

The JD Parser skill reads the pasted job text. It returns structured needs: hard needs, preferred skills, seniority, and keywords.

## Step 2: Rank projects

The Project Matcher skill compares cached GitHub repos to those needs. It uses LLM ranking, not vector search. It returns repos ordered by fit, with reasons.

Each project bullet follows this shape:

- What was done
- Which skill it shows, taken from the job text
- Why it mattered, in plain terms

## Step 3: Rewrite Skills and Projects

The Resume Writer skill writes new Skills and Projects text. It only uses skills and projects found in the resume or synced repos. It does not invent history.

## Step 4: Check ATS score

A deterministic ATS engine scores the rewritten text. When a threshold is set, the writer refines the text until the score passes or the loop ends. See `backend/app/orchestrator.py:87-142`.

## Step 5: Return the result

The app stores the rewritten text, the ATS report, and the PDF bytes. The results page shows the preview and the ATS score.
