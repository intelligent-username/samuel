import type { Generation, Repository, Resume, User } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchMe(): Promise<User> {
  return fetchApi<User>("/auth/me");
}

export async function getLoginUrl(): Promise<string> {
  const data = await fetchApi<{ authorization_url: string }>("/auth/login");
  return data.authorization_url;
}

export async function logout(): Promise<void> {
  await fetchApi("/auth/logout", { method: "POST" });
}

export async function syncRepos(): Promise<Repository[]> {
  return fetchApi<Repository[]>("/github/sync", { method: "POST" });
}

export async function listRepos(): Promise<Repository[]> {
  return fetchApi<Repository[]>("/github/repos");
}

export async function uploadResume(file: File): Promise<Resume> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/resume/upload`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json() as Promise<Resume>;
}

export async function saveApiKey(key: string): Promise<void> {
  await fetchApi("/resume/key", {
    method: "POST",
    body: JSON.stringify({ api_key: key }),
  });
}

export async function getKeyStatus(): Promise<{ has_key: boolean; env_configured: boolean }> {
  return fetchApi<{ has_key: boolean; env_configured: boolean }>("/resume/key-status");
}

export async function listResumes(): Promise<Resume[]> {
  return fetchApi<Resume[]>("/resume/resumes");
}

export async function startGeneration(resumeId: string, jobDescription: string): Promise<Generation> {
  return fetchApi<Generation>("/generate/", {
    method: "POST",
    body: JSON.stringify({ resume_id: resumeId, job_description: jobDescription }),
  });
}

export function createGenerationStream(generationId: string): EventSource {
  return new EventSource(`${API}/generate/${generationId}/stream`, { withCredentials: true });
}

export function getDownloadUrl(generationId: string): string {
  return `${API}/generate/${generationId}/download`;
}

export async function fetchGenerations(): Promise<Generation[]> {
  return fetchApi<Generation[]>("/history/");
}

export async function fetchGeneration(id: string): Promise<Generation> {
  return fetchApi<Generation>(`/history/${id}`);
}