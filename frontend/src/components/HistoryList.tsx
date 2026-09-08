"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { deleteGeneration, updateGeneration, stopGeneration, retryGeneration } from "@/lib/api";
import type { Generation } from "@/lib/types";
import DeleteConfirmModal from "./history/DeleteConfirmModal";
import GenerationCard from "./history/GenerationCard";

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

  // Deletion state
  const [confirmDeleteGen, setConfirmDeleteGen] = useState<Generation | null>(null);
  const [confirmMultiDelete, setConfirmMultiDelete] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isMultiDeleting, setIsMultiDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Selection state
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

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

  const handleDelete = async () => {
    if (!confirmDeleteGen) return;
    const targetId = confirmDeleteGen.id;
    setDeletingId(targetId);
    setDeleteError(null);
    try {
      await deleteGeneration(targetId);
      if (onDeleted) onDeleted(targetId);
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
      <DeleteConfirmModal
        isOpen={Boolean(confirmDeleteGen || confirmMultiDelete)}
        count={confirmMultiDelete ? selectedIds.size : 1}
        isDeleting={Boolean(deletingId || isMultiDeleting)}
        error={deleteError}
        onCancel={() => {
          setConfirmDeleteGen(null);
          setConfirmMultiDelete(false);
        }}
        onConfirm={confirmMultiDelete ? handleMultiDelete : handleDelete}
      />

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
                className="checkbox-control"
              />
            </label>
          </div>

          {generations.map((gen) => (
            <GenerationCard
              key={gen.id}
              gen={gen}
              compact={compact}
              isChecked={selectedIds.has(gen.id)}
              isSelectMode={isSelectMode}
              actionGenId={actionGenId}
              hoveredTagGenId={hoveredTagGenId}
              onHoverTag={setHoveredTagGenId}
              onClick={handleClickItem}
              onCheck={toggleCheck}
              onDeleteRequest={setConfirmDeleteGen}
              onStop={handleStop}
              onRetry={handleRetry}
              onUpdated={onUpdated}
              updateGenerationFn={updateGeneration}
            />
          ))}
        </div>
      )}
    </>
  );
}
