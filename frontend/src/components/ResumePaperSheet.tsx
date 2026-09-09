"use client";

import React, { useMemo } from "react";
import { parseResumeText, type ParsedResume, type ResumeEntry } from "@/lib/resume-parser";
import { PhoneIcon, MailIcon, GithubIcon, LinkedinIcon, GlobeIcon } from "@/components/ResumeIcons";

interface ResumePaperSheetProps {
  resumeText: string | null;
  candidateNameFallback?: string | null;
}

export default function ResumePaperSheet({
  resumeText,
  candidateNameFallback,
}: ResumePaperSheetProps) {
  const parsed: ParsedResume = useMemo(() => {
    return parseResumeText(resumeText || "");
  }, [resumeText]);

  const displayName = parsed.name || candidateNameFallback?.replace(/\.pdf$/i, "") || "Professional Resume";

  if (!resumeText || !resumeText.trim()) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center text-slate-400">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mb-2 opacity-60">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        <p className="text-xs font-medium">Resume preview is loading…</p>
      </div>
    );
  }

  return (
    <article
      className="resume-paper-document"
      style={{
        width: "100%",
        maxWidth: "800px",
        minHeight: "1050px",
        margin: "0 auto",
        background: "#ffffff",
        color: "#111827",
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        padding: "2.25rem 2.75rem",
        boxSizing: "border-box",
        lineHeight: 1.4,
        boxShadow: "0 18px 40px -12px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(0, 0, 0, 0.06)",
        borderRadius: "4px",
      }}
    >
      {/* ─── Header: Name & Contact ────────────────────────────────────────── */}
      <header style={{ textAlign: "center", marginBottom: "0.9rem", borderBottom: "1.5px solid #111827", paddingBottom: "0.65rem" }}>
        <h1
          style={{
            fontSize: "1.35rem",
            fontWeight: 800,
            letterSpacing: "0.03em",
            textTransform: "uppercase",
            color: "#111827",
            margin: "0 0 0.35rem 0",
          }}
        >
          {displayName}
        </h1>

        {parsed.contact.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.3rem 0.9rem",
              fontSize: "0.76rem",
              color: "#4b5563",
              fontWeight: 500,
            }}
          >
            {parsed.contact.map((item, idx) => (
              <span key={idx} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
                {renderContactIcon(item)}
                {renderContactLink(item, displayName)}
              </span>
            ))}
          </div>
        )}
      </header>

      {/* ─── Sections ──────────────────────────────────────────────────────── */}
      {parsed.sections.map((section, sIdx) => (
        <section key={sIdx} style={{ marginBottom: "0.9rem" }}>
          <h2
            style={{
              fontSize: "0.82rem",
              fontWeight: 800,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#111827",
              borderBottom: "1.5px solid #111827",
              paddingBottom: "2px",
              marginTop: "0.75rem",
              marginBottom: "0.45rem",
            }}
          >
            {section.title}
          </h2>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {section.entries.map((entry, eIdx) => (
              <ResumeEntryCard key={eIdx} entry={entry} isSkillsSection={/skills/i.test(section.title)} />
            ))}
          </div>
        </section>
      ))}
    </article>
  );
}

function ResumeEntryCard({
  entry,
  isSkillsSection,
}: {
  entry: ResumeEntry;
  isSkillsSection: boolean;
}) {
  const hasRow1 = entry.title || entry.meta;
  const hasRow2 = entry.subtitle || entry.subMeta;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.1rem" }}>
      {/* Row 1: Title (left) & Meta (right) */}
      {hasRow1 && (
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: "0.2rem 0.75rem" }}>
          {entry.title && (
            <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "#111827" }}>
              {entry.title}
            </span>
          )}
          {entry.meta && (
            <span style={{ fontSize: "0.78rem", fontWeight: 500, fontStyle: "italic", color: "#4b5563", whiteSpace: "nowrap", marginLeft: "auto" }}>
              {entry.meta}
            </span>
          )}
        </div>
      )}

      {/* Row 2: Subtitle (left, italic) & SubMeta (right, italic) */}
      {hasRow2 && (
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: "0.2rem 0.75rem" }}>
          {entry.subtitle && (
            <span style={{ fontSize: "0.80rem", fontWeight: 500, fontStyle: "italic", color: "#374151" }}>
              {entry.subtitle}
            </span>
          )}
          {entry.subMeta && (
            <span style={{ fontSize: "0.76rem", fontWeight: 500, fontStyle: "italic", color: "#6b7280", whiteSpace: "nowrap", marginLeft: "auto" }}>
              {entry.subMeta}
            </span>
          )}
        </div>
      )}

      {/* Text lines */}
      {entry.textLines.map((tLine, tIdx) => {
        if (isSkillsSection && tLine.includes(":")) {
          const [cat, items] = tLine.split(/:\s*(.+)/);
          return (
            <div key={tIdx} style={{ fontSize: "0.78rem", color: "#1f2937", lineHeight: 1.45 }}>
              <strong style={{ color: "#111827", fontWeight: 700 }}>{cat}: </strong>
              <span>{items || ""}</span>
            </div>
          );
        }
        return (
          <p key={tIdx} style={{ margin: 0, fontSize: "0.78rem", color: "#374151", lineHeight: 1.45 }}>
            {tLine}
          </p>
        );
      })}

      {/* Bullets */}
      {entry.bullets.length > 0 && (
        <ul style={{ margin: "0.1rem 0 0 0", paddingLeft: "1.05rem", listStyleType: "disc" }}>
          {entry.bullets.map((bullet, bIdx) => (
            <li
              key={bIdx}
              style={{
                fontSize: "0.78rem",
                color: "#1f2937",
                lineHeight: 1.42,
                marginBottom: "0.15rem",
                paddingLeft: "0.1rem",
              }}
            >
              {bullet}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function renderContactIcon(item: string) {
  if (/\+?\d[\d\s().-]{7,}\d/.test(item)) return <PhoneIcon />;
  if (item.includes("@")) return <MailIcon />;
  if (/github/i.test(item)) return <GithubIcon />;
  if (/linkedin/i.test(item)) return <LinkedinIcon />;
  if (/portfolio|website|\.dev|\.io|\.com/i.test(item)) return <GlobeIcon />;
  return null;
}

function renderContactLink(item: string, candidateName: string) {
  const cleanName = candidateName.toLowerCase().replace(/[^a-z0-9]/g, "");

  if (/\+?\d[\d\s().-]{7,}\d/.test(item)) {
    return <a href={`tel:${item.replace(/[^\d+]/g, "")}`} style={{ color: "inherit", textDecoration: "none" }} className="hover:underline">{item}</a>;
  }
  if (item.includes("@")) {
    return <a href={`mailto:${item}`} style={{ color: "inherit", textDecoration: "none" }} className="hover:underline">{item}</a>;
  }
  if (/github/i.test(item)) {
    const href = item.includes("http") ? item : `https://github.com/${cleanName || "varak"}`;
    return <a href={href} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }} className="hover:underline">GitHub</a>;
  }
  if (/linkedin/i.test(item)) {
    const href = item.includes("http") ? item : `https://linkedin.com/in/${cleanName || "varaktanashian"}`;
    return <a href={href} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }} className="hover:underline">LinkedIn</a>;
  }
  if (/portfolio/i.test(item)) {
    return <a href="https://varak.dev" target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }} className="hover:underline">Portfolio</a>;
  }
  if (/^https?:\/\//i.test(item)) {
    return <a href={item} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }} className="hover:underline">{item.replace(/^https?:\/\/(?:www\.)?/, "")}</a>;
  }

  return <span>{item}</span>;
}
