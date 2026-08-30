"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import {
  fetchGeneration,
  fetchGenerations,
  stopGeneration,
  retryGeneration,
} from "@/lib/api";
import type { Generation } from "@/lib/types";

import { useGenerationStream } from "@/hooks/useGenerationStream";
import JobDescriptionDrawer from "@/components/JobDescriptionDrawer";
import HistoryDrawer from "@/components/HistoryDrawer";
import GenerationProgressCard from "@/components/GenerationProgressCard";
import ResumePreviewer from "@/components/ResumePreviewer";
import ResultsActionBar from "@/components/ResultsActionBar";

export default function ResultsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const {
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
  } = useGenerationStream(params.id);

  const [stopping, setStopping] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const [jdOpen, setJdOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyGenerations, setHistoryGenerations] = useState<Generation[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingJd, setLoadingJd] = useState(false);
  const [copiedJd, setCopiedJd] = useState(false);

  const pdfFileName = generationTitle?.trim()
    ? `${generationTitle.trim().replace(/[/\\:*?"<>|]/g, "").replace(/\.pdf$/i, "")}.pdf`
    : "generated_resume.pdf";

  const handleStopGeneration = async () => {
    setStopping(true);
    try {
      await stopGeneration(params.id);
      setFatalError("Generation stopped by user.");
    } catch {
      setFatalError("Failed to stop generation.");
    } finally {
      setStopping(false);
    }
  };

  const handleRetryGeneration = async () => {
    setRetrying(true);
    try {
      await retryGeneration(params.id);
      window.location.reload();
    } catch {
      setRetrying(false);
    }
  };

  const toggleJd = () => {
    if (!jdOpen && !jobDescription) {
      setLoadingJd(true);
      fetchGeneration(params.id)
        .then((gen) => {
          if (gen.job_description_text) setJobDescription(gen.job_description_text);
        })
        .finally(() => setLoadingJd(false));
    }
    setJdOpen((v) => !v);
  };

  const toggleHistory = () => {
    if (!historyOpen) {
      setLoadingHistory(true);
      fetchGenerations()
        .then((gens) => setHistoryGenerations(gens))
        .finally(() => setLoadingHistory(false));
    }
    setHistoryOpen((v) => !v);
  };

  return (
    <div className="results-page-shell">
      <div className="results-main-col">
        {/* Drawers */}
        <JobDescriptionDrawer
          open={jdOpen}
          onClose={() => setJdOpen(false)}
          jobDescription={jobDescription}
          loading={loadingJd}
          copied={copiedJd}
          onCopy={() => {
            if (jobDescription) {
              navigator.clipboard.writeText(jobDescription);
              setCopiedJd(true);
              setTimeout(() => setCopiedJd(false), 2000);
            }
          }}
        />

        <HistoryDrawer
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
          loading={loadingHistory}
          generations={historyGenerations}
          onDeleted={(delId) =>
            setHistoryGenerations((prev) => prev.filter((g) => g.id !== delId))
          }
          onUpdated={(upId, updated) => {
            setHistoryGenerations((prev) =>
              prev.map((g) => (g.id === upId ? updated : g))
            );
            if (upId === params.id && updated.title) {
              setGenerationTitle(updated.title);
            }
          }}
          onSelect={(selectedId) => {
            setHistoryOpen(false);
            router.push(`/dashboard/results/${selectedId}`);
          }}
        />

        {/* Top Header */}
        <div className="flex items-center justify-between" style={{ marginBottom: "1rem", flexShrink: 0 }}>
          <div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>
              {done ? "Resume ready" : "Rewriting your resume"}
            </h2>
            <p className="text-muted text-xs" style={{ margin: "0.2rem 0 0" }}>
              Generation ID: {params.id}
            </p>
          </div>
          <Link
            href="/dashboard"
            className="btn btn-ghost btn-sm"
          >
            ← Back to Dashboard
          </Link>
        </div>

        {/* Generation in Progress */}
        {!fatalError && !done && !connectionError && (
          <GenerationProgressCard
            stopping={stopping}
            onStop={handleStopGeneration}
          />
        )}

        {/* Fatal Error */}
        {fatalError && (
          <div
            className="nm-card"
            style={{
              borderColor: "rgba(220, 38, 38, 0.4)",
              padding: "1.5rem",
              textAlign: "center",
            }}
          >
            <h3 style={{ color: "var(--color-destructive)", margin: "0 0 0.5rem" }}>
              Generation Error
            </h3>
            <p className="text-muted text-sm">{fatalError}</p>
            <button
              onClick={handleRetryGeneration}
              disabled={retrying}
              className="btn btn-primary btn-sm"
              style={{ marginTop: "1rem" }}
            >
              {retrying ? "Retrying…" : "Retry"}
            </button>
          </div>
        )}

        {/* Preview & Action Buttons */}
        {rewrittenResume && (
          <>
            <ResumePreviewer
              generationId={params.id}
              generationTitle={generationTitle}
              pdfBlobUrl={pdfBlobUrl}
              onError={(err) => setDownloadError(err)}
            />

            <ResultsActionBar
              generationId={params.id}
              pdfFileName={pdfFileName}
              jdOpen={jdOpen}
              onToggleJd={toggleJd}
              historyOpen={historyOpen}
              onToggleHistory={toggleHistory}
              atsScore={atsScore}
              onError={(err) => setDownloadError(err || null)}
            />
          </>
        )}
      </div>
    </div>
  );
}
