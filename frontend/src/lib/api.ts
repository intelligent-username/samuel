const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchMe() {
  return fetchApi("/auth/me");
}

export async function getLoginUrl() {
  const data = await fetchApi("/auth/login");
  return data.authorization_url;
}

export async function syncRepos() {
  return fetchApi("/github/sync", { method: "POST" });
}

export async function listRepos() {
  return fetchApi("/github/repos");
}

export async function uploadResume(file: File) {
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
  return res.json();
}

export async function saveApiKey(key: string) {
  return fetchApi("/resume/key", {
    method: "POST",
    body: JSON.stringify({ api_key: key }),
  });
}

export async function listResumes() {
  return fetchApi("/resume/resumes");
}

export async function startGeneration(resumeId: string, jobDescription: string) {
  return fetchApi("/generate", {
    method: "POST",
    body: JSON.stringify({ resume_id: resumeId, job_description: jobDescription }),
  });
}

export function createGenerationStream(generationId: string): EventSource {
  return new EventSource(`${API}/generate/${generationId}/stream`, { withCredentials: true });
}