"use client";

import { useEffect, useState } from "react";
import { getLoginUrl } from "@/lib/api";

export default function Home() {
  const [loginUrl, setLoginUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    try {
      const url = await getLoginUrl();
      window.location.href = url;
    } catch {
      setLoading(false);
    }
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--color-background)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: "480px", width: "100%" }}>
        {/* Logo Mark */}
        <div
          style={{
            width: "72px",
            height: "72px",
            borderRadius: "12px",
            background: "var(--color-primary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 1.5rem",
            fontSize: "2rem",
          }}
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary-fg)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </div>

        <h1 style={{ marginBottom: "0.5rem" }}>Samuel</h1>
        <p className="text-muted" style={{ marginBottom: "2.5rem", lineHeight: 1.7 }}>
          AI-powered resume rewriting. Paste a job description,<br />
          and we&apos;ll tailor your resume to match — using your own GitHub projects.
        </p>

        {/* Login Card */}
        <div className="nm-card" style={{ padding: "2rem" }}>
          <p style={{ marginBottom: "1.5rem", fontWeight: 500 }}>
            Sign in with GitHub to get started
          </p>

          <button
            id="github-login-btn"
            onClick={handleLogin}
            disabled={loading}
            className="btn btn-primary btn-lg"
            style={{ width: "100%", justifyContent: "center", gap: "0.75rem" }}
          >
            {loading ? (
              <span className="spinner spinner-sm" />
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
            )}
            {loading ? "Redirecting…" : "Login with GitHub"}
          </button>

          <p className="text-xs text-muted" style={{ marginTop: "1rem" }}>
            We only request <code>read:user</code> and <code>public_repo</code> scopes.
          </p>
        </div>

        {/* Feature chips */}
        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center", marginTop: "2rem", flexWrap: "wrap" }}>
          <span className="chip">Semantic matching</span>
          <span className="chip">Smart rewriting</span>
          <span className="chip">ATS check</span>
          <span className="chip">PDF export</span>
        </div>
      </div>
    </main>
  );
}
