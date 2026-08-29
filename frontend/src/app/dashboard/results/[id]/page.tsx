"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { createGenerationStream, getDownloadUrl, fetchGeneration, fetchGenerations } from "@/lib/api";
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
  const [historyOpen, setHistoryOpen]   = useState(false);
  const [historyGenerations, setHistoryGenerations] = useState<Generation[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const openHistory = () => {
    setHistoryOpen(true);
    setLoadingHistory(true);
    fetchGenerations()
      .then((data) => {
        setHistoryGenerations(data);
        setLoadingHistory(false);
      })
      .catch(() => setLoadingHistory(false));
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
        if (gen.status === "failed") {
          // Let stream open? Instead show banner immediately but still allow stream to replay error
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
      {/* Right Drawer Dialog for History */}
      {historyOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 90,
            background: "rgba(0, 0, 0, 0.65)",
            backdropFilter: "blur(4px)",
            display: "flex",
            justifyContent: "flex-end",
          }}
          onClick={() => setHistoryOpen(false)}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 480,
              height: "100%",
              background: "var(--color-card)",
              borderLeft: "1px solid var(--color-border)",
              boxShadow: "-12px 0 30px rgba(0,0,0,0.5)",
              display: "flex",
              flexDirection: "column",
              padding: "1.5rem",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", borderBottom: "1px solid var(--color-border)", paddingBottom: "0.75rem" }}>
              <div>
                <h3 style={{ fontSize: "1.25rem", margin: 0 }}>Generation History</h3>
                <p className="text-muted text-xs" style={{ margin: "0.2rem 0 0" }}>
                  Your past tailored resumes & logs
                </p>
              </div>
              <button
                type="button"
                onClick={() => setHistoryOpen(false)}
                className="btn btn-ghost btn-sm"
                style={{ fontSize: "1.25rem", lineHeight: 1, padding: "0.25rem 0.5rem" }}
                title="Close"
              >
                ×
              </button>
            </div>

            {loadingHistory ? (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", flex: 1, padding: "3rem 0" }}>
                <span className="spinner spinner-lg" />
              </div>
            ) : (
              <div style={{ flex: 1 }}>
                <HistoryList
                  generations={historyGenerations}
                  compact
                  onDeleted={(delId) => setHistoryGenerations((prev) => prev.filter((g) => g.id !== delId))}
                  onSelect={(selectedId) => {
                    setHistoryOpen(false);
                    router.push(`/dashboard/results/${selectedId}`);
                  }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      <div style={{
        minHeight: "100vh",
        padding: "3rem 2rem",
        maxWidth: 760,
        margin: "0 auto",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.4rem", flexWrap: "wrap", gap: "0.75rem" }}>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, margin: 0 }}>
            {fatalError ? "Error" : done && !hasError ? "Resume ready" : done && hasError ? "Generation failed" : "Generating resume…"}
          </h1>
          <button
            type="button"
            onClick={openHistory}
            className="btn btn-sm"
          >
            Show History
          </button>
        </div>
        {fatalError && (
          <div className="nm-card" style={{ borderColor:"var(--color-destructive)", marginBottom:"1.5rem" }}>
            <h3 style={{ color:"var(--color-destructive)", margin:"0 0 0.35rem" }}>{fatalError.title}</h3>
            <p className="text-muted" style={{ fontSize:"0.85rem", margin:"0 0 1rem" }}>{fatalError.detail}</p>
            <div style={{ display:"flex", gap:"0.75rem" }}>
              <button type="button" onClick={openHistory} className="btn btn-sm">Show History</button>
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
          </div>
        )}

        {done && atsScore !== null && (
          <div className="nm-card" style={{ marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "1.25rem" }}>
            <div>
              <p style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--color-muted-fg)", marginBottom: "0.2rem" }}>ATS Score</p>
              <p style={{ fontSize: "2.25rem", fontWeight: 800, color: atsScore >= 80 ? "#1a9e6e" : atsScore >= 60 ? "var(--color-accent)" : "var(--color-destructive)", lineHeight: 1 }}>
                {atsScore}<span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--color-muted-fg)" }}>/100</span>
              </p>
            </div>
          </div>
        )}

        {rewrittenResume && (
          <>
            <div className="nm-card" style={{ padding: "0.5rem", overflow: "hidden" }}>
              <iframe
                src={getDownloadUrl(params.id)}
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
                style={{ textDecoration: "none" }}
              >
                Download PDF
              </a>
              <button type="button" onClick={openHistory} className="btn btn-sm">Show History</button>
              <button className="btn btn-sm btn-ghost" onClick={() => router.push("/dashboard")}>
                ← Back to Dashboard
              </button>
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
              No resume content yet — still generating or generation failed. If this persists, try regenerating.
            </div>
            <div style={{ marginTop: "1.25rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
              <button type="button" onClick={openHistory} className="btn btn-sm">Show History</button>
              <button className="btn btn-sm btn-ghost" onClick={() => router.push("/dashboard")}>← Back to Dashboard</button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
