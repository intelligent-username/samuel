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
  languages: Record<string, number>;
  topics: string[];
  last_push: string;
  readme_text: string | null;
}

export interface Resume {
  id: string;
  original_filename: string;
  created_at: string;
}

export interface Generation {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  job_description_text: string;
  rewritten_resume_text: string | null;
  ats_report: ATSReport | null;
  created_at: string;
  completed_at: string | null;
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
