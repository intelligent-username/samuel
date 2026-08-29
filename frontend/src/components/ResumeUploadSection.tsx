"use client";

import React, { useRef, useState, useEffect } from "react";
import type { Resume } from "@/lib/types";

interface ResumeUploadSectionProps {
  resumes: Resume[];
  selectedResumeId: string;
  onSelectResume: (id: string) => void;
  onUploadFile: (file: File) => void;
  onRemoveResume: (resume: Resume, e: React.MouseEvent) => void;
}

export default function ResumeUploadSection({
  resumes,
  selectedResumeId,
  onSelectResume,
  onUploadFile,
  onRemoveResume,
}: ResumeUploadSectionProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [resumeMenuOpen, setResumeMenuOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const resumeMenuRef = useRef<HTMLDivElement>(null);

  const selectedResume = resumes.find((r) => r.id === selectedResumeId);
  const uploadedResumes = resumes.filter((r) => !r.is_generated);
  const generatedResumes = resumes.filter((r) => r.is_generated);

  const formatResumeDate = (iso: string) => {
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      const isCurrentYear = d.getFullYear() === new Date().getFullYear();
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: isCurrentYear ? undefined : "numeric",
      });
    } catch {
      return "";
    }
  };

  useEffect(() => {
    if (!resumeMenuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (resumeMenuRef.current && !resumeMenuRef.current.contains(e.target as Node)) {
        setResumeMenuOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setResumeMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [resumeMenuOpen]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onUploadFile(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUploadFile(file);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div
      className="nm-card"
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        padding: "1.5rem",
        minHeight: "420px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "1.25rem",
        }}
      >
        <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 700 }}>Resume (PDF)</h3>

        {resumes.length > 0 && (
          <div ref={resumeMenuRef} style={{ position: "relative", maxWidth: "260px" }}>
            <button
              id="resume-select"
              type="button"
              onClick={() => setResumeMenuOpen((o) => !o)}
              className="select"
              style={{
                width: "260px",
                maxWidth: "260px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "0.5rem",
                padding: "0.35rem 0.75rem",
                fontSize: "0.8rem",
                background: selectedResume?.is_generated
                  ? "#0a192f"
                  : "var(--color-background)",
                borderColor: selectedResume?.is_generated
                  ? "var(--color-primary)"
                  : "var(--color-border)",
                color: selectedResume?.is_generated
                  ? "#93c5fd"
                  : "var(--color-foreground)",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <span
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  flex: 1,
                }}
              >
                {selectedResume?.original_filename ?? "Select resume"}
              </span>
              <span
                style={{
                  fontSize: "0.65rem",
                  transform: resumeMenuOpen ? "rotate(180deg)" : "rotate(0deg)",
                }}
              >
                ▼
              </span>
            </button>

            {resumeMenuOpen && (
              <div
                className="nm-card custom-scrollbar"
                style={{
                  position: "absolute",
                  top: "calc(100% + 6px)",
                  right: 0,
                  width: "340px",
                  maxWidth: "min(340px, 92vw)",
                  maxHeight: "340px",
                  overflowY: "auto",
                  padding: "0.35rem",
                  zIndex: 50,
                  background: "var(--color-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "10px",
                }}
              >
                {(uploadedResumes.length > 0 && generatedResumes.length > 0
                  ? [
                      { label: "Uploaded Resumes", items: uploadedResumes },
                      { label: "Generated Resumes", items: generatedResumes },
                    ]
                  : [{ label: null, items: resumes }]
                ).map((group) => (
                  <div key={group.label ?? "all"}>
                    {group.label && (
                      <div
                        style={{
                          fontSize: "0.62rem",
                          fontWeight: 700,
                          color: "var(--color-muted-fg)",
                          textTransform: "uppercase",
                          padding: "0.45rem 0.55rem 0.2rem",
                        }}
                      >
                        {group.label}
                      </div>
                    )}
                    {group.items.map((r) => (
                      <div
                        key={r.id}
                        onClick={() => {
                          onSelectResume(r.id);
                          setResumeMenuOpen(false);
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                          padding: "0.45rem 0.5rem 0.45rem 0.6rem",
                          borderRadius: "6px",
                          cursor: "pointer",
                          background:
                            r.id === selectedResumeId
                              ? "var(--color-muted)"
                              : "transparent",
                          border:
                            r.id === selectedResumeId
                              ? "1px solid var(--color-border)"
                              : "1px solid transparent",
                          marginBottom: "2px",
                        }}
                      >
                        <span
                          title={r.original_filename}
                          style={{
                            flex: 1,
                            minWidth: 0,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            fontSize: "0.78rem",
                            fontWeight: r.id === selectedResumeId ? 600 : 400,
                            color: r.is_generated
                              ? "#93c5fd"
                              : "var(--color-foreground)",
                          }}
                        >
                          {r.original_filename}
                        </span>
                        <span
                          style={{
                            fontSize: "0.68rem",
                            color: "var(--color-muted-fg)",
                            opacity: 0.72,
                          }}
                        >
                          {formatResumeDate(r.created_at)}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => onRemoveResume(r, e)}
                          title="Remove option from dropdown"
                          aria-label={`Remove ${r.original_filename} from dropdown`}
                          style={{
                            width: "22px",
                            height: "22px",
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: "transparent",
                            border: "none",
                            color: "var(--color-muted-fg)",
                            cursor: "pointer",
                            fontSize: "0.95rem",
                            lineHeight: 1,
                          }}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "340px",
          border: `2px dashed ${
            isDragging ? "var(--color-primary)" : "var(--color-border)"
          }`,
          borderRadius: "12px",
          padding: "2.5rem 1.5rem",
          textAlign: "center",
          background: isDragging ? "var(--color-muted)" : "transparent",
          gap: "1.25rem",
        }}
      >
        <svg
          width="44"
          height="44"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ opacity: 0.5, color: "var(--color-primary)" }}
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <line x1="9" y1="15" x2="12" y2="12" />
          <line x1="15" y1="15" x2="12" y2="12" />
        </svg>
        <div>
          <p
            style={{
              fontSize: "0.95rem",
              fontWeight: 600,
              margin: "0 0 0.35rem",
              color: "var(--color-foreground)",
            }}
          >
            {isDragging ? "Drop your PDF here" : "Drag & drop your resume PDF here"}
          </p>
          <p className="text-muted text-xs" style={{ margin: 0 }}>
            PDF files up to 10MB
          </p>
        </div>
        <button
          id="upload-resume-btn"
          onClick={() => fileRef.current?.click()}
          className="btn btn-primary btn-sm"
          style={{ padding: "0.45rem 1.25rem" }}
        >
          Browse File
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
      </div>
    </div>
  );
}
