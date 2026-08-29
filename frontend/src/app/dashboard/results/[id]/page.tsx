"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { createGenerationStream, getDownloadUrl, fetchGeneration, fetchGenerations, stopGeneration, retryGeneration } from "@/lib/api";
import type { Generation } from "@/lib/types";
import Borromean3DViewer from "@/components/Borromean3DViewer";
import HistoryList from "@/components/HistoryList";

type StepName =
  | "jd_parser"
  | "project_matcher"
  | "resume_writer"
  | "ats_checker";

interface Step {
  step: StepName;
  label: string;
  status: "pending" | "running" | "done" | "error";
}

const STEP_LABELS: Record<StepName, string> = {
  jd_parser:        "Analyzing JD",
  project_matcher:  "Matching projects",
  resume_writer:    "Rewriting resume",
  ats_checker:      "ATS check",
};

const INITIAL_STEPS: Step[] = (
  ["jd_parser", "project_matcher", "resume_writer", "ats_checker"] as StepName[]
).map((s) => ({ step: s, label: STEP_LABELS[s], status: "pending" }));

export default function ResultsPage() {
  const params  = useParams<{ id: string }>();
  const router  = useRouter();

  const [steps, setSteps]               = useState<Step[]>(INITIAL_STEPS);
  const [done, setDone]                 = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [fatalError, setFatalError]     = useState<null | { title: string; detail: string }>(null);
  const [banner, setBanner]             = useState<string | null>(null);
  const [atsScore, setAtsScore]         = useState<number | null>(null);
  const [rewrittenResume, setRewrittenResume] = useState<string | null>(null);
  const [showPreview] = useState(true);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [jdOpen, setJdOpen]             = useState(false);
  const [jobDescription, setJobDescription] = useState<string | null>(null);
  const [loadingJd, setLoadingJd]       = useState(false);
  const [copiedJd, setCopiedJd]         = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const toggleJd = () => {
    if (jdOpen) {
      setJdOpen(false);
      return;
    }
    setJdOpen(true);
    if (!jobDescription) {
      setLoadingJd(true);
      fetchGeneration(params.id)
        .then((gen) => {
          if (gen.job_description_text) setJobDescription(gen.job_description_text);
          setLoadingJd(false);
        })
        .catch(() => setLoadingJd(false));
    }
  };

  const copyJdText = () => {
    if (!jobDescription) return;
    navigator.clipboard.writeText(jobDescription);
    setCopiedJd(true);
    setTimeout(() => setCopiedJd(false), 2000);
  };

  const [historyOpen, setHistoryOpen]   = useState(false);
  const [historyGenerations, setHistoryGenerations] = useState<Generation[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const toggleHistory = () => {
    if (historyOpen) {
      setHistoryOpen(false);
      return;
    }
    setHistoryOpen(true);
    setLoadingHistory(true);
    fetchGenerations()
      .then((data) => {
        setHistoryGenerations(data);
        setLoadingHistory(false);
      })
      .catch(() => setLoadingHistory(false));
  };

  useEffect(() => {
    if (!rewrittenResume) return;
    let active = true;
    fetch(getDownloadUrl(params.id), { credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        if (!active) return;
        const url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
      })
      .catch((err) => {
        console.error("PDF blob fetch failed:", err);
      });
    return () => {
      active = false;
    };
  }, [params.id, rewrittenResume]);

  useEffect(() => {
    if (!jdOpen && !historyOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setJdOpen(false);
        setHistoryOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [jdOpen, historyOpen]);

  const [stopping, setStopping] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const handleStopGeneration = async () => {
    if (stopping) return;
    setStopping(true);
    try {
      esRef.current?.close();
      await stopGeneration(params.id);
      setSteps((prev) => prev.map((s) => s.status === "running" ? { ...s, status: "error" } : s));
      setBanner("Generation stopped by user");
      setDone(true);
    } catch (err) {
      console.error("Failed to stop generation:", err);
    } finally {
      setStopping(false);
    }
  };

  const handleRetryGeneration = async () => {
    if (retrying) return;
    setRetrying(true);
    try {
      esRef.current?.close();
      await retryGeneration(params.id);
      setDone(false);
      setFatalError(null);
      setBanner(null);
      setConnectionError(false);
      setRewrittenResume(null);
      setPdfBlobUrl(null);
      setAtsScore(null);
      setSteps(INITIAL_STEPS);
      startStream();
    } catch (err) {
      console.error("Failed to retry generation:", err);
    } finally {
      setRetrying(false);
    }
  };

  const startStream = useCallback(() => {
    let es: EventSource;
    try {
      es = createGenerationStream(params.id);
    } catch {
      setConnectionError(true);
      return;
    }
    esRef.current = es;

    const parseStep = (e: MessageEvent): StepName | null => {
      try {
        const d = JSON.parse(e.data);
        return typeof d?.step === "string" ? (d.step as StepName) : null;
      } catch {
        return null;
      }
    };

    es.addEventListener("step-start", (e: MessageEvent) => {
      const step = parseStep(e);
      if (!step) return;
      setSteps((prev) =>
        prev.map((s) => s.step === step ? { ...s, status: "running" } : s)
      );
    });
    es.addEventListener("step-done", (e: MessageEvent) => {
      const step = parseStep(e);
      if (!step) return;
      setSteps((prev) =>
        prev.map((s) => s.step === step ? { ...s, status: "done" } : s)
      );
    });
    es.addEventListener("step-error", (e: MessageEvent) => {
      const step = parseStep(e);
      if (!step) return;
      setSteps((prev) =>
        prev.map((s) => s.step === step ? { ...s, status: "error" } : s)
      );
    });
    // Handle warning event from PDF fallback detection
    es.addEventListener("warning", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        if (data?.message) setBanner(data.message);
      } catch {}
    });
    // Terminal error emitted by the backend router's except block.
    // Native EventSource connection errors have no `data` — those are handled by es.onerror.
    es.addEventListener("error", (e: MessageEvent) => {
      if (!(e as any).data) return;
      let msg = "Generation failed";
      try { const d = JSON.parse((e as any).data); if (d?.message) msg = d.message; } catch {}
      setSteps((prev) => prev.map((s) => s.status === "running" ? { ...s, status: "error" } : s));
      setBanner(msg);
      setDone(true);
      es.close();
    });
    es.addEventListener("done", (e: MessageEvent) => {
      let data: any;
      try { data = JSON.parse(e.data); } catch { data = {}; }
      setAtsScore(data.ats_score ?? null);
      // Fallback: if output was missed (race on fast replay), populate from done
      const fallback = data.rewritten_resume ?? data.rewritten_resume_text ?? data.text ?? null;
      if (fallback) setRewrittenResume((prev) => prev ?? fallback);
      setDone(true);
      es.close();
    });
    // Handle the dedicated `output` event that carries the full rewritten text.
    // Backend sends `data` as plain string (rewritten_text), not JSON object.
    // Support both cases: JSON-wrapped string and plain text.
    es.addEventListener("output", (e: MessageEvent) => {
      let text: string;
      try {
        const parsed = JSON.parse(e.data);
        if (typeof parsed === "string") text = parsed;
        else if (parsed && typeof parsed.rewritten_resume === "string") text = parsed.rewritten_resume;
        else if (parsed && typeof parsed.text === "string") text = parsed.text;
        else text = e.data;
      } catch {
        text = e.data;
      }
      if (text) setRewrittenResume(text);
    });

    es.onerror = () => {
      if (!done && !fatalError) {
        setConnectionError(true);
        setDone(true);
        es.close();
      }
    };
  }, [params.id, done, fatalError]);

  useEffect(() => {
    let cancelled = false;
    // Optimistic fetch before opening SSE
    fetchGeneration(params.id)
      .then((gen) => {
        if (cancelled) return;
        if (gen.job_description_text) {
          setJobDescription(gen.job_description_text);
        }
        if (gen.status === "completed" && gen.rewritten_resume_text) {
          setRewrittenResume(gen.rewritten_resume_text);
          if (gen.ats_report && typeof gen.ats_report.score === "number") {
            setAtsScore(gen.ats_report.score);
          }
          setSteps((prev) => prev.map((s) => ({ ...s, status: "done" } as Step)));
          setDone(true);
          return;
        }
        if (gen.status === "failed") {
          // Let stream open or show error
        }
        // Only after successful fetch, open stream (unless we already know completed cached path exists)
        startStream();
      })
      .catch((err: Error) => {
        if (cancelled) return;
        const msg = err.message || "";
        // fetchApi throws Error(err || HTTP status); detect 404 vs 401
        if (msg.includes("404") || msg.includes("Generation not found")) {
          setFatalError({ title: "Generation not found", detail: "Check the URL or go back to history." });
        } else if (msg.includes("401") || msg.toLowerCase().includes("not authenticated") || msg.includes("Not authorized") || msg.includes("403")) {
          setFatalError({ title: "Not authorized", detail: "You do not have access to this generation." });
        } else {
          // Network or other -> still try SSE; SSE onerror will show connection lost
          startStream();
          return;
        }
        setDone(true);
        setSteps((prev) => prev.map((s) => ({ ...s, status: "error" } as Step)));
      });
    return () => { cancelled = true; esRef.current?.close(); };
  }, [params.id]); // do NOT depend on startStream to avoid double-open; call directly

  const allDone  = steps.every((s) => s.status === "done");
  const hasError = steps.some((s) => s.status === "error") || !!fatalError;

  // ── Results body ────────────────────────────────────────────────────────
  return (
    <>
      <style>{`
        @keyframes historyDialogIn {
          0% {
            opacity: 0;
            transform: translateX(18px) scale(0.98);
          }
          100% {
            opacity: 1;
            transform: translateX(0) scale(1);
          }
        }

        @keyframes jdDialogIn {
          0% {
            opacity: 0;
            transform: translateX(-18px) scale(0.98);
          }
          100% {
            opacity: 1;
            transform: translateX(0) scale(1);
          }
        }

        .results-page-shell {
          min-height: 100vh;
          padding: 3rem 1.5rem;
          display: flex;
          justifyContent: center;
          align-items: flex-start;
          width: 100%;
          position: relative;
        }

        .results-main-col {
          position: relative;
          width: 100%;
          max-width: 760px;
          margin: 0 auto;
        }

        @media (min-width: 1300px) {
          .side-panel-left {
            position: absolute;
            top: 0;
            bottom: 0;
            right: calc(100% + 1.75rem);
            width: clamp(320px, calc(50vw - 410px), 420px);
            pointer-events: none;
            z-index: 40;
          }
          .side-panel-left > .side-dialog-panel {
            pointer-events: auto;
            position: sticky;
            top: 2.5rem;
            width: 100%;
            max-height: calc(100vh - 5rem);
            box-shadow: 0 16px 36px -4px rgba(0, 0, 0, 0.6), 0 4px 12px -2px rgba(0, 0, 0, 0.4);
          }

          .side-panel-right {
            position: absolute;
            top: 0;
            bottom: 0;
            left: calc(100% + 1.75rem);
            width: clamp(320px, calc(50vw - 410px), 420px);
            pointer-events: none;
            z-index: 40;
          }
          .side-panel-right > .side-dialog-panel {
            pointer-events: auto;
            position: sticky;
            top: 2.5rem;
            width: 100%;
            max-height: calc(100vh - 5rem);
            box-shadow: 0 16px 36px -4px rgba(0, 0, 0, 0.6), 0 4px 12px -2px rgba(0, 0, 0, 0.4);
          }
        }

        @media (max-width: 1299px) {
          .side-panel-left,
          .side-panel-right {
            position: fixed;
            inset: 0;
            z-index: 90;
            background: rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justifyContent: center;
            padding: 1.25rem;
          }
          .side-panel-left > .side-dialog-panel,
          .side-panel-right > .side-dialog-panel {
            width: 100%;
            max-width: 480px;
            max-height: 85vh;
            box-shadow: 0 20px 45px -5px rgba(0, 0, 0, 0.75);
          }
        }
      `}</style>

      <div className="results-page-shell">
        <div className="results-main-col">
          {/* Job Description Panel (Strictly on the LEFT of the resume) */}
          {jdOpen && (
            <aside
              className="side-panel-left"
              onClick={(e) => {
                if (e.target === e.currentTarget) setJdOpen(false);
              }}
            >
              <div
                className="side-dialog-panel nm-card"
                style={{
                  background: "var(--color-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "14px",
                  padding: "1.25rem",
                  display: "flex",
                  flexDirection: "column",
                  animation: "jdDialogIn 0.28s cubic-bezier(0.16, 1, 0.3, 1)",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", borderBottom: "1px solid var(--color-border)", paddingBottom: "0.75rem" }}>
                  <div>
                    <h3 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>Target Job Description</h3>
                    <p className="text-muted text-xs" style={{ margin: "0.2rem 0 0" }}>
                      {jobDescription
                        ? `${jobDescription.length.toLocaleString()} characters · ${jobDescription.trim().split(/\s+/).filter(Boolean).length} words`
                        : "Job description for this resume"}
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    {jobDescription && (
                      <button
                        type="button"
                        onClick={copyJdText}
                        className="btn btn-ghost btn-xs"
                        style={{ fontSize: "0.72rem", padding: "0.25rem 0.5rem" }}
                        title="Copy job description"
                      >
                        {copiedJd ? "Copied!" : "Copy"}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setJdOpen(false)}
                      className="btn btn-ghost btn-xs"
                      style={{ fontSize: "1.25rem", lineHeight: 1, padding: "0.2rem 0.45rem", borderRadius: "4px" }}
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
                    maxHeight: "calc(100vh - 12rem)",
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
                  ) : loadingJd ? (
                    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", padding: "3rem 0" }}>
                      <span className="spinner spinner-lg" />
                    </div>
                  ) : (
                    <p className="text-muted">No job description available for this generation.</p>
                  )}
                </div>
              </div>
            </aside>
          )}

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.4rem", flexWrap: "wrap", gap: "0.75rem" }}>
              <h1 style={{ fontSize: "1.75rem", fontWeight: 800, margin: 0 }}>
                {fatalError ? "Error" : done && !hasError ? "Resume ready" : done && hasError ? "Generation failed" : "Generating resume…"}
              </h1>
              <button
                type="button"
                onClick={toggleHistory}
                className={`btn btn-sm${historyOpen ? " btn-primary" : ""}`}
              >
                {historyOpen ? "Hide History" : "Show History"}
              </button>
            </div>
            {fatalError && (
              <div className="nm-card" style={{ borderColor:"var(--color-destructive)", marginBottom:"1.5rem" }}>
                <h3 style={{ color:"var(--color-destructive)", margin:"0 0 0.35rem" }}>{fatalError.title}</h3>
                <p className="text-muted" style={{ fontSize:"0.85rem", margin:"0 0 1rem" }}>{fatalError.detail}</p>
                <div style={{ display:"flex", gap:"0.75rem" }}>
                  <button type="button" onClick={toggleHistory} className={`btn btn-sm${historyOpen ? " btn-primary" : ""}`}>
                    {historyOpen ? "Hide History" : "Show History"}
                  </button>
                  <button className="btn btn-sm btn-ghost" onClick={() => router.push("/dashboard")}>← Back to Dashboard</button>
                </div>
              </div>
            )}
            {!fatalError && banner && (
              <div className="nm-card" style={{ borderColor:"var(--color-destructive)", color:"var(--color-destructive)", fontSize:"0.85rem", marginBottom:"1rem" }}>{banner}</div>
            )}
            {!fatalError && !done && !connectionError && (
              <div className="nm-card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1.2rem", padding: "2.5rem 1.5rem", textAlign: "center", marginBottom: "1.5rem" }}>
                <Borromean3DViewer height={140} width={140} interactive={false} speed="normal" />
                <div>
                  <p style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.35rem" }}>Generating your tailored resume…</p>
                  <p className="text-muted" style={{ fontSize: "0.8rem" }}>Matching projects → rewriting → ATS check</p>
                </div>
                <button
                  type="button"
                  onClick={handleStopGeneration}
                  disabled={stopping}
                  className="btn btn-sm"
                  style={{
                    color: "var(--color-destructive)",
                    borderColor: "rgba(220, 38, 38, 0.4)",
                    background: "var(--color-card)",
                    gap: "0.35rem",
                    cursor: "pointer",
                    marginTop: "0.25rem",
                  }}
                >
                  {stopping && <span className="spinner spinner-sm" />}
                  <span style={{ fontSize: "0.65rem" }}>■</span> {stopping ? "Stopping…" : "Stop Generation"}
                </button>
              </div>
            )}

            {rewrittenResume && (
              <>
                <div className="nm-card" style={{ padding: "0.5rem", overflow: "hidden" }}>
                  <iframe
                    src={pdfBlobUrl || getDownloadUrl(params.id)}
                    title="Resume PDF preview"
                    style={{ width: "100%", height: "720px", border: "none", borderRadius: "8px", background: "#fff" }}
                    onError={() => setDownloadError("Preview failed to load. Try downloading instead.")}
                  />
                </div>

                <div style={{ marginTop: "1.25rem", display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
                  <a
                    href={getDownloadUrl(params.id)}
                    download="resume.pdf"
                    className="btn btn-primary"
                    onClick={() => setDownloadError(null)}
                    style={{ textDecoration: "none", height: "2.4rem", padding: "0 1.25rem", display: "inline-flex", alignItems: "center" }}
                  >
                    Download PDF
                  </a>
                  <button
                    type="button"
                    onClick={toggleJd}
                    className={`btn${jdOpen ? " btn-primary" : ""}`}
                    style={{ height: "2.4rem", padding: "0 1.25rem", display: "inline-flex", alignItems: "center" }}
                  >
                    {jdOpen ? "Hide Job Description" : "Show Job Description"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => router.push("/dashboard")}
                    style={{ height: "2.4rem", padding: "0 1.25rem", display: "inline-flex", alignItems: "center" }}
                  >
                    ← Back to Dashboard
                  </button>

                  {atsScore !== null && (
                    <div
                      className="nm-card"
                      style={{
                        marginLeft: "auto",
                        height: "2.4rem",
                        padding: "0 0.85rem",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.45rem",
                        borderRadius: "8px",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                      }}
                      title="ATS Compatibility Score"
                    >
                      <span style={{ fontSize: "0.72rem", color: "var(--color-muted-fg)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                        ATS
                      </span>
                      <span
                        style={{
                          color: atsScore >= 80 ? "#1a9e6e" : atsScore >= 60 ? "var(--color-accent)" : "var(--color-destructive)",
                          fontWeight: 700,
                        }}
                      >
                        {atsScore}/100
                      </span>
                    </div>
                  )}
                </div>

                {downloadError && (
                  <div className="nm-card" style={{ marginTop: "0.85rem", borderColor: "var(--color-destructive)", color: "var(--color-destructive)", fontSize: "0.82rem" }}>
                    {downloadError}
                  </div>
                )}
              </>
            )}

            {done && !rewrittenResume && !connectionError && !fatalError && (
              <>
                <div className="nm-card" style={{ color: "var(--color-muted-fg)", fontSize: "0.85rem" }}>
                  {banner ?? "Generation stopped or failed. Click retry to re-run the generation pipeline."}
                </div>
                <div style={{ marginTop: "1.25rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={handleRetryGeneration}
                    disabled={retrying}
                    className="btn btn-primary btn-sm"
                    style={{ gap: "0.35rem" }}
                  >
                    {retrying && <span className="spinner spinner-sm" />}
                    ↻ {retrying ? "Retrying…" : "Retry Generation"}
                  </button>
                  <button type="button" onClick={toggleHistory} className={`btn btn-sm${historyOpen ? " btn-primary" : ""}`}>
                    {historyOpen ? "Hide History" : "Show History"}
                  </button>
                  <button className="btn btn-sm btn-ghost" onClick={() => router.push("/dashboard")}>← Back to Dashboard</button>
                </div>
              </>
            )}

          {/* History Dialog positioned on the RIGHT of the resume */}
          {historyOpen && (
            <aside
              className="side-panel-right"
              onClick={(e) => {
                if (e.target === e.currentTarget) setHistoryOpen(false);
              }}
            >
              <div
                className="side-dialog-panel nm-card"
                style={{
                  background: "var(--color-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "14px",
                  padding: "1.25rem",
                  display: "flex",
                  flexDirection: "column",
                  animation: "historyDialogIn 0.28s cubic-bezier(0.16, 1, 0.3, 1)",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", borderBottom: "1px solid var(--color-border)", paddingBottom: "0.75rem" }}>
                  <div>
                    <h3 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>Generation History</h3>
                    <p className="text-muted text-xs" style={{ margin: "0.2rem 0 0" }}>
                      Your past tailored resumes & logs
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setHistoryOpen(false)}
                    className="btn btn-ghost btn-xs"
                    style={{ fontSize: "1.25rem", lineHeight: 1, padding: "0.2rem 0.45rem", borderRadius: "4px" }}
                    title="Close (Esc)"
                  >
                    ×
                  </button>
                </div>

                {loadingHistory ? (
                  <div style={{ display: "flex", justifyContent: "center", alignItems: "center", flex: 1, padding: "3rem 0" }}>
                    <span className="spinner spinner-lg" />
                  </div>
                ) : (
                  <div style={{ flex: 1, overflowY: "auto", maxHeight: "calc(100vh - 12rem)" }} className="custom-scrollbar">
                    <HistoryList
                      generations={historyGenerations}
                      compact
                      onDeleted={(delId) => setHistoryGenerations((prev) => prev.filter((g) => g.id !== delId))}
                      onUpdated={(upId, updated) => setHistoryGenerations((prev) => prev.map((g) => g.id === upId ? updated : g))}
                      onSelect={(selectedId) => {
                        setHistoryOpen(false);
                        router.push(`/dashboard/results/${selectedId}`);
                      }}
                    />
                  </div>
                )}
              </div>
            </aside>
          )}
        </div>
      </div>
    </>
  );
}
