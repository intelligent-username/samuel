"use client";

import React from "react";
import Borromean3DViewer from "@/components/Borromean3DViewer";

interface GenerationProgressCardProps {
  stopping: boolean;
  onStop: () => void;
}

export default function GenerationProgressCard({
  stopping,
  onStop,
}: GenerationProgressCardProps) {
  return (
    <div
      className="nm-card"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "1.2rem",
        padding: "2.5rem 1.5rem",
        textAlign: "center",
        marginBottom: "1.5rem",
      }}
    >
      <Borromean3DViewer height={140} width={140} interactive={false} speed="normal" />
      <div>
        <p style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.35rem" }}>
          Generating your tailored resume…
        </p>
        <p className="text-muted" style={{ fontSize: "0.8rem" }}>
          Matching projects → rewriting → ATS check
        </p>
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
