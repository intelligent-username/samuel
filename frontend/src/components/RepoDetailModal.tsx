"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import remarkFrontmatter from "remark-frontmatter";

import type { Repository } from "@/lib/types";
import LangBar, { LANG_COLORS } from "@/components/LangBar";

interface RepoDetailModalProps {
  repo: Repository;
  onClose: () => void;
}

export default function RepoDetailModal({ repo, onClose }: RepoDetailModalProps) {
  const [tab, setTab] = useState<"overview" | "readme">("overview");
  const total = repo.languages ? Object.values(repo.languages).reduce((a, b) => a + b, 0) : 0;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(0,0,0,0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1.5rem",
      }}
      onClick={onClose}
    >
      <div
        className="nm-card custom-scrollbar"
        style={{
          maxWidth: "660px",
          width: "100%",
          maxHeight: "82vh",
          overflowY: "auto",
          position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
          <div style={{ minWidth: 0 }}>
            <h3 style={{ margin: 0, fontSize: "1rem" }}>{repo.name}</h3>
            {repo.description && (
              <p className="text-muted" style={{ margin: "0.25rem 0 0", fontSize: "0.825rem" }}>
                {repo.description}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost btn-sm"
            style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem", flexShrink: 0, marginLeft: "1rem" }}
          >
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

            <div>
              <p style={{ fontSize: "0.72rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--color-muted-fg)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Languages</p>
              {repo.languages && total > 0 ? (
                <>
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
                </>
              ) : (
                <LangBar languages={repo.languages} />
              )}
            </div>

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
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkFrontmatter]}
                rehypePlugins={[rehypeSanitize]}
                components={{
                  img: ({ node, src, alt, ...props }) => {
                    if (!src) return null;
                    let finalSrc = src;
                    if (!src.startsWith("http://") && !src.startsWith("https://") && !src.startsWith("data:")) {
                      const cleanPath = src.replace(/^\.?\//, "");
                      if (repo.url) {
                        finalSrc = `${repo.url.replace(/\/$/, "")}/raw/HEAD/${cleanPath}`;
                      }
                    }
                    return (
                      <img
                        src={finalSrc}
                        alt={alt || "README image"}
                        loading="lazy"
                        style={{
                          maxWidth: "100%",
                          height: "auto",
                          borderRadius: "6px",
                          margin: "0.75rem 0",
                          display: "block",
                          border: "1px solid var(--color-border)",
                        }}
                        onError={(e) => {
                          const target = e.currentTarget;
                          target.style.display = "none";
                        }}
                        {...props}
                      />
                    );
                  },
                  a: ({ node, children }) => (
                    <span style={{ color: "var(--color-fg)", cursor: "default" }}>
                      {children}
                    </span>
                  ),
                }}
              >
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
