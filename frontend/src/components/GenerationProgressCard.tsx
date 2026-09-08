"use client";

import React from "react";
import Borromean3DViewer from "@/components/Borromean3DViewer";
import type { StepProgress } from "@/lib/types";

interface GenerationProgressCardProps {
  stopping: boolean;
  onStop: () => void;
  steps: StepProgress[];
  connectionRetrying?: boolean;
}

export default function GenerationProgressCard({
  stopping,
  onStop,
  steps,
  connectionRetrying = false,
}: GenerationProgressCardProps) {
  const runningStep = steps.find((s) => s.status === "running");
  const headline = runningStep?.message || (runningStep?.label ? `${runningStep.label}…` : "Generating your tailored resume…");

  return (
    <div
      className="nm-card"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "1.25rem",
        padding: "2rem 1.5rem",
        textAlign: "center",
        marginBottom: "1.5rem",
      }}
    >
      <Borromean3DViewer height={140} width={140} interactive={false} speed="normal" />

      <div>
        <h3 style={{ fontSize: "1.05rem", fontWeight: 700, margin: "0 0 0.35rem" }}>
          {headline}
        </h3>
        <p className="text-muted" style={{ fontSize: "0.8rem", margin: 0 }}>
          Aligning GitHub projects with job description & optimizing for ATS compatibility
        </p>
        {connectionRetrying && (
          <span
            className="chip"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              marginTop: "0.5rem",
              fontSize: "0.72rem",
              color: "var(--color-primary)",
              borderColor: "var(--color-primary)",
              background: "rgba(0, 102, 153, 0.08)",
            }}
          >
            <span className="spinner spinner-xs" />
            Reconnecting stream (generation running in background)
          </span>
        )}
      </div>

      {/* Step by step timeline */}
      <div
        className="nm-card"
        style={{
          width: "100%",
          maxWidth: "520px",
          padding: "1rem 1.25rem",
          textAlign: "left",
          background: "var(--color-background)",
          borderRadius: "8px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {steps.map((stepItem, idx) => {
            const isDone = stepItem.status === "done";
            const isRunning = stepItem.status === "running";
            const isError = stepItem.status === "error";

            return (
              <div
                key={stepItem.step || idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.65rem",
                  fontSize: "0.84rem",
                }}
              >
                {/* Status Indicator Icon */}
                <div
                  style={{
                    width: "20px",
                    height: "20px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    marginTop: "0.1rem",
                  }}
                >
                  {isDone ? (
                    <span
                      style={{
                        color: "var(--color-success)",
                        fontWeight: 800,
                        fontSize: "0.95rem",
                      }}
                    >
                      ✓
                    </span>
                  ) : isRunning ? (
                    <span className="spinner spinner-xs" />
                  ) : isError ? (
                    <span style={{ color: "var(--color-destructive)", fontWeight: 800 }}>!</span>
                  ) : (
                    <span
                      style={{
                        width: "6px",
                        height: "6px",
                        borderRadius: "50%",
                        background: "var(--color-muted-fg)",
                        opacity: 0.45,
                      }}
                    />
                  )}
                </div>

                {/* Step content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "0.5rem" }}>
                    <span
                      style={{
                        fontWeight: isRunning ? 600 : 500,
                        color: isRunning
                          ? "var(--color-primary)"
                          : isDone
                          ? "var(--color-foreground)"
                          : "var(--color-muted-fg)",
                      }}
                    >
                      {stepItem.label || stepItem.step}
                    </span>
                    {stepItem.summary && (
                      <span
                        className="text-xs"
                        style={{
                          color: isDone ? "var(--color-success)" : "var(--color-muted-fg)",
                          fontSize: "0.75rem",
                          fontWeight: 500,
                        }}
                      >
                        {stepItem.summary}
                      </span>
                    )}
                  </div>
                  {isRunning && stepItem.message && (
                    <p
                      className="text-xs text-muted"
                      style={{
                        margin: "0.15rem 0 0",
                        fontSize: "0.76rem",
                        color: "var(--color-primary)",
                        opacity: 0.85,
                      }}
                    >
                      {stepItem.message}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <button
        type="button"
        onClick={onStop}
        disabled={stopping}
        className="btn btn-sm btn-outline-destructive"
        style={{ marginTop: "0.25rem" }}
      >
        {stopping && <span className="spinner spinner-sm" />}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
          <rect x="4" y="4" width="16" height="16" rx="2" />
        </svg>{" "}
        {stopping ? "Stopping…" : "Stop Generation"}
      </button>
    </div>
  );
}
