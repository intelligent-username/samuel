"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { fetchGenerations } from "@/lib/api";
import type { Generation } from "@/lib/types";
import HistoryList from "@/components/HistoryList";

export default function HistoryPage() {
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGenerations()
      .then((data) => {
        setGenerations(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", paddingTop: "4rem" }}>
        <span className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--color-background)", padding: "2.5rem 1.5rem" }}>
      <main style={{ maxWidth: "860px", margin: "0 auto", display: "flex", flexDirection: "column" }}>
        {/* Top Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2rem" }}>
          <div>
            <h1
              style={{
                fontSize: "2rem",
                fontWeight: 800,
                margin: 0,
                letterSpacing: "-0.025em",
              }}
            >
              Generation History
            </h1>
            <p className="text-muted" style={{ margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
              Your past resume generations and optimization logs ({generations.length} total).
            </p>
          </div>
          <Link
            href="/dashboard"
            className="btn btn-ghost btn-sm"
            style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
          >
            ← Back to Dashboard
          </Link>
        </div>

        <HistoryList
          generations={generations}
          onDeleted={(id) =>
            setGenerations((prev) => prev.filter((g) => g.id !== id))
          }
          onUpdated={(id, updated) =>
            setGenerations((prev) =>
              prev.map((g) => (g.id === id ? updated : g))
            )
          }
        />
      </main>
    </div>
  );
}
