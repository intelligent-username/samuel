"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { createGenerationStream, getDownloadUrl } from "@/lib/api";
import type { StepEvent } from "@/lib/types";

const STEP_META: Record<string, { label: string }> = {
  jd_parser:       { label: "Parsing Job Description" },
  project_matcher: { label: "Matching Projects" },
  resume_writer:   { label: "Rewriting Resume" },
  ats_checker:     { label: "ATS Compatibility Check" },
};

export default function ResultsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [output, setOutput] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [atsScore, setAtsScore] = useState<number | null>(null);
  const [connectionError, setConnectionError] = useState(false);
  const outputRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (!params.id) return;

    let es: EventSource;
    try {
      es = createGenerationStream(params.id);
    } catch {
      setConnectionError(true);
      return;
    }

    // B9: handle connection errors
    es.onerror = () => {
      if (steps.length === 0 && !done) {
        setConnectionError(true);
        setDone(true);
        es.close();
      }
    };

    es.addEventListener("step-start", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setSteps((prev) => {
        if (prev.find((s) => s.step === data.step)) return prev;
        return [...prev, { step: data.step, message: data.message, status: "active" }];
      });
    });

    es.addEventListener("step-done", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setSteps((prev) =>
        prev.map((s) => s.step === data.step ? { ...s, summary: data.summary, status: "done" } : s)
      );
    });

    es.addEventListener("output", (e: MessageEvent) => {
      setOutput(e.data);
    });

    es.addEventListener("done", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setAtsScore(data.ats_score);
      setDone(true);
      es.close();
    });

    es.addEventListener("error", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setError(data.message || "An error occurred");
      } catch {
        setError("An unexpected error occurred");
      }
      setSteps((prev) => prev.map((s) => s.status === "active" ? { ...s, status: "error" } : s));
      setDone(true);
      es.close();
    });

    return () => es.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  const atsColor = atsScore !== null
    ? atsScore >= 80 ? "#1a9e6e" : atsScore >= 60 ? "#a94904" : "#b90e0a"
    : "var(--color-foreground)";

  if (connectionError) {
    return (
      <div className="nm-card" style={{ textAlign: "center", padding: "3rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-destructive)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ margin: "0 auto" }}>
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </div>
        <h2 style={{ marginBottom: "0.5rem" }}>Generation not found</h2>
        <p className="text-muted" style={{ marginBottom: "1.5rem" }}>
          This generation doesn&apos;t exist or you don&apos;t have access to it.
        </p>
        <button onClick={() => router.push("/dashboard")} className="btn btn-primary">
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "800px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "2rem" }}>
        <button onClick={() => router.push("/dashboard")} className="btn btn-ghost btn-sm">
          Back
        </button>
        <h2 style={{ margin: 0 }}>Resume Generation</h2>
      </div>

      {/* ─── Progress Steps ─── */}
      <div className="nm-card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "1rem" }}>Progress</h3>
        <div>
          {Object.entries(STEP_META).map(([key, meta]) => {
            const step = steps.find((s) => s.step === key);
            const status = step?.status ?? "pending";
            return (
              <div key={key} className="step-item">
                <div className={`step-icon ${status}`}>
                  {status === "pending" && "Pending"}
                  {status === "active" && <span className="spinner spinner-sm" style={{ borderColor: "#fff3", borderTopColor: "#fff" }} />}
                  {status === "done" && "Done"}
                  {status === "error" && "Error"}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                    {meta.label}
                  </div>
                  {step?.message && status === "active" && (
                    <div className="text-muted text-xs" style={{ marginTop: "0.2rem" }}>{step.message}</div>
                  )}
                  {step?.summary && (
                    <div style={{ color: "#1a9e6e", fontSize: "0.8rem", marginTop: "0.2rem" }}>{step.summary}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {!done && steps.length === 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.75rem 0", color: "var(--color-muted-fg)" }}>
            <span className="spinner spinner-sm" />
            <span className="text-sm">Connecting to generation stream...</span>
          </div>
        )}
      </div>

      {/* ─── Error Banner ─── */}
      {error && (
        <div
          className="nm-card-sm"
          style={{
            marginBottom: "1.5rem",
            borderLeft: "4px solid var(--color-destructive)",
            background: "var(--color-card)",
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--color-destructive)", marginBottom: "0.25rem" }}>
            Generation failed
          </div>
          <p className="text-sm text-muted">{error}</p>
        </div>
      )}

      {/* ─── ATS Score ─── */}
      {atsScore !== null && (
        <div className="nm-card" style={{ marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <div
            style={{
              width: "72px",
              height: "72px",
              borderRadius: "50%",
              background: "var(--color-card)",
              border: "1px solid var(--color-border)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <span style={{ fontWeight: 700, fontSize: "1.4rem", color: atsColor }}>{atsScore}</span>
            <span style={{ fontSize: "0.65rem", color: "var(--color-muted-fg)", fontWeight: 500 }}>/100</span>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: "1rem" }}>ATS Compatibility Score</div>
            <p className="text-sm text-muted" style={{ marginTop: "0.25rem" }}>
              {atsScore >= 80
                ? "Excellent match — your resume is well-optimized for this role."
                : atsScore >= 60
                ? "Good match — minor improvements recommended."
                : "Needs work — consider addressing the flagged issues."}
            </p>
          </div>
        </div>
      )}

      {/* ─── Rewritten Resume ─── */}
      {output && (
        <div className="nm-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h3 style={{ margin: 0 }}>Rewritten Resume</h3>
            {done && (
              <a
                id="download-pdf-btn"
                href={getDownloadUrl(params.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary btn-sm"
              >
                Download PDF
              </a>
            )}
          </div>
          <div className="nm-inset" style={{ padding: "1.25rem" }}>
            <pre
              ref={outputRef}
              className="font-mono"
              style={{
                fontSize: "0.8rem",
                lineHeight: 1.7,
                whiteSpace: "pre-wrap",
                maxHeight: "600px",
                overflowY: "auto",
              }}
            >
              {output}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}