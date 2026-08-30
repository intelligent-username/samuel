"use client";

import React from "react";
import BorromeanLoader from "@/components/BorromeanLoader";

interface JobDescriptionDrawerProps {
  open: boolean;
  onClose: () => void;
  jobDescription: string | null;
  loading: boolean;
  copied: boolean;
  onCopy: () => void;
}

export default function JobDescriptionDrawer({
  open,
  onClose,
  jobDescription,
  loading,
  copied,
  onCopy,
}: JobDescriptionDrawerProps) {
  if (!open) return null;

  const charCount = jobDescription ? jobDescription.length.toLocaleString() : 0;
  const wordCount = jobDescription
    ? jobDescription.trim().split(/\s+/).filter(Boolean).length
    : 0;

  return (
    <aside
      className="side-panel-left"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="side-dialog-panel nm-card"
        style={{ animation: "jdDialogIn 0.28s cubic-bezier(0.16, 1, 0.3, 1)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="panel-header">
          <div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>
              Target Job Description
            </h3>
            <p className="text-muted text-xs" style={{ margin: "0.2rem 0 0" }}>
              {jobDescription
                ? `${charCount} characters · ${wordCount} words`
                : "Job description for this resume"}
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            {jobDescription && (
              <button
                type="button"
                onClick={onCopy}
                className="btn btn-ghost btn-xs"
                style={{ fontSize: "0.72rem", padding: "0.25rem 0.5rem" }}
                title="Copy job description"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="btn btn-ghost btn-xs close-btn"
              title="Close (Esc)"
            >
              ×
            </button>
          </div>
        </div>

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            maxHeight: "calc(100vh - 10rem)",
            fontSize: "0.85rem",
            lineHeight: "1.65",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            padding: "0.5rem 0.4rem 0.5rem 0",
            color: "var(--color-foreground)",
          }}
          className="custom-scrollbar"
        >
          {jobDescription ? (
            jobDescription
          ) : loading ? (
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                padding: "3rem 0",
              }}
            >
              <BorromeanLoader size={72} label="Loading job description…" />
            </div>
          ) : (
            <p className="text-muted">
              No job description available for this generation.
            </p>
          )}
        </div>
      </div>
    </aside>
  );
}
