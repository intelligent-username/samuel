"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  syncRepos, listRepos, uploadResume, saveApiKey,
  getKeyStatus, listResumes, startGeneration,
} from "@/lib/api";
import type { Repository, Resume } from "@/lib/types";

type Message = { text: string; type: "info" | "success" | "error" };

export default function DashboardPage() {
  const router = useRouter();

  const [repos, setRepos] = useState<Repository[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [jobDesc, setJobDesc] = useState("");
  const [hasKey, setHasKey] = useState(false);
  const [envConfigured, setEnvConfigured] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [msg, setMsg] = useState<Message | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [savingKey, setSavingKey] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([listRepos(), listResumes(), getKeyStatus()]).then(([r, res, k]) => {
      setRepos(r);
      setResumes(res);
      if (res.length > 0) setSelectedResumeId(res[0].id);
      setHasKey(k.has_key);
      setEnvConfigured(k.env_configured);
    });
  }, []);

  const flash = (text: string, type: Message["type"] = "info") => setMsg({ text, type });

  const handleSync = async () => {
    setSyncing(true);
    flash("Syncing repos from GitHub...");
    try {
      await syncRepos();
      const fresh = await listRepos();
      setRepos(fresh);
      flash(`Synced ${fresh.length} repositories`, "success");
    } catch (e: any) {
      flash(e.message || "Sync failed", "error");
    } finally {
      setSyncing(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    flash("Uploading resume...");
    try {
      const resume = await uploadResume(file);
      const all = await listResumes();
      setResumes(all);
      setSelectedResumeId(resume.id);
      flash(`Uploaded: ${file.name}`, "success");
    } catch (e: any) {
      flash(e.message || "Upload failed", "error");
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleSaveKey = async () => {
    if (!apiKeyInput.trim()) return;
    setSavingKey(true);
    try {
      await saveApiKey(apiKeyInput.trim());
      setHasKey(true);
      setApiKeyInput("");
      setShowKeyInput(false);
      flash("API key saved securely", "success");
    } catch (e: any) {
      flash(e.message || "Failed to save key", "error");
    } finally {
      setSavingKey(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedResumeId) return flash("Please upload or select a resume", "error");
    if (!jobDesc.trim()) return flash("Please paste a job description", "error");
    if (!hasKey && !envConfigured) return flash("Please save your OpenRouter API key first", "error");
    setGenerating(true);
    try {
      const gen = await startGeneration(selectedResumeId, jobDesc);
      router.push(`/dashboard/results/${gen.id}`);
    } catch (e: any) {
      flash(e.message || "Failed to start generation", "error");
      setGenerating(false);
    }
  };

  const msgColor =
    msg?.type === "success" ? "#1a9e6e" : msg?.type === "error" ? "var(--color-destructive)" : "var(--color-muted-fg)";

  const repoSecNum = 1;
  const keySecNum = envConfigured ? 0 : 2;
  const resumeSecNum = envConfigured ? 2 : 3;
  const jobSecNum = envConfigured ? 3 : 4;

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "1rem" }}>
      <h2 style={{ marginBottom: "0.25rem" }}>Resume Generator</h2>
      <p className="text-muted" style={{ marginBottom: "2rem" }}>
        Follow the steps below to generate a tailored resume.
      </p>

      <div className="dashboard-grid">
        {/* Left Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Step 1: GitHub Repos */}
          <Section number={repoSecNum} title="GitHub Repositories">
            <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
              <button
                id="sync-repos-btn"
                onClick={handleSync}
                disabled={syncing}
                className="btn btn-primary"
              >
                {syncing && <span className="spinner spinner-sm" />}
                {syncing ? "Syncing..." : "Sync Repos"}
              </button>
              {repos.length > 0 && (
                <span className="text-muted text-sm">{repos.length} repos cached</span>
              )}
            </div>
            {repos.length > 0 && (
              <div
                className="nm-inset"
                style={{ marginTop: "1rem", maxHeight: "360px", overflowY: "auto" }}
              >
                {repos.map((r) => (
                  <div
                    key={r.id}
                    style={{
                      padding: "0.875rem",
                      borderBottom: "1px solid var(--color-border)",
                      fontSize: "0.875rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.35rem",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <span style={{ fontWeight: 600, color: "var(--color-foreground)" }}>{r.name}</span>
                      <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.75rem" }} className="text-muted">
                        <span>Stars: {r.stars}</span>
                        {r.last_push && (
                          <span>Pushed: {new Date(r.last_push).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    {r.description && (
                      <p className="text-muted" style={{ margin: 0, fontSize: "0.8125rem", lineBreak: "anywhere" }}>
                        {r.description}
                      </p>
                    )}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginTop: "0.25rem" }}>
                      {r.languages && Object.keys(r.languages).slice(0, 3).map((lang) => (
                        <span key={lang} className="chip text-xs" style={{ fontSize: "0.7rem", padding: "0.1rem 0.4rem" }}>
                          {lang}
                        </span>
                      ))}
                      {r.topics && r.topics.slice(0, 3).map((topic) => (
                        <span key={topic} className="chip text-xs" style={{ fontSize: "0.7rem", padding: "0.1rem 0.4rem", borderColor: "transparent", background: "var(--color-muted)" }}>
                          #{topic}
                        </span>
                      ))}
                      {r.readme_text && (
                        <span className="chip text-xs" style={{ fontSize: "0.7rem", padding: "0.1rem 0.4rem", color: "var(--color-primary)", borderColor: "var(--color-primary)" }}>
                          README
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* Step 3/4: Job Description */}
          <Section number={jobSecNum} title="Job Description">
            <textarea
              id="job-description"
              rows={12}
              placeholder="Paste the job description here..."
              value={jobDesc}
              onChange={(e) => setJobDesc(e.target.value)}
              className="textarea"
              style={{ minHeight: "220px" }}
            />
            <p className="text-xs text-muted" style={{ marginTop: "0.35rem" }}>
              {jobDesc.trim().split(/\s+/).filter(Boolean).length} words
            </p>
          </Section>
        </div>

        {/* Right Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Step 2: API Key (only if not envConfigured) */}
          {!envConfigured && (
            <Section number={keySecNum} title="OpenRouter API Key">
              {hasKey && !showKeyInput ? (
                <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                  <div className="nm-card-sm" style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1 }}>
                    <span style={{ letterSpacing: "0.15em", color: "var(--color-muted-fg)" }}>
                      ••••••••••••••••
                    </span>
                    <span style={{ marginLeft: "auto" }}>
                      <span className="chip" style={{ background: "transparent", color: "#1a9e6e", borderColor: "#1a9e6e" }}>Saved</span>
                    </span>
                  </div>
                  <button
                    id="change-key-btn"
                    onClick={() => setShowKeyInput(true)}
                    className="btn btn-sm"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                  <input
                    id="api-key-input"
                    type="password"
                    placeholder="sk-or-..."
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    className="input"
                    style={{ flex: 1 }}
                    onKeyDown={(e) => e.key === "Enter" && handleSaveKey()}
                  />
                  <button
                    id="save-key-btn"
                    onClick={handleSaveKey}
                    disabled={savingKey || !apiKeyInput.trim()}
                    className="btn btn-primary"
                  >
                    {savingKey ? <span className="spinner spinner-sm" /> : "Save"}
                  </button>
                  {showKeyInput && (
                    <button onClick={() => setShowKeyInput(false)} className="btn btn-ghost btn-sm">
                      Cancel
                    </button>
                  )}
                </div>
              )}
              <p className="text-xs text-muted" style={{ marginTop: "0.5rem" }}>
                Get a key at{" "}
                <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer">
                  openrouter.ai/keys
                </a>
                . Keys are encrypted at rest.
              </p>
            </Section>
          )}

          {/* Step 2/3: Upload Resume */}
          <Section number={resumeSecNum} title="Resume (PDF)">
            <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
              <button
                id="upload-resume-btn"
                onClick={() => fileRef.current?.click()}
                className="btn"
              >
                Upload PDF
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf"
                onChange={handleUpload}
                style={{ display: "none" }}
              />
              {resumes.length > 0 && (
                <select
                  id="resume-select"
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                  className="select"
                  style={{ maxWidth: "260px" }}
                >
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>{r.original_filename}</option>
                  ))}
                </select>
              )}
            </div>
          </Section>

          {/* Rewrite Button */}
          <div style={{ marginTop: "0.5rem" }}>
            <button
              id="generate-btn"
              onClick={handleGenerate}
              disabled={generating}
              className="btn btn-accent btn-lg"
              style={{ width: "100%", justifyContent: "center" }}
            >
              {generating && <span className="spinner spinner-sm" />}
              {generating ? "Starting generation..." : "Generate Rewritten Resume"}
            </button>
          </div>

          {/* Message */}
          {msg && (
            <div
              style={{
                padding: "0.75rem 1rem",
                borderRadius: "8px",
                background: "var(--color-card)",
                border: "1px solid var(--color-border)",
                color: msgColor,
                fontSize: "0.875rem",
                fontWeight: 500,
              }}
            >
              {msg.text}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ number, title, children }: { number: number; title: string; children: React.ReactNode }) {
  return (
    <div className="nm-card">
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
        <div
          style={{
            width: "28px",
            height: "28px",
            borderRadius: "4px",
            background: "var(--color-primary)",
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: "0.8rem",
            flexShrink: 0,
          }}
        >
          {number}
        </div>
        <h3 style={{ margin: 0 }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}