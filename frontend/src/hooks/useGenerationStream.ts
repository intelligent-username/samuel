"use client";

import { useEffect, useState } from "react";
import { fetchGeneration, getDownloadUrl } from "@/lib/api";
import type { StepProgress } from "@/lib/types";

export function useGenerationStream(generationId: string) {
  const [steps, setSteps] = useState<StepProgress[]>([]);
  const [done, setDone] = useState(false);
  const [atsScore, setAtsScore] = useState<number | null>(null);
  const [rewrittenResume, setRewrittenResume] = useState<string | null>(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [fatalError, setFatalError] = useState<string | null>(null);
  const [connectionError, setConnectionError] = useState(false);
  const [jobDescription, setJobDescription] = useState<string | null>(null);
  const [generationTitle, setGenerationTitle] = useState<string | null>(null);

  // Initial check
  useEffect(() => {
    let active = true;
    fetchGeneration(generationId)
      .then((gen) => {
        if (!active) return;
        if (gen.title) setGenerationTitle(gen.title);
        if (gen.job_description_text) setJobDescription(gen.job_description_text);
        if (gen.status === "completed" && gen.rewritten_resume_text) {
          setRewrittenResume(gen.rewritten_resume_text);
          setDone(true);
          if (gen.ats_report?.score !== undefined) setAtsScore(gen.ats_report.score);
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

    es.addEventListener("step-start", (e: MessageEvent) => {
      const data = parseEventData<{ step?: string }>(e.data);
      if (data.step) {
        setSteps((prev) => [
          ...prev.filter((s) => s.step !== data.step),
          { step: data.step!, status: "running" },
        ]);
      }
    });

    es.addEventListener("step-done", (e: MessageEvent) => {
      const data = parseEventData<{ step?: string }>(e.data);
      if (data.step) {
        setSteps((prev) =>
          prev.map((s) => (s.step === data.step ? { ...s, status: "done" } : s))
        );
      }
    });

    es.addEventListener("done", (e: MessageEvent) => {
      const data = parseEventData<{ ats_score?: number }>(e.data);
      setDone(true);
      if (data.ats_score !== undefined) setAtsScore(data.ats_score);
      fetchGeneration(generationId)
        .then((gen) => {
          if (gen.rewritten_resume_text) setRewrittenResume(gen.rewritten_resume_text);
          if (gen.title) setGenerationTitle(gen.title);
          if (gen.job_description_text) setJobDescription(gen.job_description_text);
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
      setConnectionError(true);
      es.close();
    };

    return () => es.close();
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
    connectionError,
    jobDescription,
    setJobDescription,
    generationTitle,
    setGenerationTitle,
  };
}
