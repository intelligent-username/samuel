"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { createGenerationStream } from "@/lib/api";

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
  const [atsScore, setAtsScore]         = useState<number | null>(null);
  const [rewrittenResume, setRewrittenResume] = useState<string | null>(null);
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

    es.onerror = () => {
      if (!done) {
        setConnectionError(true);
        setDone(true);
        es.close();
      }
    };

    es.addEventListener("step-start", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setSteps((prev) =>
        prev.map((s) => s.step === data.step ? { ...s, status: "running" } : s)
      );
    });

    es.addEventListener("step-done", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setSteps((prev) =>
        prev.map((s) => s.step === data.step ? { ...s, status: "done" } : s)
      );
    });

    es.addEventListener("step-error", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setSteps((prev) =>
        prev.map((s) => s.step === data.step ? { ...s, status: "error" } : s)
      );
    });

    es.addEventListener("done", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setAtsScore(data.ats_score ?? null);
      setRewrittenResume(data.rewritten_resume ?? null);
      setDone(true);
      // Auto-collapse after a short delay
      setTimeout(() => setPanelVisible(false), 2200);
      es.close();
    });
  }, [params.id]);

  useEffect(() => {
    startStream();
    return () => esRef.current?.close();
  }, [startStream]);

  const allDone  = steps.every((s) => s.status === "done");
  const hasError = steps.some((s) => s.status === "error");

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
      {connectionError && (
        <div style={{ marginTop: "auto", paddingTop: "0.75rem", borderTop: "1px solid var(--color-border)" }}>
          <p style={{ fontSize: "0.72rem", color: "var(--color-destructive)", marginBottom: "0.5rem" }}>
            Connection lost.
          </p>
          <button
            onClick={() => { setConnectionError(false); setDone(false); setSteps(INITIAL_STEPS); startStream(); }}
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
          {done && !hasError ? "Resume ready" : done && hasError ? "Generation failed" : "Generating resume…"}
        </h1>
        <p className="text-muted" style={{ marginBottom: "2.5rem", fontSize: "0.85rem" }}>
          {done && !hasError
            ? "Your rewritten resume is below."
            : done && hasError
            ? "One or more steps encountered an error."
            : "Hang tight — the AI is working on your resume."}
        </p>

        {!done && (
          <div className="nm-card" style={{ display: "flex", alignItems: "center", gap: "1rem", color: "var(--color-muted-fg)", fontSize: "0.875rem" }}>
            <span className="spinner spinner-sm" />
            Working…
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

        {done && rewrittenResume && (
          <div className="nm-card">
            <p style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--color-muted-fg)", marginBottom: "0.85rem" }}>
              Rewritten Resume
            </p>
            <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.82rem", lineHeight: 1.7, color: "var(--color-foreground)", fontFamily: "inherit" }}>
              {rewrittenResume}
            </pre>
          </div>
        )}

        {done && (
          <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <a href="/dashboard/history" className="btn btn-sm">View History</a>
            <button className="btn btn-sm btn-ghost" onClick={() => router.push("/dashboard")}>
              ← Back to Dashboard
            </button>
          </div>
        )}
      </div>
    </>
  );
}
