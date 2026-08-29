"use client";

import React from "react";
import Link from "next/link";
import BorromeanLogo from "@/components/BorromeanLogo";
import LangBar from "@/components/LangBar";
import type { Repository } from "@/lib/types";

interface DashboardSidebarProps {
  username: string;
  onLogout: () => void;
  repos: Repository[];
  syncing: boolean;
  onSync: () => void;
  onSelectRepo: (r: Repository) => void;
  onRemoveRepo: (id: string, e: React.MouseEvent) => void;
  envConfigured: boolean;
  hasKey: boolean;
  showKeyInput: boolean;
  setShowKeyInput: (show: boolean) => void;
  apiKeyInput: string;
  setApiKeyInput: (key: string) => void;
  savingKey: boolean;
  onSaveKey: () => void;
}

export default function DashboardSidebar({
  username,
  onLogout,
  repos,
  syncing,
  onSync,
  onSelectRepo,
  onRemoveRepo,
  envConfigured,
  hasKey,
  showKeyInput,
  setShowKeyInput,
  apiKeyInput,
  setApiKeyInput,
  savingKey,
  onSaveKey,
}: DashboardSidebarProps) {
  const avatarUrl = username ? `https://github.com/${username}.png?size=40` : null;

  return (
    <aside className="sidebar-layout">
      {/* GitHub Repositories Section */}
      <div className="nm-card repo-section-card" style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {/* Row 1: Title */}
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, margin: 0, textAlign: "center" }}>
            GitHub Repositories
          </h3>

          {/* Row 2: Username profile & Sign out */}
          {username && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
              <div className="nm-card-sm" style={{ padding: "0.3rem 0.7rem", display: "inline-flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8rem" }}>
                {avatarUrl && (
                  <img src={avatarUrl} width={26} height={26} style={{ borderRadius: "50%", objectFit: "cover", flexShrink: 0 }} alt="" />
                )}
                <span style={{ fontWeight: 600 }}>{username}</span>
              </div>
              <button onClick={onLogout} className="btn btn-ghost btn-xs" style={{ fontSize: "0.72rem", padding: "0.25rem 0.6rem" }}>
                Sign out
              </button>
            </div>
          )}

          {/* Row 3: Description */}
          <p className="text-muted text-xs" style={{ margin: 0, lineHeight: "1.4" }}>
            Source material for the projects section of your resume. You may remove individual repos if you wish.
          </p>

          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <button id="sync-repos-btn" onClick={onSync} disabled={syncing} className="btn btn-primary btn-sm">
              {syncing && <span className="spinner spinner-sm" />}
              {syncing ? "Syncing..." : "Sync Repos"}
            </button>
            {repos.length > 0 && <span className="text-muted text-xs">{repos.length} repos</span>}
          </div>

          {repos.length > 0 && (
            <div className="nm-inset custom-scrollbar repo-list-container">
              {repos.map((r) => (
                <div
                  key={r.id}
                  className="repo-row"
                  onClick={() => onSelectRepo && onSelectRepo(r)}
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
                    <span style={{ fontWeight: 600, fontSize: "0.8125rem", color: "var(--color-foreground)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {r.name}
                    </span>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", flexShrink: 0, marginLeft: "0.5rem" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--color-muted-fg)", display: "inline-flex", alignItems: "center", gap: "0.2rem" }}>
                        ★ {r.stars}
                      </span>
                      <button
                        className="repo-remove-btn"
                        onClick={(e) => onRemoveRepo && onRemoveRepo(r.id, e)}
                        title="Remove from catalogue"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  {r.description && (
                    <p style={{ margin: "0.2rem 0 0", fontSize: "0.72rem", color: "var(--color-muted-fg)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {r.description}
                    </p>
                  )}
                  <LangBar languages={r.languages} />
                </div>
              ))}
            </div>
          )}
        </div>

      {/* OpenRouter API Key Section */}
      {!envConfigured && (
        <div className="nm-card" style={{ padding: "1.25rem" }}>
          <h4 style={{ fontSize: "0.85rem", fontWeight: 600, margin: "0 0 0.5rem" }}>OpenRouter API Key</h4>
          {hasKey && !showKeyInput ? (
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <div className="nm-card-sm" style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1, padding: "0.5rem 0.75rem" }}>
                <span style={{ letterSpacing: "0.15em", color: "var(--color-muted-fg)", fontSize: "0.8rem" }}>••••••••••••••••</span>
                <span className="chip" style={{ marginLeft: "auto", color: "#1a9e6e", borderColor: "#1a9e6e", fontSize: "0.65rem" }}>Saved</span>
              </div>
              <button id="change-key-btn" onClick={() => setShowKeyInput && setShowKeyInput(true)} className="btn btn-sm">Change</button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input
                id="api-key-input"
                type="password"
                placeholder="sk-or-..."
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput && setApiKeyInput(e.target.value)}
                className="input"
                style={{ flex: 1, padding: "0.5rem", fontSize: "0.8rem" }}
                onKeyDown={(e) => e.key === "Enter" && onSaveKey && onSaveKey()}
              />
              <button id="save-key-btn" onClick={onSaveKey} disabled={savingKey || !apiKeyInput.trim()} className="btn btn-primary btn-sm">
                {savingKey ? <span className="spinner spinner-sm" /> : "Save"}
              </button>
              {showKeyInput && setShowKeyInput && <button onClick={() => setShowKeyInput(false)} className="btn btn-ghost btn-sm">Cancel</button>}
            </div>
          )}
          <p className="text-xs text-muted" style={{ marginTop: "0.5rem" }}>
            Get a key at <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer">openrouter.ai/keys</a>. Encrypted at rest.
          </p>
        </div>
      )}

      {/* Footer Navigation */}
      <div style={{ marginTop: "auto", paddingTop: "1rem", borderTop: "1px solid var(--color-border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
          <BorromeanLogo size={18} />
          <span style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase" }}>Samuel</span>
        </div>
        <Link href="/dashboard/history" style={{ fontSize: "0.75rem", color: "var(--color-primary)", textDecoration: "underline" }}>
          History
        </Link>
      </div>
    </aside>
  );
}
