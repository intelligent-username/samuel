"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchMe } from "@/lib/api";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    fetchMe()
      .then(() => setLoading(false))
      .catch(() => router.push("/"));
  }, [router]);

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--color-background)",
        }}
      >
        <div style={{ textAlign: "center", gap: "1rem", display: "flex", flexDirection: "column", alignItems: "center" }}>
          <span className="spinner spinner-lg" />
          <p className="text-muted">Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: "var(--color-background)" }}>
      <main style={{ padding: 0 }}>
        {children}
      </main>
    </div>
  );
}