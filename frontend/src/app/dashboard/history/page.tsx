"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchGenerations, fetchMe, logout } from "@/lib/api";
import type { Generation } from "@/lib/types";

const STATUS_META: Record<string, { label: string; color: string }> = {
  pending:   { label: "Pending",   color: "var(--color-muted-fg)" },
  running:   { label: "Running",   color: "var(--color-primary)" },
  completed: { label: "Completed", color: "#1a9e6e" },
  failed:    { label: "Failed",    color: "var(--color-destructive)" },
};

export default function HistoryPage() {
  const router = useRouter();
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState("");

  useEffect(() => {
    fetchGenerations()
      .then((data) => { setGenerations(data); setLoading(false); })
      .catch(() => setLoading(false));

    fetchMe()
      .then((u) => setUsername(u.github_username))
      .catch(() => null);
  }, []);

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", paddingTop: "4rem" }}>
        <span className="spinner spinner-lg" />
      </div>
    );
  }

  const avatarUrl = username ? `https://github.com/${username}.png?size=40` : null;

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
      <aside className="sidebar-layout custom-scrollbar">
        {usernameTag && (
          <div style={{ display: "flex", width: "100%", justifyContent: "flex-end", marginBottom: "-0.5rem" }}>
            {usernameTag}
          </div>
        )}
        <Section title="Workspace Status">
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.8125rem", marginTop: "0.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span className="text-muted">Total Generations</span>
              <span style={{ fontWeight: 600 }}>{generations.length}</span>
            </div>
            {generations.length > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span className="text-muted">Last run</span>
                <span style={{ fontWeight: 600, fontSize: "0.75rem" }}>
                  {new Date(generations[0].created_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </Section>

        {/* Navigation */}
        <div style={{ marginTop: "auto", paddingTop: "1rem", borderTop: "1px solid var(--color-border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase" }}>Samuel</span>
          <Link href="/dashboard" style={{ fontSize: "0.75rem", color: "var(--color-primary)", textDecoration: "underline" }}>
            Dashboard
          </Link>
        </div>
      </aside>

      {/* Main content */}
      <div className="main-layout">
        <h1 style={{ fontSize: "2.5rem", fontWeight: 800, textAlign: "center", marginBottom: "0.5rem", letterSpacing: "-0.025em" }}>
          Generation History
        </h1>
        <p className="text-muted" style={{ textAlign: "center", marginBottom: "3rem", fontSize: "0.9rem" }}>
          Your past resume generations and optimization logs.
        </p>

        {generations.length === 0 ? (
          <div className="nm-card" style={{ textAlign: "center", padding: "3rem", width: "100%", maxWidth: "720px", margin: "0 auto" }}>
            <div style={{ marginBottom: "1rem" }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-muted-fg)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ margin: "0 auto" }}>
                <rect width="20" height="16" x="2" y="4" rx="2" />
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
              </svg>
            </div>
            <h3 style={{ marginBottom: "0.5rem" }}>No generations yet</h3>
            <p className="text-muted" style={{ marginBottom: "1.5rem" }}>
              Upload your resume, paste a job description, and click Generate to get started.
            </p>
            <button onClick={() => router.push("/dashboard")} className="btn btn-accent">
              Start generating
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", width: "100%", maxWidth: "720px", margin: "0 auto" }}>
            {generations.map((gen) => {
              const meta = STATUS_META[gen.status] ?? STATUS_META.pending;
              const createdAt = new Date(gen.created_at).toLocaleString();
              const snippet = gen.job_description_text?.slice(0, 140).replace(/\n/g, " ");

              return (
                <div
                  key={gen.id}
                  className="nm-card"
                  style={{ cursor: "pointer", transition: "border-color 0.18s ease" }}
                  onClick={() => router.push(`/dashboard/results/${gen.id}`)}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--color-primary)")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--color-border)")}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontWeight: 500, fontSize: "0.9rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: "0.35rem" }}>
                        {snippet || "No job description"}...
                      </p>
                      <span className="text-xs text-muted">{createdAt}</span>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.4rem", flexShrink: 0 }}>
                      <span className="chip" style={{ color: meta.color, background: "var(--color-card)" }}>
                        {meta.label}
                      </span>
                      {gen.ats_report && (
                        <span className="chip">ATS {gen.ats_report.score}/100</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

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
