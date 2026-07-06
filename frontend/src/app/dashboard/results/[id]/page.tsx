"use client";

import { useParams } from "next/navigation";
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
  jd_parser: "Analyzing job description",
  project_matcher: "Matching projects from GitHub",
  resume_writer: "Rewriting skills and projects",
  ats_checker: "Checking ATS compatibility",
};

const INITIAL_STEPS: Step[] = [
  { step: "jd_parser", label: STEP_LABELS.jd_parser, status: "pending" },
  {
    step: "project_matcher",
    label: STEP_LABELS.project_matcher,
    status: "pending",
  },
  {
    step: "resume_writer",
    label: STEP_LABELS.resume_writer,
    status: "pending",
  },
  {
    step: "ats_checker",
    label: STEP_LABELS.ats_checker,
    status: "pending",
  },
];

export default function ResultsPage() {
  const params = useParams<{ id: string }>();
  const [steps, setSteps] = useState<Step[]>(INITIAL_STEPS);
  const [done, setDone] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [atsScore, setAtsScore] = useState<number | null>(null);
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
        return [
          ...prev,
          { step: data.step, label: STEP_LABELS[data.step as StepName] || data.step, status: "running" },
        ];
      });
    });

    es.addEventListener("step-done", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setSteps((prev) =>
        prev.map((s) =>
          s.step === data.step ? { ...s, status: "done" as const } : s,
        ),
      );
    });

    es.addEventListener("step-error", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setSteps((prev) =>
        prev.map((s) =>
          s.step === data.step ? { ...s, status: "error" as const } : s,
        ),
      );
    });

    es.addEventListener("done", (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setGenerationId(data.generation_id ?? null);
      setAtsScore(data.ats_score ?? null);
      setRewrittenResume(data.rewritten_resume ?? null);
      setDone(true);
      es.close();
    });
  }, [params.id]);

  useEffect(() => {
    startStream();
    return () => {
      esRef.current?.close();
    };
  }, [startStream]);

  const statusIcon = (status: Step["status"]) => {
    switch (status) {
      case "running":
        return "⟳";
      case "done":
        return "✓";
      case "error":
        return "✗";
      default:
        return "○";
    }
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-8 text-center text-3xl font-bold text-foreground">
          Generating Resume
        </h1>

        {connectionError && (
          <div className="neumorphic-card mb-8 rounded-2xl p-6 text-center">
            <p className="mb-4 text-red-500">
              Connection lost. Please wait or try again.
            </p>
            <button
              onClick={() => {
                setConnectionError(false);
                setDone(false);
                setSteps(INITIAL_STEPS);
                startStream();
              }}
              className="neumorphic-button rounded-xl px-6 py-3 text-foreground"
            >
              Retry
            </button>
          </div>
        )}

        <div className="neumorphic-card rounded-2xl p-6">
          <div className="space-y-4">
            {steps.map((step) => (
              <div key={step.step} className="flex items-center gap-3">
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-sm ${
                    step.status === "running"
                      ? "animate-spin text-accent"
                      : step.status === "done"
                        ? "text-green-500"
                        : step.status === "error"
                          ? "text-red-500"
                          : "text-muted-foreground"
                  }`}
                >
                  {statusIcon(step.status)}
                </span>
                <span
                  className={`text-sm ${
                    step.status === "running"
                      ? "font-semibold text-accent"
                      : step.status === "done"
                        ? "text-green-500"
                        : step.status === "error"
                          ? "text-red-500"
                          : "text-muted-foreground"
                  }`}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {done && (
          <div className="mt-8 space-y-6">
            {atsScore !== null && (
              <div className="neumorphic-card rounded-2xl p-6">
                <h2 className="mb-2 text-lg font-semibold text-foreground">
                  ATS Compatibility Score
                </h2>
                <p className="text-3xl font-bold text-accent">{atsScore}/100</p>
              </div>
            )}

            {rewrittenResume && (
              <div className="neumorphic-card rounded-2xl p-6">
                <h2 className="mb-4 text-lg font-semibold text-foreground">
                  Rewritten Resume
                </h2>
                <pre className="whitespace-pre-wrap text-sm text-foreground">
                  {rewrittenResume}
                </pre>
              </div>
            )}

            <div className="text-center">
              <a
                href="/dashboard/history"
                className="neumorphic-button inline-block rounded-xl px-6 py-3 text-foreground"
              >
                View History
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
