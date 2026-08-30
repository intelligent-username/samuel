"use client";

import React from "react";

export const LANG_COLORS: Record<string, string> = {
  TypeScript: "#3178c6", JavaScript: "#f7df1e", Python: "#3572a5",
  Rust: "#dea584", Go: "#00add8", Java: "#b07219", "C++": "#f34b7d",
  C: "#555555", HTML: "#e34c26", CSS: "#563d7c", Shell: "#89e051",
  Vue: "#41b883", Svelte: "#ff3e00", Kotlin: "#a97bff", Swift: "#f05138",
  Ruby: "#701516", PHP: "#4f5d95", Dart: "#00b4ab", Scala: "#dc322f",
};

interface LangBarProps {
  languages: Record<string, number> | null | undefined;
}

export default function LangBar({ languages }: LangBarProps) {
  if (!languages || typeof languages !== "object") {
    return <span className="text-muted" style={{ fontSize: "0.7rem", fontStyle: "italic" }}>No language data</span>;
  }
  const total = Object.values(languages).reduce((a, b) => a + b, 0);
  if (total === 0 || Object.keys(languages).length === 0) {
    return <span className="text-muted" style={{ fontSize: "0.7rem", fontStyle: "italic" }}>No language data</span>;
  }
  const entries = Object.entries(languages).sort((a, b) => b[1] - a[1]).slice(0, 8);

  return (
    <div style={{ marginTop: "0.35rem" }}>
      <div style={{ display: "flex", height: "4px", borderRadius: "2px", overflow: "hidden", gap: "1px" }}>
        {entries.map(([lang, bytes]) => (
          <div
            key={lang}
            title={`${lang}: ${((bytes / total) * 100).toFixed(1)}%`}
            style={{ flex: bytes, background: LANG_COLORS[lang] ?? "var(--color-muted-fg)", minWidth: "2px" }}
          />
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.35rem" }}>
        {entries.slice(0, 4).map(([lang, bytes]) => (
          <span key={lang} style={{ display: "flex", alignItems: "center", gap: "0.2rem", fontSize: "0.65rem", color: "var(--color-muted-fg)" }}>
            <span className="indicator-dot" style={{ width: "6px", height: "6px", background: LANG_COLORS[lang] ?? "var(--color-muted-fg)" }} />
            {lang} <span style={{ opacity: 0.6 }}>{((bytes / total) * 100).toFixed(0)}%</span>
          </span>
        ))}
      </div>
    </div>
  );
}
