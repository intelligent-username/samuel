"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { deleteGeneration } from "@/lib/api";
import type { Generation } from "@/lib/types";

const STATUS_META: Record<string, { label: string; color: string }> = {
  pending:   { label: "Pending",   color: "var(--color-muted-fg)" },
  running:   { label: "Running",   color: "var(--color-primary)" },
  completed: { label: "Completed", color: "#1a9e6e" },
  failed:    { label: "Failed",    color: "var(--color-destructive)" },
};

interface HistoryListProps {
  generations: Generation[];
  onDeleted?: (id: string) => void;
  compact?: boolean;
  onSelect?: (id: string) => void;
}

export default function HistoryList({
  generations,
  onDeleted,
  compact = false,
  onSelect,
}: HistoryListProps) {
  const router = useRouter();
  const [confirmDeleteGen, setConfirmDeleteGen] = useState<Generation | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!confirmDeleteGen) return;
    const targetId = confirmDeleteGen.id;
    setDeletingId(targetId);
    setDeleteError(null);
    try {
      await deleteGeneration(targetId);
      if (onDeleted) {
        onDeleted(targetId);
      }
      setConfirmDeleteGen(null);
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete");
    } finally {
      setDeletingId(null);
    }
  };

  const handleClickItem = (id: string) => {
    if (onSelect) {
      onSelect(id);
    } else {
      router.push(`/dashboard/results/${id}`);
    }
  };

  return (
    <>
      {/* Confirmation Dialog */}
      {confirmDeleteGen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            background: "rgba(0,0,0,0.65)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
          onClick={() => !deletingId && setConfirmDeleteGen(null)}
        >
          <div
            className="nm-card"
            style={{
              maxWidth: 420,
              width: "100%",
              borderColor: "var(--color-border)",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.5), 0 8px 10px -6px rgba(0,0,0,0.5)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>Delete Generation</h3>
            <p className="text-muted" style={{ fontSize: "0.875rem", marginBottom: "1.25rem", color: "var(--color-foreground)" }}>
              Are you sure? This is permanent
            </p>
            {deleteError && (
              <p style={{ color: "var(--color-destructive)", fontSize: "0.8rem", marginBottom: "1rem" }}>
                {deleteError}
              </p>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                onClick={() => setConfirmDeleteGen(null)}
                disabled={!!deletingId}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-sm"
                style={{
                  background: "var(--color-destructive)",
                  color: "#fff",
                  borderColor: "var(--color-destructive)",
                }}
                onClick={handleDelete}
                disabled={!!deletingId}
              >
                {deletingId ? <span className="spinner spinner-sm" /> : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {generations.length === 0 ? (
        <div className="nm-card" style={{ textAlign: "center", padding: compact ? "2rem 1rem" : "3rem", width: "100%" }}>
          <div style={{ marginBottom: "0.75rem" }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-muted-fg)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ margin: "0 auto" }}>
              <rect width="20" height="16" x="2" y="4" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
          </div>
          <h4 style={{ marginBottom: "0.35rem", fontSize: compact ? "0.95rem" : "1.1rem" }}>No generations yet</h4>
          <p className="text-muted" style={{ fontSize: "0.82rem", marginBottom: compact ? "1rem" : "1.5rem" }}>
            Upload your resume, paste a job description, and click Generate.
          </p>
          <button onClick={() => router.push("/dashboard")} className="btn btn-accent btn-sm">
            Start generating
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", width: "100%" }}>
          {generations.map((gen) => {
            const meta = STATUS_META[gen.status] ?? STATUS_META.pending;
            const createdAt = new Date(gen.created_at).toLocaleString();
            const snippet = gen.job_description_text?.slice(0, 140).replace(/\n/g, " ");

            return (
              <div
                key={gen.id}
                className="nm-card"
                style={{
                  cursor: "pointer",
                  transition: "border-color 0.18s ease, background 0.15s ease",
                  padding: compact ? "0.875rem 1rem" : "1.25rem 1.5rem",
                  position: "relative",
                }}
                onClick={() => handleClickItem(gen.id)}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--color-primary)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--color-border)")}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.75rem" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{
                      fontWeight: 500,
                      fontSize: compact ? "0.84rem" : "0.9rem",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      marginBottom: "0.35rem",
                      paddingRight: "0.5rem",
                    }}>
                      {snippet || "No job description"}...
                    </p>
                    <span className="text-xs text-muted">{createdAt}</span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexShrink: 0 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.35rem" }}>
                      <span className="chip" style={{ color: meta.color, background: "var(--color-card)", fontSize: "0.7rem", padding: "0.1rem 0.45rem" }}>
                        {meta.label}
                      </span>
                      {gen.status === "completed" && gen.ats_report && typeof gen.ats_report.score === "number" && (
                        <span className="chip" style={{ fontSize: "0.7rem", padding: "0.1rem 0.45rem" }} title={gen.ats_report.issues?.length ? `${gen.ats_report.issues.length} issues` : undefined}>
                          ATS {gen.ats_report.score}/100
                          {Array.isArray(gen.ats_report.issues) && gen.ats_report.issues.length > 0 && !compact && (
                            <span style={{ marginLeft: "0.35rem", fontSize: "0.68rem", opacity: 0.85 }}>· {gen.ats_report.issues.length} issues</span>
                          )}
                        </span>
                      )}
                    </div>

                    {/* "X" Delete Button */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmDeleteGen(gen);
                      }}
                      title="Delete generation"
                      aria-label={`Delete generation from ${createdAt}`}
                      style={{
                        width: "24px",
                        height: "24px",
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        borderRadius: "4px",
                        border: "1px solid transparent",
                        background: "transparent",
                        color: "var(--color-muted-fg)",
                        cursor: "pointer",
                        fontSize: "1rem",
                        lineHeight: 1,
                        transition: "all 0.15s",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "rgba(153,27,27,0.14)";
                        e.currentTarget.style.color = "var(--color-destructive)";
                        e.currentTarget.style.borderColor = "rgba(153,27,27,0.2)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "transparent";
                        e.currentTarget.style.color = "var(--color-muted-fg)";
                        e.currentTarget.style.borderColor = "transparent";
                      }}
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
