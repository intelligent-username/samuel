"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { createGenerationStream, getDownloadUrl, fetchGeneration } from "@/lib/api";
import Borromean3DViewer from "@/components/Borromean3DViewer";

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

// ── Status icon ──────────────────────────────────────────────────────────────
function StepDot({ status }: { status: Step["status"] }) {
  const base: React.CSSProperties = {
    width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
    transition: "background 0.2s ease",
  };
  const colors: Record<Step["status"], string> = {
    pending: "var(--color-border)",
    running: "var(--color-primary)",
    done:    "#1a9e6e",
    error:   "var(--color-destructive)",
  };
  return (
    <span style={{ ...base, background: colors[status],
      boxShadow: status === "running" ? `0 0 0 3px color-mix(in srgb, var(--color-primary) 25%, transparent)` : "none",
    }} />
  );
}

// ── Thin progress bar at top of panel ────────────────────────────────────────
function ProgressBar({ steps }: { steps: Step[] }) {
  const done = steps.filter((s) => s.status === "done").length;
  const pct  = Math.round((done / steps.length) * 100);
  return (
    <div style={{ height: 2, background: "var(--color-border)", borderRadius: 2, overflow: "hidden", marginBottom: "1rem" }}>
      <div style={{ height: "100%", width: `${pct}%`, background: "var(--color-primary)", transition: "width 0.4s ease" }} />
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ResultsPage() {
  const params  = useParams<{ id: string }>();
  const router  = useRouter();

  const [steps, setSteps]               = useState<Step[]>(INITIAL_STEPS);
  const [done, setDone]                 = useState(false);
  const [panelVisible, setPanelVisible] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [fatalError, setFatalError]     = useState<null | { title: string; detail: string }>(null);
  const [banner, setBanner]             = useState<string | null>(null);
  const [atsScore, setAtsScore]         = useState<number | null>(null);
  const [rewrittenResume, setRewrittenResume] = useState<string | null>(null);
  const [headerSnippet, setHeaderSnippet] = useState<string | null>(null);
  const [showPreview] = useState(true);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

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
      // Auto-collapse after a short delay
      setTimeout(() => setPanelVisible(false), 2200);
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
        if (gen.job_description_text) setHeaderSnippet(gen.job_description_text.slice(0,140));
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

  // Suppress harmless Next.js auto-scroll warning for the fixed timeline panel
  useEffect(() => {
    const orig = console.warn;
    console.warn = (...args: any[]) => {
      if (typeof args[0] === "string" && args[0].includes("Skipping auto-scroll")) return;
      orig.apply(console, args);
    };
    return () => { console.warn = orig; };
  }, []);

  useEffect(() => {
    fetchGeneration(params.id).then(g => {
      if (g.job_description_text) setHeaderSnippet(g.job_description_text.slice(0,140));
    }).catch(()=>{});
  }, [params.id]);

  const allDone  = steps.every((s) => s.status === "done");
  const hasError = steps.some((s) => s.status === "error") || !!fatalError;

  // ── Timeline overlay panel ──────────────────────────────────────────────
  const panel = panelVisible && (
    <div
      style={{
        position: "fixed",
        right: 0, top: 0, bottom: 0,
        width: 220,
        background: "var(--color-card)",
        borderLeft: "1px solid var(--color-border)",
        padding: "1.25rem 1rem",
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        gap: 0,
        boxShadow: "-8px 0 24px rgba(0,0,0,0.35)",
        animation: "slideInRight 0.25s ease",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
        <span style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--color-muted-fg)" }}>
          {allDone ? "Complete" : hasError ? "Error" : "Generating"}
        </span>
        <button
          onClick={() => setPanelVisible(false)}
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-muted-fg)", lineHeight: 1, fontSize: "0.85rem", padding: "0 0.15rem" }}
          title="Dismiss"
        >
          ×
        </button>
      </div>

      <ProgressBar steps={steps} />

      {/* Timeline */}
      <div style={{ display: "flex", flexDirection: "column", gap: 0, flex: 1 }}>
        {steps.map((step, idx) => {
          const isLast = idx === steps.length - 1;
          return (
            <div key={step.step} style={{ display: "flex", gap: "0.6rem", alignItems: "flex-start" }}>
              {/* Dot + connector */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                <div style={{ paddingTop: "0.15rem" }}>
                  <StepDot status={step.status} />
                </div>
                {!isLast && (
                  <div style={{
                    width: 1, flex: 1, minHeight: 20,
                    background: step.status === "done" ? "#1a9e6e" : "var(--color-border)",
                    margin: "3px 0",
                    transition: "background 0.3s ease",
                  }} />
                )}
              </div>

              {/* Label */}
              <div style={{ paddingBottom: isLast ? 0 : "0.75rem" }}>
                <span style={{
                  fontSize: "0.775rem",
                  fontWeight: step.status === "running" ? 600 : 400,
                  color: step.status === "running"  ? "var(--color-foreground)"
                       : step.status === "done"     ? "#1a9e6e"
                       : step.status === "error"    ? "var(--color-destructive)"
                       : "var(--color-muted-fg)",
                  transition: "color 0.2s ease",
                }}>
                  {step.label}
                </span>
                {step.status === "running" && (
                  <span style={{ display: "block", fontSize: "0.65rem", color: "var(--color-muted-fg)", marginTop: "0.1rem" }}>
                    in progress…
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Connection error */}
      {!fatalError && connectionError && (
        <div style={{ marginTop: "auto", paddingTop: "0.75rem", borderTop: "1px solid var(--color-border)" }}>
          <p style={{ fontSize: "0.72rem", color: "var(--color-destructive)", marginBottom: "0.5rem" }}>
            Connection lost.
          </p>
          <button
            onClick={() => { setConnectionError(false); setDone(false); setFatalError(null); setBanner(null); setSteps(INITIAL_STEPS); startStream(); }}
            className="btn btn-sm"
            style={{ width: "100%", justifyContent: "center" }}
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );

  // ── Results body ────────────────────────────────────────────────────────
  return (
    <>
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);   opacity: 1; }
        }
      `}</style>

      {panel}

      <div style={{
        minHeight: "100vh",
        padding: "3rem 2rem",
        maxWidth: 760,
        margin: "0 auto",
        paddingRight: panelVisible ? "calc(220px + 2rem)" : "2rem",
        transition: "padding-right 0.3s ease",
      }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 800, marginBottom: "0.4rem" }}>
          {fatalError ? "Error" : done && !hasError ? "Resume ready" : done && hasError ? "Generation failed" : "Generating resume…"}
        </h1>
        {fatalError && (
          <div className="nm-card" style={{ borderColor:"var(--color-destructive)", marginBottom:"1.5rem" }}>
            <h3 style={{ color:"var(--color-destructive)", margin:"0 0 0.35rem" }}>{fatalError.title}</h3>
            <p className="text-muted" style={{ fontSize:"0.85rem", margin:"0 0 1rem" }}>{fatalError.detail}</p>
            <div style={{ display:"flex", gap:"0.75rem" }}>
              <a href="/dashboard/history" className="btn btn-sm">View History</a>
              <button className="btn btn-sm btn-ghost" onClick={() => router.push("/dashboard")}>← Back to Dashboard</button>
            </div>
          </div>
        )}
        {!fatalError && banner && (
          <div className="nm-card" style={{ borderColor:"var(--color-destructive)", color:"var(--color-destructive)", fontSize:"0.85rem", marginBottom:"1rem" }}>{banner}</div>
        )}
        {!fatalError && !done && !connectionError && (
          <div className="nm-card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1.2rem", padding: "2.5rem 1.5rem", textAlign: "center" }}>
            <Borromean3DViewer height={140} width={140} interactive={false} speed="normal" />
            <div>
              <p style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.35rem" }}>Generating your tailored resume…</p>
              <p className="text-muted" style={{ fontSize: "0.8rem" }}>Matching projects → rewriting → ATS check</p>
            </div>
          </div>
        )}

        {!fatalError && (
        <p className="text-muted" style={{ marginBottom: "2.5rem", fontSize: "0.85rem" }}>
          {headerSnippet || "Your past resume generations..."}
        </p>
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
              <a href="/dashboard/history" className="btn btn-sm">View History</a>
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
              <a href="/dashboard/history" className="btn btn-sm">View History</a>
              <button className="btn btn-sm btn-ghost" onClick={() => router.push("/dashboard")}>← Back to Dashboard</button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
