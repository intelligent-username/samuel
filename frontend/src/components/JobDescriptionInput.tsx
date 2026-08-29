"use client";

import React from "react";

interface JobDescriptionInputProps {
  jobDesc: string;
  onChange: (text: string) => void;
  onEnterGenerate: () => void;
  overLimit: boolean;
  nearLimit: boolean;
  wordCount: number;
  jdLen: number;
  jdTrimLen: number;
  charsRemaining: number;
  maxChars: number;
}

export default function JobDescriptionInput({
  jobDesc,
  onChange,
  onEnterGenerate,
  overLimit,
  nearLimit,
  wordCount,
  jdLen,
  jdTrimLen,
  charsRemaining,
  maxChars,
}: JobDescriptionInputProps) {
  return (
    <div
      className="nm-card"
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        padding: "1.5rem",
        minHeight: "560px",
      }}
    >
      <h3 style={{ margin: "0 0 0.85rem", fontSize: "1rem", fontWeight: 700 }}>
        Job Description
      </h3>
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <textarea
          id="job-description"
          rows={18}
          placeholder="Paste the target job description here..."
          value={jobDesc}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
              e.preventDefault();
              onEnterGenerate();
            }
          }}
          maxLength={maxChars}
          className="textarea"
          style={{
            flex: 1,
            minHeight: "440px",
            fontSize: "0.875rem",
            lineHeight: "1.65",
            resize: "none",
          }}
        />
        <p
          className="text-xs text-muted"
          style={{
            marginTop: "0.6rem",
            fontFamily: "monospace",
            color:
              overLimit || nearLimit
                ? "var(--color-destructive)"
                : "var(--color-muted-fg)",
            fontWeight: nearLimit ? 600 : 400,
          }}
        >
          {wordCount} words · {jdLen.toLocaleString()} / {maxChars.toLocaleString()} chars
          {nearLimit && !overLimit && ` · ${charsRemaining} remaining`}
          {overLimit && ` · over by ${Math.abs(charsRemaining)}`}
        </p>
        {overLimit && (
          <p
            className="text-xs"
            style={{ color: "var(--color-destructive)", marginTop: "0.25rem" }}
          >
            Job description too long (max {maxChars.toLocaleString()} characters)
          </p>
        )}
        {jdTrimLen > 0 && jdTrimLen < 10 && (
          <p
            className="text-xs"
            style={{ color: "var(--color-destructive)", marginTop: "0.25rem" }}
          >
            Job description too short (min 10 characters)
          </p>
        )}
      </div>
    </div>
  );
}
