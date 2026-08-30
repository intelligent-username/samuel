"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { deleteGeneration, updateGeneration, stopGeneration, retryGeneration } from "@/lib/api";
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
  onUpdated?: (id: string, updated: Generation) => void;
  compact?: boolean;
  onSelect?: (id: string) => void;
}

export default function HistoryList({
  generations,
  onDeleted,
  onUpdated,
  compact = false,
  onSelect,
}: HistoryListProps) {
  const router = useRouter();
  const [confirmDeleteGen, setConfirmDeleteGen] = useState<Generation | null>(null);
  const [confirmMultiDelete, setConfirmMultiDelete] = useState(false);
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Status tag action states (stop/retry)
  const [hoveredTagGenId, setHoveredTagGenId] = useState<string | null>(null);
  const [actionGenId, setActionGenId] = useState<string | null>(null);

  const handleStop = async (gen: Generation, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionGenId(gen.id);
    try {
      const updated = await stopGeneration(gen.id);
      if (onUpdated) onUpdated(gen.id, updated);
    } catch (err) {
      console.error("Failed to stop generation:", err);
    } finally {
      setActionGenId(null);
    }
  };

  const handleRetry = async (gen: Generation, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionGenId(gen.id);
    try {
      const updated = await retryGeneration(gen.id);
      if (onUpdated) onUpdated(gen.id, updated);
      if (onSelect) {
        onSelect(gen.id);
      } else {
        router.push(`/dashboard/results/${gen.id}`);
      }
    } catch (err) {
      console.error("Failed to retry generation:", err);
    } finally {
      setActionGenId(null);
    }
  };

  // Title editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [savingTitle, setSavingTitle] = useState(false);
  const editInputRef = useRef<HTMLInputElement | null>(null);

  const startRename = (gen: Generation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(gen.id);
    const initial = gen.title ?? gen.job_description_text?.slice(0, 140).replace(/\n/g, " ") ?? "";
    setEditValue(initial);
    setTimeout(() => {
      editInputRef.current?.focus();
      editInputRef.current?.select();
    }, 50);
  };

  const cancelRename = () => {
    setEditingId(null);
    setEditValue("");
  };

  const saveRename = async (genId: string) => {
    if (savingTitle) return;
    const trimmed = editValue.trim();
    setSavingTitle(true);
    try {
      const updated = await updateGeneration(genId, trimmed);
      if (onUpdated) {
        onUpdated(genId, updated);
      }
      setEditingId(null);
    } catch {
      // Keep edit state or cancel
      setEditingId(null);
    } finally {
      setSavingTitle(false);
    }
  };

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
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(targetId);
        return next;
      });
      setConfirmDeleteGen(null);
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete");
    } finally {
      setDeletingId(null);
    }
  };

  const handleMultiDelete = async () => {
    if (selectedIds.size === 0) return;
    setIsMultiDeleting(true);
    setDeleteError(null);
    try {
      const idsToDelete = Array.from(selectedIds);
      await Promise.all(idsToDelete.map((id) => deleteGeneration(id)));
      if (onDeleted) {
        idsToDelete.forEach((id) => onDeleted(id));
      }
      setSelectedIds(new Set());
      setConfirmMultiDelete(false);
      setIsSelectMode(false);
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete some generations");
    } finally {
      setIsMultiDeleting(false);
    }
  };

  const toggleSelectMode = () => {
    if (isSelectMode) {
      setIsSelectMode(false);
      setSelectedIds(new Set());
    } else {
      setIsSelectMode(true);
    }
  };

  const toggleCheck = (id: string, e: React.MouseEvent | React.ChangeEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleClickItem = (id: string) => {
    if (isSelectMode) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
      return;
    }
    if (onSelect) {
      onSelect(id);
    } else {
      router.push(`/dashboard/results/${id}`);
    }
  };

  return (
    <>
      {/* Single Confirmation Dialog */}
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

      {/* Multi-Delete Confirmation Dialog */}
      {confirmMultiDelete && (
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
          onClick={() => !isMultiDeleting && setConfirmMultiDelete(false)}
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
            <h3 style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>Delete {selectedIds.size} Generations</h3>
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
                onClick={() => setConfirmMultiDelete(false)}
                disabled={isMultiDeleting}
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
                onClick={handleMultiDelete}
                disabled={isMultiDeleting}
              >
                {isMultiDeleting ? <span className="spinner spinner-sm" /> : `Delete (${selectedIds.size})`}
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
        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", width: "100%" }}>
          {/* Top selection bar */}
          <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: "0.6rem", paddingRight: compact ? "1rem" : "1.5rem", marginBottom: "0.15rem" }}>
            {selectedIds.size > 0 && (
              <button
                type="button"
                onClick={() => setConfirmMultiDelete(true)}
                title={`Delete ${selectedIds.size} selected`}
                aria-label="Delete selected generations"
                className="btn btn-sm"
                style={{
                  background: "rgba(153,27,27,0.18)",
                  borderColor: "var(--color-destructive)",
                  color: "var(--color-destructive)",
                  padding: "0.2rem 0.55rem",
                  fontSize: "0.74rem",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  borderRadius: "6px",
                }}
              >
                {/* Trash can icon */}
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 6h18" />
                  <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                  <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                  <line x1="10" y1="11" x2="10" y2="17" />
                  <line x1="14" y1="11" x2="14" y2="17" />
                </svg>
                <span>Delete ({selectedIds.size})</span>
              </button>
            )}

            <label
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.45rem",
                fontSize: "0.72rem",
                fontWeight: 600,
                letterSpacing: "0.03em",
                textTransform: "uppercase",
                color: isSelectMode ? "var(--color-foreground)" : "var(--color-muted-fg)",
                cursor: "pointer",
                userSelect: "none",
                background: isSelectMode ? "var(--color-muted)" : "transparent",
                border: `1px solid ${isSelectMode ? "var(--color-border)" : "transparent"}`,
                padding: "0.2rem 0.45rem 0.2rem 0.55rem",
                borderRadius: "6px",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                if (!isSelectMode) e.currentTarget.style.color = "var(--color-foreground)";
              }}
              onMouseLeave={(e) => {
                if (!isSelectMode) e.currentTarget.style.color = "var(--color-muted-fg)";
              }}
            >
              <span>Select</span>
              <input
                type="checkbox"
                checked={isSelectMode}
                onChange={toggleSelectMode}
                style={{
                  accentColor: "var(--color-primary)",
                  cursor: "pointer",
                  width: "16px",
                  height: "16px",
                  margin: 0,
                }}
              />
            </label>
          </div>

          {generations.map((gen) => {
            const meta = STATUS_META[gen.status] ?? STATUS_META.pending;
            const createdAt = new Date(gen.created_at).toLocaleString();
            const snippet = gen.job_description_text?.slice(0, 140).replace(/\n/g, " ");
            const isChecked = selectedIds.has(gen.id);

            return (
              <div
                key={gen.id}
                className="nm-card"
                style={{
                  cursor: "pointer",
                  transition: "border-color 0.18s ease, background 0.15s ease",
                  padding: compact ? "0.875rem 1rem" : "1.25rem 1.5rem",
                  position: "relative",
                  borderColor: isChecked ? "var(--color-primary)" : "var(--color-border)",
                  background: isChecked ? "rgba(0, 102, 153, 0.08)" : "var(--color-card)",
                }}
                onClick={() => handleClickItem(gen.id)}
                onMouseEnter={(e) => {
                  if (!isChecked) e.currentTarget.style.borderColor = "var(--color-primary)";
                }}
                onMouseLeave={(e) => {
                  if (!isChecked) e.currentTarget.style.borderColor = "var(--color-border)";
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.75rem" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {editingId === gen.id ? (
                      <div
                        onClick={(e) => e.stopPropagation()}
                        style={{ marginBottom: "0.35rem", display: "flex", alignItems: "center", gap: "0.4rem" }}
                      >
                        <input
                          ref={editInputRef}
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") saveRename(gen.id);
                            else if (e.key === "Escape") cancelRename();
                          }}
                          onBlur={() => saveRename(gen.id)}
                          disabled={savingTitle}
                          maxLength={255}
                          className="input"
                          style={{
                            padding: "0.2rem 0.45rem",
                            fontSize: compact ? "0.84rem" : "0.9rem",
                            fontWeight: 500,
                            width: "100%",
                            background: "var(--color-background)",
                            borderColor: "var(--color-primary)",
                            borderRadius: "4px",
                          }}
                          placeholder="Name this generation..."
                        />
                      </div>
                    ) : (
                      <p
                        title="Double-click to rename"
                        onClick={(e) => e.stopPropagation()}
                        onDoubleClick={(e) => startRename(gen, e)}
                        style={{
                          fontWeight: 500,
                          fontSize: compact ? "0.84rem" : "0.9rem",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          marginBottom: "0.35rem",
                          paddingRight: "0.5rem",
                          cursor: "text",
                          color: "var(--color-foreground)",
                        }}
                      >
                        {gen.title ? gen.title : `${snippet || "No job description"}...`}
                      </p>
                    )}
                    <span className="text-xs text-muted">{createdAt}</span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexShrink: 0 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.35rem" }}>
                      {gen.status === "running" ? (
                        <button
                          type="button"
                          onClick={(e) => handleStop(gen, e)}
                          onMouseEnter={() => setHoveredTagGenId(gen.id)}
                          onMouseLeave={() => setHoveredTagGenId(null)}
                          disabled={actionGenId === gen.id}
                          title={hoveredTagGenId === gen.id ? "Click to stop generation" : "Running (click to stop)"}
                          className="chip"
                          style={{
                            cursor: "pointer",
                            fontSize: "0.7rem",
                            padding: "0.15rem 0.55rem",
                            transition: "all 0.15s ease",
                            fontWeight: 600,
                            background: hoveredTagGenId === gen.id ? "rgba(220, 38, 38, 0.14)" : "var(--color-card)",
                            color: hoveredTagGenId === gen.id ? "var(--color-destructive)" : "var(--color-primary)",
                            borderColor: hoveredTagGenId === gen.id ? "var(--color-destructive)" : "var(--color-primary)",
                          }}
                        >
                          {actionGenId === gen.id ? (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
                              <span className="spinner spinner-sm" style={{ width: "9px", height: "9px", borderWidth: "1.5px" }} />
                              Stopping…
                            </span>
                          ) : hoveredTagGenId === gen.id ? (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                              <span style={{ fontSize: "0.6rem" }}>■</span> Stop
                            </span>
                          ) : (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
                              <span className="spinner spinner-sm" style={{ width: "8px", height: "8px", borderWidth: "1.5px" }} />
                              Running
                            </span>
                          )}
                        </button>
                      ) : gen.status === "failed" ? (
                        <button
                          type="button"
                          onClick={(e) => handleRetry(gen, e)}
                          onMouseEnter={() => setHoveredTagGenId(gen.id)}
                          onMouseLeave={() => setHoveredTagGenId(null)}
                          disabled={actionGenId === gen.id}
                          title={hoveredTagGenId === gen.id ? "Click to retry generation" : "Failed (click to retry)"}
                          className="chip"
                          style={{
                            cursor: "pointer",
                            fontSize: "0.7rem",
                            padding: "0.15rem 0.55rem",
                            transition: "all 0.15s ease",
                            fontWeight: 600,
                            background: hoveredTagGenId === gen.id ? "rgba(0, 102, 153, 0.16)" : "var(--color-card)",
                            color: hoveredTagGenId === gen.id ? "var(--color-primary)" : "var(--color-destructive)",
                            borderColor: hoveredTagGenId === gen.id ? "var(--color-primary)" : "rgba(220, 38, 38, 0.4)",
                          }}
                        >
                          {actionGenId === gen.id ? (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
                              <span className="spinner spinner-sm" style={{ width: "9px", height: "9px", borderWidth: "1.5px" }} />
                              Retrying…
                            </span>
                          ) : hoveredTagGenId === gen.id ? (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                              ↻ Retry
                            </span>
                          ) : (
                            "Failed"
                          )}
                        </button>
                      ) : (
                        <span
                          className="chip"
                          style={{
                            color: meta.color,
                            background: "var(--color-card)",
                            fontSize: "0.7rem",
                            padding: "0.15rem 0.55rem",
                            borderColor: meta.color === "var(--color-muted-fg)" ? "var(--color-border)" : meta.color,
                          }}
                        >
                          {meta.label}
                        </span>
                      )}
                      {gen.status === "completed" && gen.ats_report && typeof gen.ats_report.score === "number" && (
                        <span
                          className="chip"
                          style={{
                            fontSize: "0.7rem",
                            padding: "0.1rem 0.45rem",
                            color:
                              gen.ats_report.score >= 80
                                ? "#1a9e6e"
                                : gen.ats_report.score > 45
                                ? "var(--color-accent)"
                                : "var(--color-destructive)",
                            borderColor:
                              gen.ats_report.score >= 80
                                ? "#1a9e6e"
                                : gen.ats_report.score > 45
                                ? "var(--color-accent)"
                                : "var(--color-destructive)",
                            background:
                              gen.ats_report.score >= 80
                                ? "rgba(26, 158, 110, 0.15)"
                                : gen.ats_report.score > 45
                                ? "rgba(252, 106, 3, 0.15)"
                                : "rgba(153, 27, 27, 0.15)",
                          }}
                          title={gen.ats_report.issues?.length ? `${gen.ats_report.issues.length} issues` : undefined}
                        >
                          ATS {gen.ats_report.score}/100
                          {Array.isArray(gen.ats_report.issues) && gen.ats_report.issues.length > 0 && !compact && (
                            <span style={{ marginLeft: "0.35rem", fontSize: "0.68rem", opacity: 0.85 }}>· {gen.ats_report.issues.length} issues</span>
                          )}
                        </span>
                      )}
                    </div>

                    {isSelectMode ? (
                      /* Checkbox when in select mode */
                      <div
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          width: "24px",
                          height: "24px",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => toggleCheck(gen.id, e)}
                          style={{
                            accentColor: "var(--color-primary)",
                            width: "16px",
                            height: "16px",
                            cursor: "pointer",
                          }}
                        />
                      </div>
                    ) : (
                      /* "X" Delete Button when not in select mode */
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
                    )}
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
