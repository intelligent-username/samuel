"use client";

import React, { useEffect } from "react";

interface AtsDetailsModalProps {
  open: boolean;
  onClose: () => void;
  atsScore: number | null;
  currentThreshold: number | null;
  atsScores: number[];
  iterations: Array<{ iteration: number; score: number }>;
  exitReason: string | null;
}

export default function AtsDetailsModal({
  open,
  onClose,
  atsScore,
  currentThreshold,
  atsScores,
  iterations,
  exitReason,
}: AtsDetailsModalProps) {
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const targetScore = currentThreshold ?? atsScores[0] ?? 80;

  return (
    <div
      className="modal-backdrop"
      style={{ zIndex: 1000, padding: "1.5rem" }}
      onClick={onClose}
    >
      <div
        className="nm-card custom-scrollbar"
        style={{
          maxWidth: "460px",
          width: "100%",
          maxHeight: "85vh",
          overflowY: "auto",
          position: "relative",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="panel-header" style={{ marginBottom: 0, paddingBottom: "0.5rem" }}>
          <div>
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, margin: 0 }}>
              ATS Score Details
            </h3>
            <p className="text-muted text-xs" style={{ margin: "0.2rem 0 0" }}>
              Target: {targetScore} / 100
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn btn-ghost btn-xs close-btn"
            style={{ fontSize: "1.1rem", padding: "0.2rem 0.5rem" }}
            title="Close (Esc)"
          >
            ×
          </button>
        </div>

        {exitReason && (
          <div
            className="nm-card"
            style={{
              padding: "0.75rem 1rem",
              fontSize: "0.85rem",
              borderColor:
                exitReason === "threshold_met"
                  ? "var(--color-success)"
                  : exitReason === "stagnation"
                  ? "#f59e0b"
                  : "var(--color-border)",
            }}
          >
            {exitReason === "threshold_met" && (
              <span style={{ color: "var(--color-success)", fontWeight: 600 }}>
                ✓ Target met ({atsScore}/{targetScore})
              </span>
            )}
            {exitReason === "stagnation" && (
              <span>Paused: improvement stalled below 3% for 3 tries (final {atsScore})</span>
            )}
            {exitReason === "max_iterations" && (
              <span>Reached max tries: final {atsScore}/{targetScore}</span>
            )}
            {exitReason === "single_pass" && (
              <span>Single pass: completed (final {atsScore}/{targetScore})</span>
            )}
          </div>
        )}

        {iterations.length > 0 ? (
          <div>
            <h4 style={{ fontSize: "0.8rem", fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--color-muted-fg)", marginBottom: "0.5rem" }}>
              Iterations
            </h4>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              {iterations.map((it) => {
                const isMet = currentThreshold !== null && it.score >= currentThreshold;
                return (
                  <li
                    key={it.iteration}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "0.4rem 0.6rem",
                      borderRadius: 6,
                      background: "var(--color-muted)",
                      border: "1px solid var(--color-border)",
                      fontSize: "0.85rem",
                    }}
                  >
                    <span className="font-mono">
                      Iter {it.iteration} — {it.score}/{targetScore}
                    </span>
                    <span
                      style={{
                        fontWeight: 600,
                        fontSize: "0.78rem",
                        color: isMet ? "var(--color-success)" : "var(--color-muted-fg)",
                      }}
                    >
                      {isMet ? "✓ met" : "retrying"}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : (
          <p className="text-muted text-xs">No iteration history recorded.</p>
        )}
      </div>
    </div>
  );
}
