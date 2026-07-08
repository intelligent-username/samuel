"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import remarkFrontmatter from "remark-frontmatter";

import {
  syncRepos, listRepos, uploadResume, saveApiKey,
  getKeyStatus, listResumes, startGeneration, fetchMe, logout,
} from "@/lib/api";
import type { Repository, Resume } from "@/lib/types";

type Message = { text: string; type: "info" | "success" | "error" };

// ── Language bar ────────────────────────────────────────────────────────────
const LANG_COLORS: Record<string, string> = {
  TypeScript: "#3178c6", JavaScript: "#f7df1e", Python: "#3572a5",
  Rust: "#dea584", Go: "#00add8", Java: "#b07219", "C++": "#f34b7d",
  C: "#555555", HTML: "#e34c26", CSS: "#563d7c", Shell: "#89e051",
  Vue: "#41b883", Svelte: "#ff3e00", Kotlin: "#a97bff", Swift: "#f05138",
  Ruby: "#701516", PHP: "#4f5d95", Dart: "#00b4ab", Scala: "#dc322f",
};

function LangBar({ languages }: { languages: Record<string, number> | null }) {
  if (!languages) return null;
  const total = Object.values(languages).reduce((a, b) => a + b, 0);
  if (total === 0) return null;
  const entries = Object.entries(languages).sort((a, b) => b[1] - a[1]).slice(0, 8);

  return (
    <div style={{ marginTop: "0.35rem" }}>
      <div style={{ display: "flex", height: "4px", borderRadius: "2px", overflow: "hidden", gap: "1px" }}>
        {entries.map(([lang, bytes]) => (
          <div
            key={lang}
            title={`${lang}: ${((bytes / total) * 100).toFixed(1)}%`}
            style={{ flex: bytes, background: LANG_COLORS[lang] ?? "#888", minWidth: "2px" }}
          />
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.35rem" }}>
        {entries.slice(0, 4).map(([lang, bytes]) => (
          <span key={lang} style={{ display: "flex", alignItems: "center", gap: "0.2rem", fontSize: "0.65rem", color: "var(--color-muted-fg)" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: LANG_COLORS[lang] ?? "#888", display: "inline-block", flexShrink: 0 }} />
            {lang} <span style={{ opacity: 0.6 }}>{((bytes / total) * 100).toFixed(0)}%</span>
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Repo detail modal ───────────────────────────────────────────────────────
function RepoDetail({ repo, onClose }: { repo: Repository; onClose: () => void }) {
  const [tab, setTab] = useState<"overview" | "readme">("overview");
  const total = repo.languages ? Object.values(repo.languages).reduce((a, b) => a + b, 0) : 0;

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "1.5rem",
      }}
      onClick={onClose}
    >
      <div
        className="nm-card custom-scrollbar"
        style={{ maxWidth: "660px", width: "100%", maxHeight: "82vh", overflowY: "auto", position: "relative" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
          <div style={{ minWidth: 0 }}>
            <h3 style={{ margin: 0, fontSize: "1rem" }}>{repo.name}</h3>
            {repo.description && (
              <p className="text-muted" style={{ margin: "0.25rem 0 0", fontSize: "0.825rem" }}>{repo.description}</p>
            )}
          </div>
          <button onClick={onClose} className="btn btn-ghost btn-sm" style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem", flexShrink: 0, marginLeft: "1rem" }}>
            ✕
          </button>
        </div>

        {/* Meta row */}
        <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", color: "var(--color-muted-fg)", marginBottom: "1rem", flexWrap: "wrap" }}>
          <span>★ {repo.stars}</span>
          {repo.last_push && <span>Last push: {new Date(repo.last_push).toLocaleDateString()}</span>}
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: "0.4rem", marginBottom: "1rem", borderBottom: "1px solid var(--color-border)", paddingBottom: "0.5rem" }}>
          {(["overview", "readme"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`btn btn-sm${tab === t ? " btn-primary" : " btn-ghost"}`}
              style={{ fontSize: "0.75rem", padding: "0.2rem 0.6rem" }}
            >
              {t === "overview" ? "Overview" : "README"}
            </button>
          ))}
        </div>

        {tab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Metadata Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.75rem" }}>
              <div className="nm-card-sm" style={{ padding: "0.5rem 0.75rem", fontSize: "0.78rem" }}>
                <span className="text-muted" style={{ display: "block", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Forks</span>
                <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{repo.forks}</span>
              </div>
              <div className="nm-card-sm" style={{ padding: "0.5rem 0.75rem", fontSize: "0.78rem" }}>
                <span className="text-muted" style={{ display: "block", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Stars</span>
                <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{repo.stars}</span>
              </div>
              {repo.repo_created_at && (
                <div className="nm-card-sm" style={{ padding: "0.5rem 0.75rem", fontSize: "0.78rem" }}>
                  <span className="text-muted" style={{ display: "block", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Created</span>
                  <span style={{ fontWeight: 600, fontSize: "0.82rem" }}>{new Date(repo.repo_created_at).toLocaleDateString()}</span>
                </div>
              )}
              <div className="nm-card-sm" style={{ padding: "0.5rem 0.75rem", fontSize: "0.78rem" }}>
                <span className="text-muted" style={{ display: "block", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Visibility</span>
                <span style={{ fontWeight: 600, fontSize: "0.82rem" }}>{repo.is_private ? "Private" : "Public"}</span>
              </div>
            </div>

            {/* Quick Action Badges / Links */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
              {repo.is_archived && (
                <span className="chip" style={{ color: "var(--color-destructive)", borderColor: "var(--color-destructive)", background: "transparent", fontSize: "0.7rem", padding: "0.1rem 0.4rem" }}>
                  Archived
                </span>
              )}
              {repo.url && (
                <a href={repo.url} target="_blank" rel="noopener noreferrer" className="btn btn-sm" style={{ paddingBlock: "0.2rem 0.5rem", fontSize: "0.72rem" }}>
                  View GitHub ↗
                </a>
              )}
              {repo.homepage_url && (
                <a href={repo.homepage_url} target="_blank" rel="noopener noreferrer" className="btn btn-sm" style={{ paddingBlock: "0.2rem 0.5rem", fontSize: "0.72rem" }}>
                  Homepage ↗
                </a>
              )}
            </div>

            {repo.languages && total > 0 && (
              <div>
                <p style={{ fontSize: "0.72rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--color-muted-fg)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Languages</p>
                <LangBar languages={repo.languages} />
                <div style={{ marginTop: "0.6rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                  {Object.entries(repo.languages).sort((a, b) => b[1] - a[1]).map(([lang, bytes]) => (
                    <div key={lang} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                      <span style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                        <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: LANG_COLORS[lang] ?? "#888", display: "inline-block" }} />
                        {lang}
                      </span>
                      <span className="text-muted">{((bytes / total) * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {repo.topics && repo.topics.length > 0 && (
              <div>
                <p style={{ fontSize: "0.72rem", fontWeight: 600, marginBottom: "0.4rem", color: "var(--color-muted-fg)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Topics</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                  {repo.topics.map((t) => (
                    <span key={t} className="chip" style={{ fontSize: "0.72rem" }}>#{t}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "readme" && (
          <div className="markdown-body" style={{ maxHeight: "440px", overflowY: "auto" }}>
            {repo.readme_text ? (
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkFrontmatter]} rehypePlugins={[rehypeSanitize]}>
                {repo.readme_text}
              </ReactMarkdown>
            ) : (
              <p className="text-muted" style={{ fontSize: "0.85rem" }}>No README found.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter();

  const [repos, setRepos] = useState<Repository[]>([]);
  const [removedIds, setRemovedIds] = useState<Set<string>>(new Set());
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
  const [username, setUsername] = useState("");
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Avatar derived from GitHub username — publicly available, no auth needed
  const avatarUrl = username ? `https://github.com/${username}.png?size=40` : null;

  // Filter: hide repos with no language data, and any manually removed
  const visibleRepos = repos.filter(
    (r) => !removedIds.has(r.id) &&
           r.languages && Object.values(r.languages).some((v) => v > 0)
  );

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      listRepos(),
      listResumes(),
      getKeyStatus(),
      fetchMe().catch(() => null),
    ]).then(([r, res, k, u]) => {
      if (cancelled) return;
      setRepos(r);
      setResumes(res);
      if (res.length > 0) setSelectedResumeId(res[0].id);
      setHasKey(k.has_key);
      setEnvConfigured(k.env_configured);
      if (u) setUsername(u.github_username);
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
      setRemovedIds(new Set()); // sync resets removals
      flash(`Synced ${fresh.length} repositories`, "success");
    } catch (e: unknown) {
      flash(e instanceof Error ? e.message : "Sync failed", "error");
    } finally {
      setSyncing(false);
    }
  };

  const handleRemove = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRemovedIds((prev) => new Set([...prev, id]));
  };

  const uploadFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      flash("Only PDF files are supported", "error");
      return;
    }
    flash("Uploading resume...");
    try {
      const resume = await uploadResume(file);
      const all = await listResumes();
      setResumes(all);
      setSelectedResumeId(resume.id);
      flash(`Uploaded: ${file.name}`, "success");
    } catch (e: unknown) {
      flash(e instanceof Error ? e.message : "Upload failed", "error");
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
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
    if (!hasKey && !envConfigured) return flash("Please save your OpenRouter API key first", "error");
    setGenerating(true);
    try {
      const gen = await startGeneration(selectedResumeId, jobDesc);
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
    msg?.type === "success" ? "#1a9e6e" : msg?.type === "error" ? "var(--color-destructive)" : "var(--color-muted-fg)";

  const usernameTag = username ? (
    <div className="username-container" style={{ marginLeft: "auto" }}>
      <div className="nm-card-sm" style={{ padding: "0.2rem 0.5rem", display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.75rem", borderRadius: "4px" }}>
        {avatarUrl ? (
          <img
            src={avatarUrl}
            width={14} height={14}
            style={{ borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
            alt=""
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" style={{ opacity: 0.6, flexShrink: 0 }}>
            <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
          </svg>
        )}
        <a
          href={`https://github.com/${username}?tab=repositories`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "inherit", textDecoration: "none" }}
        >
          {username}
        </a>
      </div>
      <button
        onClick={handleLogout}
        className="btn btn-ghost btn-xs signout-btn"
        style={{ padding: "0.2rem 0.5rem", fontSize: "0.7rem" }}
      >
        Sign out
      </button>
    </div>
  ) : null;

  return (
    <div className="page-shell">
      {selectedRepo && <RepoDetail repo={selectedRepo} onClose={() => setSelectedRepo(null)} />}

      {/* Left Sidebar */}
      <aside className="sidebar-layout custom-scrollbar">
        {/* GitHub Repositories */}
        <Section title="GitHub Repositories" titleExtra={usernameTag}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <button id="sync-repos-btn" onClick={handleSync} disabled={syncing} className="btn btn-primary btn-sm">
              {syncing && <span className="spinner spinner-sm" />}
              {syncing ? "Syncing..." : "Sync Repos"}
            </button>
            {visibleRepos.length > 0 && (
              <span className="text-muted text-xs">{visibleRepos.length} repos</span>
            )}
          </div>

          {visibleRepos.length > 0 && (
            <div
              className="nm-inset custom-scrollbar repo-list-container"
              style={{ marginTop: "1rem", maxHeight: "320px", overflowY: "auto" }}
            >
              {visibleRepos.map((r) => (
                <div
                  key={r.id}
                  className="repo-row"
                  onClick={() => setSelectedRepo(r)}
                  style={{
                    padding: "0.65rem 0.75rem",
                    borderBottom: "1px solid var(--color-border)",
                    cursor: "pointer",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-muted)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 600, fontSize: "0.8125rem", color: "var(--color-foreground)", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {r.name}
                    </span>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", flexShrink: 0, marginLeft: "0.5rem" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--color-muted-fg)" }}>★ {r.stars}</span>
                      <button
                        className="repo-remove-btn"
                        onClick={(e) => handleRemove(r.id, e)}
                        title="Remove from catalogue"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  {r.description && (
                    <p style={{
                      margin: "0.2rem 0 0", fontSize: "0.72rem", color: "var(--color-muted-fg)",
                      display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden",
                    }}>
                      {r.description}
                    </p>
                  )}
                  <LangBar languages={r.languages} />
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* OpenRouter API Key */}
        {!envConfigured && (
          <Section title="OpenRouter API Key">
            {hasKey && !showKeyInput ? (
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <div className="nm-card-sm" style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1, padding: "0.5rem 0.75rem" }}>
                  <span style={{ letterSpacing: "0.15em", color: "var(--color-muted-fg)", fontSize: "0.8rem" }}>••••••••••••••••</span>
                  <span style={{ marginLeft: "auto" }}>
                    <span className="chip" style={{ background: "transparent", color: "#1a9e6e", borderColor: "#1a9e6e", fontSize: "0.65rem", padding: "0.05rem 0.3rem" }}>Saved</span>
                  </span>
                </div>
                <button id="change-key-btn" onClick={() => setShowKeyInput(true)} className="btn btn-sm">Change</button>
              </div>
            ) : (
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  id="api-key-input" type="password" placeholder="sk-or-..."
                  value={apiKeyInput} onChange={(e) => setApiKeyInput(e.target.value)}
                  className="input" style={{ flex: 1, padding: "0.5rem", fontSize: "0.8rem" }}
                  onKeyDown={(e) => e.key === "Enter" && handleSaveKey()}
                />
                <button id="save-key-btn" onClick={handleSaveKey} disabled={savingKey || !apiKeyInput.trim()} className="btn btn-primary btn-sm">
                  {savingKey ? <span className="spinner spinner-sm" /> : "Save"}
                </button>
                {showKeyInput && <button onClick={() => setShowKeyInput(false)} className="btn btn-ghost btn-sm">Cancel</button>}
              </div>
            )}
            <p className="text-xs text-muted" style={{ marginTop: "0.5rem" }}>
              Get a key at <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer">openrouter.ai/keys</a>. Encrypted at rest.
            </p>
          </Section>
        )}

        {/* Footer */}
        <div style={{ marginTop: "auto", paddingTop: "1rem", borderTop: "1px solid var(--color-border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase" }}>Samuel</span>
          <Link href="/dashboard/history" style={{ fontSize: "0.75rem", color: "var(--color-primary)", textDecoration: "underline" }}>History</Link>
        </div>
      </aside>

      {/* Main content */}
      <div className="main-layout">
        <h1 style={{ fontSize: "2.5rem", fontWeight: 800, textAlign: "center", marginBottom: "0.5rem", letterSpacing: "-0.025em" }}>
          Resume Personalizer
        </h1>
        <p className="text-muted" style={{ textAlign: "center", marginBottom: "3rem", fontSize: "0.9rem" }}>
          Paste a job description and upload your resume to generate a tailored version.
        </p>

        <div style={{ width: "100%" }} className="dashboard-grid">
          {/* Job Description */}
          <Section title="Job Description">
            <textarea
              id="job-description" rows={12} placeholder="Paste the job description here..."
              value={jobDesc} onChange={(e) => setJobDesc(e.target.value)}
              className="textarea" style={{ minHeight: "320px", fontSize: "0.85rem", lineHeight: "1.6" }}
            />
            <p className="text-xs text-muted" style={{ marginTop: "0.5rem", fontFamily: "monospace" }}>
              {jobDesc.trim().split(/\s+/).filter(Boolean).length} words
            </p>
          </Section>

          {/* Resume + Action */}
          <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
            <Section title="Resume (PDF)">
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                style={{
                  border: `2px dashed ${isDragging ? "var(--color-primary)" : "var(--color-border)"}`,
                  borderRadius: "10px",
                  padding: "1.25rem 1rem",
                  textAlign: "center",
                  background: isDragging ? "var(--color-muted)" : "transparent",
                  transition: "border-color 0.15s ease, background 0.15s ease",
                  cursor: "default",
                }}
              >
                <p style={{ fontSize: "0.8rem", color: "var(--color-muted-fg)", marginBottom: "0.75rem" }}>
                  {isDragging ? "Drop your PDF here" : "Drag & drop a PDF, or click to browse"}
                </p>
                <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}>
                  <button id="upload-resume-btn" onClick={() => fileRef.current?.click()} className="btn">
                    Upload PDF
                  </button>
                  <input ref={fileRef} type="file" accept=".pdf" onChange={handleUpload} style={{ display: "none" }} />
                  {resumes.length > 0 && (
                    <select id="resume-select" value={selectedResumeId} onChange={(e) => setSelectedResumeId(e.target.value)} className="select" style={{ maxWidth: "260px" }}>
                      {resumes.map((r) => <option key={r.id} value={r.id}>{r.original_filename}</option>)}
                    </select>
                  )}
                </div>
              </div>
            </Section>

            <div>
              <button
                id="generate-btn" onClick={handleGenerate} disabled={generating}
                className="btn btn-accent btn-lg"
                style={{ width: "100%", justifyContent: "center", paddingBlock: "0.875rem", transition: "transform 0.1s ease" }}
                onMouseDown={(e) => { e.currentTarget.style.transform = "scale(0.98) translateY(1px)"; }}
                onMouseUp={(e) => { e.currentTarget.style.transform = "none"; }}
                onMouseLeave={(e) => { e.currentTarget.style.transform = "none"; }}
              >
                {generating && <span className="spinner spinner-sm" />}
                {generating ? "Starting generation..." : "Generate Rewritten Resume"}
              </button>
            </div>

            {msg && (
              <div style={{ padding: "0.75rem 1rem", borderRadius: "8px", background: "var(--color-card)", border: "1px solid var(--color-border)", color: msgColor, fontSize: "0.875rem", fontWeight: 500 }}>
                {msg.text}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Section wrapper ─────────────────────────────────────────────────────────
function Section({
  title,
  titleExtra,
  children,
}: {
  title: string;
  titleExtra?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="nm-card">
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <h3 style={{ margin: 0, fontSize: "0.95rem" }}>{title}</h3>
        {titleExtra}
      </div>
      {children}
    </div>
  );
}