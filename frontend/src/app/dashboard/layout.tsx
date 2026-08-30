"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchMe } from "@/lib/api";
import BorromeanLoader from "@/components/BorromeanLoader";

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
      <div className="viewport-center">
        <BorromeanLoader size={96} label="Loading…" />
      </div>
    );
  }

  return (
    <div className="viewport-shell">
      <main style={{ padding: 0 }}>
        {children}
      </main>
    </div>
  );
}
