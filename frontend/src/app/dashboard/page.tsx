"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { syncRepos, listRepos, uploadResume, saveApiKey, listResumes, startGeneration } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [repos, setRepos] = useState<any[]>([]);
  const [resumes, setResumes] = useState<any[]>([]);
  const [resumeId, setResumeId] = useState("");
  const [jobDesc, setJobDesc] = useState("");
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState("");

  const handleSync = async () => {
    setMessage("Syncing repos...");
    await syncRepos();
    const data = await listRepos();
    setRepos(data);
    setMessage(`Synced ${data.length} repos`);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setMessage("Uploading resume...");
    const resume = await uploadResume(file);
    setResumeId(resume.id);
    const all = await listResumes();
    setResumes(all);
    setMessage("Resume uploaded");
  };

  const handleSaveKey = async () => {
    const key = prompt("Enter your OpenRouter API key:");
    if (!key) return;
    await saveApiKey(key);
    setMessage("API key saved");
  };

  const handleGenerate = async () => {
    if (!resumeId || !jobDesc) {
      setMessage("Upload a resume and paste a job description first");
      return;
    }
    setGenerating(true);
    setMessage("Starting generation...");
    const gen = await startGeneration(resumeId, jobDesc);
    router.push(`/dashboard/results/${gen.id}`);
  };

  return (
    <div>
      <h2 style={{ marginBottom: "1.5rem" }}>Dashboard</h2>

      <section style={{ marginBottom: "2rem" }}>
        <h3>1. GitHub Repos</h3>
        <button onClick={handleSync} style={btnStyle}>
          Sync Repos from GitHub
        </button>
        {repos.length > 0 && (
          <ul style={{ marginTop: "0.5rem" }}>
            {repos.slice(0, 10).map((r: any) => (
              <li key={r.id}>{r.name} ({r.stars} stars)</li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h3>2. OpenRouter API Key</h3>
        <button onClick={handleSaveKey} style={btnStyle}>
          Set API Key
        </button>
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h3>3. Upload Resume (PDF)</h3>
        <input type="file" accept=".pdf" onChange={handleUpload} />
        {resumes.length > 0 && (
          <ul style={{ marginTop: "0.5rem" }}>
            {resumes.map((r: any) => (
              <li key={r.id}>{r.original_filename}</li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h3>4. Job Description</h3>
        <textarea
          rows={8}
          placeholder="Paste the job description here..."
          value={jobDesc}
          onChange={(e) => setJobDesc(e.target.value)}
          style={{ width: "100%", padding: "0.5rem", border: "1px solid #ccc", borderRadius: "4px" }}
        />
      </section>

      <section>
        <button
          onClick={handleGenerate}
          disabled={generating}
          style={{ ...btnStyle, background: generating ? "#999" : "#2563eb" }}
        >
          {generating ? "Generating..." : "Generate Rewritten Resume"}
        </button>
      </section>

      {message && <p style={{ marginTop: "1rem", color: "#666" }}>{message}</p>}
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "0.5rem 1rem",
  background: "#2563eb",
  color: "#fff",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
  fontWeight: 600,
};