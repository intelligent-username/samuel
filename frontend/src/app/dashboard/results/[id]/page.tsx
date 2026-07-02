"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { createGenerationStream } from "@/lib/api";

interface Step {
  step: string;
  message: string;
  summary?: string;
}

export default function ResultsPage() {
  const params = useParams<{ id: string }>();
  const [steps, setSteps] = useState<Step[]>([]);
  const [output, setOutput] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [atsScore, setAtsScore] = useState<number | null>(null);
  const outputRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (!params.id) return;
    const es = createGenerationStream(params.id);

    es.addEventListener("step-start", (e: any) => {
      const data = JSON.parse(e.data);
      setSteps((s) => [...s, { step: data.step, message: data.message }]);
    });

    es.addEventListener("step-done", (e: any) => {
      const data = JSON.parse(e.data);
      setSteps((s) =>
        s.map((st) => (st.step === data.step ? { ...st, summary: data.summary } : st))
      );
    });

    es.addEventListener("output", (e: any) => {
      setOutput(e.data);
    });

    es.addEventListener("done", (e: any) => {
      const data = JSON.parse(e.data);
      setAtsScore(data.ats_score);
      setDone(true);
      es.close();
    });

    es.addEventListener("error", (e: any) => {
      const data = JSON.parse(e.data);
      setError(data.message);
      setDone(true);
      es.close();
    });

    return () => es.close();
  }, [params.id]);

  return (
    <div>
      <h2 style={{ marginBottom: "1.5rem" }}>Resume Generation</h2>

      <div style={{ marginBottom: "2rem" }}>
        <h3>Progress</h3>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {steps.map((s, i) => (
            <li
              key={i}
              style={{
                padding: "0.5rem",
                marginBottom: "0.25rem",
                background: s.summary ? "#e8f5e9" : "#fff3e0",
                borderRadius: "4px",
              }}
            >
              <strong>{s.step}:</strong> {s.message}
              {s.summary && <span style={{ color: "#2e7d32", marginLeft: "0.5rem" }}>✓ {s.summary}</span>}
            </li>
          ))}
          {!done && steps.length > 0 && steps.every((s) => !s.summary) && (
            <li style={{ padding: "0.5rem", color: "#666" }}>Processing...</li>
          )}
        </ul>
      </div>

      {error && (
        <div style={{ padding: "1rem", background: "#ffebee", borderRadius: "4px", marginBottom: "1rem" }}>
          Error: {error}
        </div>
      )}

      {atsScore !== null && (
        <div style={{ marginBottom: "1rem" }}>
          ATS Compatibility Score: <strong>{atsScore}/100</strong>
        </div>
      )}

      {output && (
        <div>
          <h3>Rewritten Resume</h3>
          <pre
            ref={outputRef}
            style={{
              background: "#f5f5f5",
              padding: "1rem",
              borderRadius: "4px",
              whiteSpace: "pre-wrap",
              fontSize: "0.875rem",
              lineHeight: 1.5,
              maxHeight: "600px",
              overflowY: "auto",
            }}
          >
            {output}
          </pre>
          {done && (
            <button
              onClick={() => {
                const blob = new Blob([output], { type: "application/pdf" });
                window.open(URL.createObjectURL(blob));
              }}
              style={{
                marginTop: "1rem",
                padding: "0.5rem 1rem",
                background: "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Save as PDF
            </button>
          )}
        </div>
      )}
    </div>
  );
}