"use client";

import React, { useEffect, useRef, useState } from "react";
import { getDownloadUrl, getPreviewHtmlUrl } from "@/lib/api";

interface ResumePreviewerProps {
  generationId: string;
  generationTitle: string | null;
  pdfBlobUrl: string | null;
  onError: (err: string) => void;
}

export default function ResumePreviewer({
  generationId,
  generationTitle,
  pdfBlobUrl,
  onError,
}: ResumePreviewerProps) {
  const [previewMode, setPreviewMode] = useState<"sheet" | "pdf">("pdf");
  const [zoomLevel, setZoomLevel] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isZooming, setIsZooming] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef(100);
  zoomRef.current = zoomLevel;

  const pdfFileName = generationTitle?.trim()
    ? `${generationTitle.trim().replace(/[/\\:*?"<>|]/g, "").replace(/\.pdf$/i, "")}.pdf`
    : "generated_resume.pdf";

  const clamp = (z: number) => Math.min(220, Math.max(50, Math.round(z)));

  // Zoom: touch pinch only — scoped to the stage element
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;

    let startDist: number | null = null;
    let startZoom = 100;

    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length < 2) return;
      setIsZooming(true);
      startDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      startZoom = zoomRef.current;
    };
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length < 2 || startDist === null) return;
      e.preventDefault();
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      setZoomLevel(clamp(startZoom * (dist / startDist)));
    };
    const onTouchEnd = () => {
      startDist = null;
      setIsZooming(false);
    };

    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchmove", onTouchMove, { passive: false });
    el.addEventListener("touchend", onTouchEnd);
    el.addEventListener("touchcancel", onTouchEnd);
    return () => {
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchmove", onTouchMove);
      el.removeEventListener("touchend", onTouchEnd);
      el.removeEventListener("touchcancel", onTouchEnd);
    };
  }, []);

  // Escape key to exit fullscreen
  useEffect(() => {
    if (!isFullscreen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKeyDown, { capture: true });
    return () => window.removeEventListener("keydown", onKeyDown, { capture: true });
  }, [isFullscreen]);

  const iframePointerEvents = isZooming ? "none" as const : "auto" as const;

  return (
    <div
      className="nm-card"
      onMouseEnter={() => stageRef.current?.focus({ preventScroll: true })}
      style={{
        padding: 0,
        overflow: "hidden",
        border: "1px solid var(--color-border)",
        borderRadius: isFullscreen ? 0 : "12px",
        display: "flex",
        flexDirection: "column",
        flex: 1,
        minHeight: 0,
        background: "var(--color-card)",
        transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
        ...(isFullscreen
          ? {
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              width: "100vw",
              height: "100vh",
              maxHeight: "100vh",
              zIndex: 9999,
              boxShadow: "none",
            }
          : {}),
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0.45rem 0.85rem",
          borderBottom: "1px solid var(--color-border)",
          background: "rgba(0, 0, 0, 0.12)",
          gap: "0.6rem",
          flexWrap: "wrap",
          minHeight: "2.4rem",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              fontSize: "0.82rem",
              fontWeight: 600,
              color: "var(--color-foreground)",
              minWidth: 0,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, opacity: 0.85 }} aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <span className="truncate" style={{ maxWidth: isFullscreen ? "400px" : "200px" }} title={pdfFileName}>
              {pdfFileName}
            </span>
          </div>
          <div style={{ display: "inline-flex", background: "rgba(0, 0, 0, 0.2)", padding: "2px", borderRadius: "7px", border: "1px solid var(--color-border)" }}>
            <button type="button" onClick={() => setPreviewMode("pdf")} className={`btn btn-xs ${previewMode === "pdf" ? "btn-primary" : "btn-ghost"}`} style={{ borderRadius: "5px", fontSize: "0.72rem", padding: "0.18rem 0.55rem", border: "none", cursor: "pointer", fontWeight: 600 }}>
              PDF Stream
            </button>
            <button type="button" onClick={() => setPreviewMode("sheet")} className={`btn btn-xs ${previewMode === "sheet" ? "btn-primary" : "btn-ghost"}`} style={{ borderRadius: "5px", fontSize: "0.72rem", padding: "0.18rem 0.55rem", border: "none", cursor: "pointer", fontWeight: 600 }}>
              Paper Sheet
            </button>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <button type="button" onClick={() => setIsFullscreen((f) => !f)} className={`btn btn-xs ${isFullscreen ? "btn-primary" : "btn-ghost"}`} style={{ height: "1.75rem", padding: "0 0.55rem", display: "inline-flex", alignItems: "center", gap: "0.35rem", fontSize: "0.74rem", borderRadius: "6px", fontWeight: 600 }} title={isFullscreen ? "Exit Fullscreen (Esc)" : "Fullscreen Preview"}>
            {isFullscreen ? (
              <><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg><span>Exit</span></>
            ) : (
              <><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" /></svg><span>Fullscreen</span></>
            )}
          </button>
        </div>
      </div>

      {/* Stage */}
      <div
        ref={stageRef}
        tabIndex={-1}
        style={{
          flex: 1,
          minHeight: 0,
          overflow: "hidden",
          background: "linear-gradient(180deg, rgba(0,0,0,0.04) 0%, rgba(0,0,0,0.12) 100%)",
          position: "relative",
          outline: "none",
        }}
      >
        {previewMode === "sheet" ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: "100%",
                maxWidth: isFullscreen ? "min(1050px, 92vw)" : "700px",
                height: "100%",
                transform: `scale(${zoomLevel / 100})`,
                transformOrigin: "top center",
                transition: "transform 0.18s ease-out",
                borderRadius: "6px",
                boxShadow: "0 18px 45px -8px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.12)",
                background: "#ffffff",
                overflow: "hidden",
              }}
            >
              <iframe
                src={getPreviewHtmlUrl(generationId)}
                title="Resume Sheet Preview"
                style={{ width: "100%", height: "100%", border: "none", display: "block", background: "#ffffff", pointerEvents: iframePointerEvents }}
                onError={() => onError("Preview sheet failed to load. Try PDF stream instead.")}
              />
            </div>
          </div>
        ) : (
          <iframe
            src={`${pdfBlobUrl || getDownloadUrl(generationId)}#toolbar=0&navpanes=0&view=FitH`}
            title="Resume PDF Stream"
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              border: "none",
              background: "#fff",
              transform: `scale(${zoomLevel / 100})`,
              transformOrigin: "top center",
              transition: "transform 0.18s ease-out",
              pointerEvents: iframePointerEvents,
            }}
            onError={() => onError("PDF preview failed to load.")}
          />
        )}
      </div>
    </div>
  );
}
