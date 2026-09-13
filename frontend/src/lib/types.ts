export interface User {
  id: string;
  github_username: string;
}

/** Cached repo row. Mirrors backend `RepositoryResponse`. */
export interface Repository {
  id: string;
  name: string;
  description: string | null;
  stars: number;
  /** Language byte counts. Backend `languages` is `dict | null`. */
  languages: Record<string, number> | null;
  /**
   * Topic tags. Backend `topics` is `list[str] | null`.
   * Frontend type stays non-null for backwards compat; treat missing value as `[]`.
   */
  topics: string[];
  /**
   * Last push time. Backend `last_push` is `datetime | null`.
   * Frontend type stays `string` for backwards compat; treat missing value as null.
   */
  last_push: string;
  readme_text: string | null;
  homepage_url: string | null;
  forks: number;
  is_archived: boolean;
  is_private: boolean;
  repo_created_at: string | null;
  url: string | null;
}

export interface Resume {
  id: string;
  original_filename: string;
  is_generated?: boolean;
  created_at: string;
}

export interface Generation {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  job_description_text: string;
  title?: string | null;
  rewritten_resume_text: string | null;
  /**
   * Backend `ats_report` is `dict | null` shaped as `{score, details, raw_report}`.
   * See `backend/app/schemas/ats.py` and `orchestrator.py:261`. Kept as `ATSReport` here for backwards compat.
   */
  ats_report: ATSReport | null;
  ats_score?: number;
  ats_threshold?: number | null;
  ats_max_iterations?: number | null;
  /** Backend `ats_exit_reason` is `str | null`: `single_pass | threshold_met | stagnation | max_iterations`. */
  ats_exit_reason?: string | null;
  /** Backend `ats_scores` is `list[int] | null`. */
  ats_scores?: number[] | null;
  /** Backend `iterations` is `list[dict] | null` shaped as `{iteration, score}` items. */
  iterations?: Array<{ iteration: number; score: number }> | null;
  error_message?: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface StepProgress {
  step: string;
  status: "pending" | "running" | "done" | "error";
  label?: string;
  message?: string;
  summary?: string;
  iteration?: number;
  score?: number;
}

/**
 * Legacy ATS shape. Backend now returns `{score, details, raw_report}`.
 * Kept for backwards compat; new code should read `details` from the dict.
 */
export interface ATSReport {
  score: number;
  issues: string[];
  warnings: string[];
  missing_keywords: string[];
}
