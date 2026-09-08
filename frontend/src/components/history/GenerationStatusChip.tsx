"use client";

import React from "react";
import type { Generation } from "@/lib/types";

export const STATUS_META: Record<string, { label: string; color: string }> = {
  pending:   { label: "Pending",   color: "var(--color-muted-fg)" },
  running:   { label: "Running",   color: "var(--color-primary)" },
  completed: { label: "Completed", color: "var(--color-success)" },
  failed:    { label: "Failed",    color: "var(--color-destructive)" },
};

interface GenerationStatusChipProps {
  gen: Generation;
  compact?: boolean;
  actionGenId: string | null;
  hoveredTagGenId: string | null;
  onHoverTag: (id: string | null) => void;
  onStop: (gen: Generation, e: React.MouseEvent) => void;
  onRetry: (gen: Generation, e: React.MouseEvent) => void;
}

export default function GenerationStatusChip({
  gen,
  compact = false,
  actionGenId,
  hoveredTagGenId,
  onHoverTag,
  onStop,
  onRetry,
}: GenerationStatusChipProps) {
  const meta = STATUS_META[gen.status] ?? STATUS_META.pending;
  const isHovered = hoveredTagGenId === gen.id;
  const isActionBusy = actionGenId === gen.id;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.35rem" }}>
      {gen.status === "running" ? (
        <button
          type="button"
          onClick={(e) => onStop(gen, e)}
          onMouseEnter={() => onHoverTag(gen.id)}
          onMouseLeave={() => onHoverTag(null)}
          disabled={isActionBusy}
          title={isHovered ? "Click to stop generation" : "Running (click to stop)"}
          className="chip"
          style={{
            cursor: "pointer",
            fontSize: "0.7rem",
            padding: "0.15rem 0.55rem",
            transition: "all 0.15s ease",
            fontWeight: 600,
            background: isHovered ? "rgba(220, 38, 38, 0.14)" : "var(--color-card)",
            color: isHovered ? "var(--color-destructive)" : "var(--color-primary)",
            borderColor: isHovered ? "var(--color-destructive)" : "var(--color-primary)",
          }}
        >
          {isActionBusy ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
              <span className="spinner spinner-xs" />
              Stopping…
            </span>
          ) : isHovered ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
              <span style={{ fontSize: "0.6rem" }}>■</span> Stop
            </span>
          ) : (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
              <span className="spinner spinner-xs" />
              Running
            </span>
          )}
        </button>
      ) : gen.status === "failed" ? (
        <button
          type="button"
          onClick={(e) => onRetry(gen, e)}
          onMouseEnter={() => onHoverTag(gen.id)}
          onMouseLeave={() => onHoverTag(null)}
          disabled={isActionBusy}
          title={isHovered ? "Click to retry generation" : "Failed (click to retry)"}
          className="chip"
          style={{
            cursor: "pointer",
            fontSize: "0.7rem",
            padding: "0.15rem 0.55rem",
            transition: "all 0.15s ease",
            fontWeight: 600,
            background: isHovered ? "rgba(0, 102, 153, 0.16)" : "var(--color-card)",
            color: isHovered ? "var(--color-primary)" : "var(--color-destructive)",
            borderColor: isHovered ? "var(--color-primary)" : "rgba(220, 38, 38, 0.4)",
          }}
        >
          {isActionBusy ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
              <span className="spinner spinner-sm" style={{ width: "9px", height: "9px", borderWidth: "1.5px" }} />
              Retrying…
            </span>
          ) : isHovered ? (
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
                ? "var(--color-success)"
                : gen.ats_report.score > 45
                ? "var(--color-accent)"
                : "var(--color-destructive)",
            borderColor:
              gen.ats_report.score >= 80
                ? "var(--color-success)"
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
            <span style={{ marginLeft: "0.35rem", fontSize: "0.68rem", opacity: 0.85 }}>
              · {gen.ats_report.issues.length} issues
            </span>
          )}
        </span>
      )}
    </div>
  );
}
