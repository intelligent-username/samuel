"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  syncRepos, listRepos, uploadResume, saveApiKey, getKeyStatus,
  listResumes, startGeneration, fetchMe, logout, fetchGenerations,
} from "@/lib/api";
import type { Generation, Repository, Resume } from "@/lib/types";

import RepoDetailModal from "@/components/RepoDetailModal";
import DashboardSidebar from "@/components/DashboardSidebar";
import ResumeUploadSection from "@/components/ResumeUploadSection";
import JobDescriptionInput from "@/components/JobDescriptionInput";

type Message = { text: string; type: "info" | "success" | "error" };

export default function DashboardPage() {
  const router = useRouter();

  const [repos, setRepos] = useState<Repository[]>([]);
  const [removedIds, setRemovedIds] = useState<Set<string>>(new Set());
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [hiddenResumeIds, setHiddenResumeIds] = useState<Set<string>>(new Set());
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
  const [username, setUsername] = useState("");
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);

  const JD_MAX = 24000;
  const jdLen = jobDesc.length;
  const jdTrimLen = jobDesc.trim().length;
  const wordCount = jobDesc.trim().split(/\s+/).filter(Boolean).length;
  const overLimit = jdLen > JD_MAX;
  const nearLimit = jdLen > JD_MAX - 500;
  const charsRemaining = JD_MAX - jdLen;

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("samuel_job_desc");
      if (saved) setJobDesc((prev) => prev || saved);
    } catch {}
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem("samuel_job_desc", jobDesc);
    } catch {}
  }, [jobDesc]);

  const visibleRepos = repos
    .filter((r) => !removedIds.has(r.id))
    .sort((a, b) => {
      const aTime = a.last_push ? new Date(a.last_push).getTime() : 0;
      const bTime = b.last_push ? new Date(b.last_push).getTime() : 0;
      return bTime - aTime;
    });

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      listRepos(),
      listResumes(),
      fetchGenerations().catch(() => []),
      getKeyStatus(),
      fetchMe().catch(() => null),
    ]).then(([r, res, gens, k, u]) => {
      if (cancelled) return;
      setRepos(r);
      const inMemoryGenResumes: Resume[] = (gens || [])
        .filter((g) => g.status === "completed" && g.rewritten_resume_text)
        .map((g) => {
          const date = new Date(g.created_at);
          const timeStr = date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });
          return {
            id: g.id,
            original_filename: g.title ? g.title : `Tailored Resume (${timeStr})`,
            is_generated: true,
            created_at: g.created_at,
          };
        });
      const combined = [...res, ...inMemoryGenResumes];
      setResumes(combined);
      if (combined.length > 0) setSelectedResumeId(combined[0].id);
      setHasKey(k.has_key);
      setEnvConfigured(k.env_configured);
      if (u) setUsername(u.github_username);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const flash = (text: string, type: Message["type"] = "info") => setMsg({ text, type });

  const visibleResumes = resumes.filter((r) => !hiddenResumeIds.has(r.id));

  const handleRemoveResumeOption = (resume: Resume, e: React.MouseEvent) => {
    e.stopPropagation();
    setHiddenResumeIds((prev) => new Set([...prev, resume.id]));
    if (selectedResumeId === resume.id) {
      const remaining = visibleResumes.filter((r) => r.id !== resume.id);
      setSelectedResumeId(remaining.length > 0 ? remaining[0].id : "");
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    flash("Syncing repos from GitHub...");
    try {
      await syncRepos();
      const fresh = await listRepos();
      setRepos(fresh);
      setRemovedIds(new Set());
      flash(`Synced ${fresh.length} repositories`, "success");
    } catch (e: unknown) {
      flash(e instanceof Error ? e.message : "Sync failed", "error");
    } finally {
      setSyncing(false);
    }
  };

  const handleUploadFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return flash("Only PDF files are supported", "error");
    }
    flash("Uploading resume...");
    try {
      const resume = await uploadResume(file);
      const freshUploaded = await listResumes();
      setResumes((prev) => {
        const genOnly = prev.filter((p) => p.is_generated);
        return [...freshUploaded, ...genOnly];
      });
      setSelectedResumeId(resume.id);
      flash(`Uploaded: ${file.name}`, "success");
    } catch (e: unknown) {
      flash(e instanceof Error ? e.message : "Upload failed", "error");
    }
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
    } catch (e: unknown) {
      flash(e instanceof Error ? e.message : "Failed to save key", "error");
    } finally {
      setSavingKey(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedResumeId) return flash("Please upload or select a resume", "error");
    if (!jobDesc.trim()) return flash("Please paste a job description", "error");
    if (jobDesc.trim().length < 10) return flash("Job description too short (min 10 characters)", "error");
    if (jobDesc.length > JD_MAX) return flash("Job description too long (max 24000 characters)", "error");
    if (!hasKey && !envConfigured) return flash("Please save your OpenRouter API key first", "error");

    setGenerating(true);
    try {
      const gen = await startGeneration(selectedResumeId, jobDesc.trim());
      router.push(`/dashboard/results/${gen.id}`);
    } catch (e: unknown) {
      flash(e instanceof Error ? e.message : "Failed to start generation", "error");
      setGenerating(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  const msgColor =
    msg?.type === "error"
      ? "var(--color-destructive)"
      : msg?.type === "success"
      ? "#1a9e6e"
      : "var(--color-primary)";

  return (
    <div className="page-shell">
      {selectedRepo && (
        <RepoDetailModal repo={selectedRepo} onClose={() => setSelectedRepo(null)} />
      )}

      <DashboardSidebar
        username={username}
        repos={visibleRepos}
        syncing={syncing}
        onSync={handleSync}
        onSelectRepo={(r) => setSelectedRepo(r)}
        onRemoveRepo={(id, e) => {
          e.stopPropagation();
          setRemovedIds((prev) => new Set([...prev, id]));
        }}
        envConfigured={envConfigured}
        hasKey={hasKey}
        showKeyInput={showKeyInput}
        setShowKeyInput={setShowKeyInput}
        apiKeyInput={apiKeyInput}
        setApiKeyInput={setApiKeyInput}
        savingKey={savingKey}
        onSaveKey={handleSaveKey}
        onLogout={handleLogout}
      />

      <main className="main-layout">
        <h1 style={{ fontSize: "2.5rem", fontWeight: 800, textAlign: "center", marginBottom: "0.5rem", letterSpacing: "-0.025em" }}>
          Samuel: Your Resume Tailor
        </h1>
        <p className="text-muted" style={{ textAlign: "center", marginBottom: "3rem", fontSize: "0.9rem" }}>
          Paste a job description and upload your resume to generate a tailored version.
        </p>

        <div style={{ width: "100%" }} className="dashboard-grid">
          <JobDescriptionInput
            jobDesc={jobDesc}
            onChange={setJobDesc}
            onEnterGenerate={handleGenerate}
            overLimit={overLimit}
            nearLimit={nearLimit}
            wordCount={wordCount}
            jdLen={jdLen}
            jdTrimLen={jdTrimLen}
            charsRemaining={charsRemaining}
            maxChars={JD_MAX}
          />

          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", height: "100%" }}>
            <ResumeUploadSection
              resumes={visibleResumes}
              selectedResumeId={selectedResumeId}
              onSelectResume={setSelectedResumeId}
              onUploadFile={handleUploadFile}
              onRemoveResume={handleRemoveResumeOption}
            />

            <div style={{ display: "flex", flexDirection: "column", flexShrink: 0, position: "relative" }}>
              <button
                id="generate-btn"
                onClick={handleGenerate}
                disabled={generating || overLimit || jdTrimLen < 10}
                className="btn btn-accent btn-lg"
                style={{ width: "100%", justifyContent: "center", paddingBlock: "0.875rem" }}
              >
                {generating && <span className="spinner spinner-sm" />}
                {generating ? "Starting generation..." : "Generate Rewritten Resume"}
              </button>

              {msg && (
                <div
                  style={{
                    position: "absolute",
                    top: "calc(100% + 0.75rem)",
                    left: 0,
                    right: 0,
                    padding: "0.75rem 1rem",
                    borderRadius: "8px",
                    background: "var(--color-card)",
                    border: "1px solid var(--color-border)",
                    color: msgColor,
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    zIndex: 10,
                    boxShadow: "var(--nm-mid)",
                  }}
                >
                  {msg.text}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
