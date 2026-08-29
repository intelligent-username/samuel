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
    <div
      style={{
        marginTop: "0.75rem",
        display: "flex",
        gap: "0.75rem",
        flexWrap: "wrap",
        alignItems: "center",
        flexShrink: 0,
      }}
    >
      <button
        type="button"
        onClick={handleDownload}
        disabled={downloading}
        className="btn btn-primary"
        style={{
          height: "2.4rem",
          padding: "0 1.25rem",
          display: "inline-flex",
          alignItems: "center",
          gap: "0.4rem",
        }}
      >
        {downloading && <span className="spinner spinner-sm" />}
        Download PDF
      </button>

      <button
        type="button"
        onClick={onToggleJd}
        className={`btn${jdOpen ? " btn-primary" : ""}`}
        style={{
          height: "2.4rem",
          padding: "0 1.25rem",
          display: "inline-flex",
          alignItems: "center",
        }}
      >
        {jdOpen ? "Hide Job Description" : "Show Job Description"}
      </button>

      <button
        type="button"
        onClick={onToggleHistory}
        className={`btn${historyOpen ? " btn-primary" : ""}`}
        style={{
          height: "2.4rem",
          padding: "0 1.25rem",
          display: "inline-flex",
          alignItems: "center",
        }}
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
                  : "rgba(217, 119, 6, 0.15)",
              borderColor: atsScore >= 80 ? "#1a9e6e" : "#d97706",
              color: atsScore >= 80 ? "#1a9e6e" : "#d97706",
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
