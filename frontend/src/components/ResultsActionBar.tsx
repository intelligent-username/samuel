"use client";

import React, { useState } from "react";
import { getDownloadUrl } from "@/lib/api";

interface ResultsActionBarProps {
  generationId: string;
  pdfFileName: string;
  jdOpen: boolean;
  onToggleJd: () => void;
  historyOpen: boolean;
  onToggleHistory: () => void;
  atsScore: number | null;
  onError: (msg: string) => void;
}

export default function ResultsActionBar({
  generationId,
  pdfFileName,
  jdOpen,
  onToggleJd,
  historyOpen,
  onToggleHistory,
  atsScore,
  onError,
}: ResultsActionBarProps) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    try {
      setDownloading(true);
      onError("");
      const res = await fetch(`${getDownloadUrl(generationId)}?download=true`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = blobUrl;
      a.download = pdfFileName;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        if (a.parentNode) a.parentNode.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);
      }, 1500);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to download PDF.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="results-action-bar">
      <button
        type="button"
        onClick={handleDownload}
        disabled={downloading}
        className="btn btn-primary"
      >
        {downloading && <span className="spinner spinner-sm" />}
        Download PDF
      </button>

      <button
        type="button"
        onClick={onToggleJd}
        className="btn btn-primary"
      >
        {jdOpen ? "Hide Job Description" : "Show Job Description"}
      </button>

      <button
        type="button"
        onClick={onToggleHistory}
        className="btn btn-primary"
      >
        {historyOpen ? "Hide History" : "Show History"}
      </button>

      {atsScore !== null && (
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <span className="text-muted text-xs">ATS Score:</span>
          <span
            className="chip"
            style={{
              background:
                atsScore >= 80
                  ? "rgba(26, 158, 110, 0.15)"
                  : atsScore > 45
                  ? "rgba(252, 106, 3, 0.15)"
                  : "rgba(153, 27, 27, 0.15)",
              borderColor:
                atsScore >= 80
                  ? "var(--color-success)"
                  : atsScore > 45
                  ? "var(--color-accent)"
                  : "var(--color-destructive)",
              color:
                atsScore >= 80
                  ? "var(--color-success)"
                  : atsScore > 45
                  ? "var(--color-accent)"
                  : "var(--color-destructive)",
              fontWeight: 700,
              fontSize: "0.82rem",
            }}
          >
            {atsScore} / 100
          </span>
        </div>
      )}
    </div>
  );
}
