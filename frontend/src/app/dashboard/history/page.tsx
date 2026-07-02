"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchGenerations } from "@/lib/api";
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

  useEffect(() => {
    fetchGenerations()
      .then((data) => { setGenerations(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", paddingTop: "4rem" }}>
        <span className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "760px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2rem" }}>
        <div>
          <h2 style={{ marginBottom: "0.25rem" }}>Generation History</h2>
          <p className="text-muted">Your past resume generations</p>
        </div>
        <button onClick={() => router.push("/dashboard")} className="btn btn-primary btn-sm">
          New Generation
        </button>
      </div>

      {generations.length === 0 ? (
        <div className="nm-card" style={{ textAlign: "center", padding: "3rem" }}>
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
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
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
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p
                      style={{
                        fontWeight: 500,
                        fontSize: "0.9rem",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        marginBottom: "0.35rem",
                      }}
                    >
                      {snippet || "No job description"}...
                    </p>
                    <span className="text-xs text-muted">{createdAt}</span>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.4rem", flexShrink: 0 }}>
                    <span
                      className="chip"
                      style={{
                        color: meta.color,
                        background: "var(--color-card)",
                      }}
                    >
                      {meta.label}
                    </span>
                    {gen.ats_report && (
                      <span className="chip">
                        ATS {gen.ats_report.score}/100
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
