"use client";

import { useEffect, useRef, useState } from "react";
import { fetchGeneration, getDownloadUrl } from "@/lib/api";
import type { StepProgress } from "@/lib/types";

const INITIAL_STEPS: StepProgress[] = [
  { step: "jd_parser", label: "Analyze Job Description", status: "pending" },
  { step: "project_matcher", label: "Match GitHub Repositories", status: "pending" },
  { step: "rewrite_1", label: "Rewrite 1", status: "pending", iteration: 1 },
  { step: "ats_1", label: "ATS Audit 1", status: "pending", iteration: 1 },
];

export function useGenerationStream(generationId: string) {
  const [steps, setSteps] = useState<StepProgress[]>(INITIAL_STEPS);
  const [done, setDone] = useState(false);
  const [atsScore, setAtsScore] = useState<number | null>(null);
  const [rewrittenResume, setRewrittenResume] = useState<string | null>(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [fatalError, setFatalError] = useState<string | null>(null);
  const [connectionRetrying, setConnectionRetrying] = useState(false);
  const [jobDescription, setJobDescription] = useState<string | null>(null);
  const [generationTitle, setGenerationTitle] = useState<string | null>(null);
  const [iterations, setIterations] = useState<Array<{ iteration: number; score: number }>>([]);
  const [exitReason, setExitReason] = useState<string | null>(null);
  const [atsScores, setAtsScores] = useState<number[]>([]);
  const [currentThreshold, setCurrentThreshold] = useState<number | null>(null);

  const activeIterationRef = useRef<number>(1);

  // Initial check
  useEffect(() => {
    let active = true;
    fetchGeneration(generationId)
      .then((gen) => {
        if (!active) return;
        if (gen.title) setGenerationTitle(gen.title);
        if (gen.job_description_text) setJobDescription(gen.job_description_text);
        if (gen.ats_threshold !== undefined && gen.ats_threshold !== null) setCurrentThreshold(gen.ats_threshold);
        if (gen.ats_exit_reason) setExitReason(gen.ats_exit_reason);
        if (gen.ats_scores && gen.ats_scores.length > 0) setAtsScores(gen.ats_scores);
        if (gen.iterations && gen.iterations.length > 0) {
          setIterations(gen.iterations);
        } else if (gen.ats_scores && gen.ats_scores.length > 0) {
          setIterations(gen.ats_scores.map((score, idx) => ({ iteration: idx + 1, score })));
        }
        if (gen.status === "completed" && gen.rewritten_resume_text) {
          setRewrittenResume(gen.rewritten_resume_text);
          setDone(true);
          const score = gen.ats_score ?? gen.ats_report?.score;
          if (score !== undefined && score !== null) {
            setAtsScore(score);
            setIterations((prev) => (prev.length > 0 ? prev : [{ iteration: 1, score }]));
          }
          setSteps((prev) => prev.map((s) => ({ ...s, status: "done" })));
        } else if (gen.status === "failed") {
          setFatalError(gen.error_message || "Generation failed.");
        }
      })
      .catch(() => null);
    return () => {
      active = false;
    };
  }, [generationId]);

  // Connect SSE stream
  useEffect(() => {
    if (!generationId || done) return;
    let pollInterval: NodeJS.Timeout | null = null;

    const es = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/generate/${generationId}/stream`,
      { withCredentials: true }
    );

    function parseEventData<T = any>(rawData: any): T {
      if (typeof rawData === "object" && rawData !== null) return rawData as T;
      if (typeof rawData !== "string") return {} as T;
      try {
        return JSON.parse(rawData);
      } catch {
        try {
          const jsonStr = rawData
            .replace(/'/g, '"')
            .replace(/True/g, "true")
            .replace(/False/g, "false")
            .replace(/None/g, "null");
          return JSON.parse(jsonStr);
        } catch {
          return {} as T;
        }
      }
    }

    const ensureIterationSteps = (iter: number) => {
      setSteps((prev) => {
        const next = [...prev];
        const rKey = `rewrite_${iter}`;
        const aKey = `ats_${iter}`;
        if (!next.some((s) => s.step === rKey)) {
          next.push({ step: rKey, label: `Rewrite ${iter}`, status: "pending", iteration: iter });
        }
        if (!next.some((s) => s.step === aKey)) {
          next.push({ step: aKey, label: `ATS Audit ${iter}`, status: "pending", iteration: iter });
        }
        return next;
      });
    };

    es.addEventListener("step-start", (e: MessageEvent) => {
      setConnectionRetrying(false);
      const data = parseEventData<{ step?: string; message?: string }>(e.data);
      if (!data.step) return;

      const rawStep = data.step;
      const iter = activeIterationRef.current;
      const targetKey = rawStep === "resume_writer" ? `rewrite_${iter}` : rawStep === "ats_checker" ? `ats_${iter}` : rawStep;

      setSteps((prev) => {
        const exists = prev.some((s) => s.step === targetKey);
        if (exists) {
          return prev.map((s) =>
            s.step === targetKey ? { ...s, status: "running", message: data.message } : s
          );
        }
        const defaultLabel = rawStep === "resume_writer" ? `Rewrite ${iter}` : rawStep === "ats_checker" ? `ATS Audit ${iter}` : rawStep;
        return [...prev, { step: targetKey, label: defaultLabel, status: "running", message: data.message, iteration: iter }];
      });
    });

    es.addEventListener("step-done", (e: MessageEvent) => {
      setConnectionRetrying(false);
      const data = parseEventData<{ step?: string; summary?: string }>(e.data);
      if (!data.step) return;

      const rawStep = data.step;
      const iter = activeIterationRef.current;
      const targetKey = rawStep === "resume_writer" ? `rewrite_${iter}` : rawStep === "ats_checker" ? `ats_${iter}` : rawStep;

      setSteps((prev) =>
        prev.map((s) => (s.step === targetKey ? { ...s, status: "done", summary: data.summary } : s))
      );
    });

    es.addEventListener("ats_loop", (e: MessageEvent) => {
      setConnectionRetrying(false);
      const data = parseEventData<{ iteration?: number; score?: number; threshold?: number }>(e.data);
      if (data.threshold !== undefined) setCurrentThreshold(data.threshold);
      if (data.iteration) {
        activeIterationRef.current = data.iteration;
        ensureIterationSteps(data.iteration);
      }
    });

    es.addEventListener("ats_evaluation", (e: MessageEvent) => {
      setConnectionRetrying(false);
      const data = parseEventData<{ score?: number; threshold?: number; iteration?: number; will_retry?: boolean }>(e.data);
      if (data.score !== undefined) {
        const iter = data.iteration ?? activeIterationRef.current;
        setAtsScores((prev) => [...prev, data.score!]);
        setIterations((prev) => [...prev, { iteration: iter, score: data.score! }]);
        if (data.threshold !== undefined) setCurrentThreshold(data.threshold);

        const aKey = `ats_${iter}`;
        setSteps((prev) =>
          prev.map((s) =>
            s.step === aKey
              ? { ...s, status: "done", score: data.score, summary: `Score: ${data.score}/100${data.threshold ? ` · Target: ${data.threshold}` : ""}` }
              : s
          )
        );

        if (data.will_retry) {
          const nextIter = iter + 1;
          activeIterationRef.current = nextIter;
          ensureIterationSteps(nextIter);
        }
      }
    });

    es.addEventListener("ats_stagnation", () => {
      setExitReason((prev) => prev ?? "stagnation");
    });

    es.addEventListener("done", (e: MessageEvent) => {
      const data = parseEventData<{ ats_score?: number; ats_scores?: number[]; exit_reason?: string; iterations?: Array<{ iteration: number; score: number }>; threshold?: number; rewritten_resume?: string }>(e.data);
      if (data.rewritten_resume) {
        setRewrittenResume(data.rewritten_resume);
      }
      setDone(true);
      if (data.ats_score !== undefined) setAtsScore(data.ats_score);
      if (data.ats_scores && data.ats_scores.length > 0) setAtsScores(data.ats_scores);
      if (data.exit_reason) setExitReason(data.exit_reason);
      if (data.iterations && data.iterations.length > 0) {
        setIterations(data.iterations);
      }
      if (data.threshold !== undefined) setCurrentThreshold(data.threshold);

      // Complete all steps
      setSteps((prev) => prev.map((s) => (s.status === "running" || s.status === "pending" ? { ...s, status: "done" } : s)));

      // Sync final database state
      fetchGeneration(generationId)
        .then((gen) => {
          if (gen.rewritten_resume_text) setRewrittenResume(gen.rewritten_resume_text);
          if (gen.title) setGenerationTitle(gen.title);
          if (gen.job_description_text) setJobDescription(gen.job_description_text);
          if (gen.ats_scores && gen.ats_scores.length > 0) setAtsScores(gen.ats_scores);
          if (gen.ats_exit_reason) setExitReason(gen.ats_exit_reason);
          if (gen.ats_report?.score !== undefined) setAtsScore(gen.ats_report.score);
        })
        .catch(() => null);

      es.close();
    });

    es.addEventListener("step-error", (e: MessageEvent) => {
      const data = parseEventData<{ step?: string; error?: string; message?: string }>(e.data);
      if (data.step) {
        setSteps((prev) =>
          prev.map((s) => (s.step === data.step ? { ...s, status: "error" } : s))
        );
      }
      setFatalError(data.error || data.message || "A step failed during generation.");
      es.close();
    });

    es.onerror = () => {
      // Do not kill the UI. Verify backend status and keep polling if still running.
      setConnectionRetrying(true);
      fetchGeneration(generationId)
        .then((gen) => {
          if (gen.status === "completed") {
            if (gen.rewritten_resume_text) setRewrittenResume(gen.rewritten_resume_text);
            setDone(true);
            setConnectionRetrying(false);
            es.close();
          } else if (gen.status === "failed") {
            setFatalError(gen.error_message || "Generation failed.");
            setConnectionRetrying(false);
            es.close();
          }
        })
        .catch(() => null);

      // Start fallback polling while disconnected
      if (!pollInterval) {
        pollInterval = setInterval(() => {
          fetchGeneration(generationId)
            .then((gen) => {
              if (gen.status === "completed") {
                if (gen.rewritten_resume_text) setRewrittenResume(gen.rewritten_resume_text);
                setDone(true);
                setConnectionRetrying(false);
                if (pollInterval) clearInterval(pollInterval);
                es.close();
              } else if (gen.status === "failed") {
                setFatalError(gen.error_message || "Generation failed.");
                setConnectionRetrying(false);
                if (pollInterval) clearInterval(pollInterval);
                es.close();
              }
            })
            .catch(() => null);
        }, 2500);
      }
    };

    return () => {
      if (pollInterval) clearInterval(pollInterval);
      es.close();
    };
  }, [generationId, done]);

  // PDF blob fetch
  useEffect(() => {
    if (!done || !rewrittenResume) return;
    let url: string | null = null;
    fetch(getDownloadUrl(generationId), { credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error("Preview fetch failed");
        return res.blob();
      })
      .then((blob) => {
        url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
      })
      .catch(() => setPdfBlobUrl(null));

    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [done, rewrittenResume, generationId]);

  return {
    steps,
    done,
    atsScore,
    rewrittenResume,
    pdfBlobUrl,
    fatalError,
    setFatalError,
    connectionRetrying,
    jobDescription,
    setJobDescription,
    generationTitle,
    setGenerationTitle,
    iterations,
    exitReason,
    atsScores,
    currentThreshold,
  };
}
