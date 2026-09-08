export interface User {
  id: string;
  github_username: string;
  has_openrouter_key: boolean;
}

export interface Repository {
  id: string;
  name: string;
  description: string | null;
  stars: number;
  languages: Record<string, number> | null;
  topics: string[];
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
  target_jd?: string;
  title?: string | null;
  rewritten_resume_text: string | null;
  ats_report: ATSReport | null;
  ats_score?: number;
  ats_threshold?: number | null;
  ats_max_iterations?: number | null;
  ats_exit_reason?: string | null;
  ats_scores?: number[] | null;
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

export interface ATSReport {
  score: number;
  issues: string[];
  warnings: string[];
  missing_keywords: string[];
}

export interface StepEvent {
  step: string;
  message: string;
  summary?: string;
  status: "pending" | "active" | "done" | "error";
}

export interface DoneEvent {
  generation_id: string;
  ats_score: number;
  ats_scores?: number[] | null;
  exit_reason?: string | null;
  iterations?: Array<{ iteration: number; score: number }> | null;
  rewritten_resume: string;
  pdf_url: string;
}
