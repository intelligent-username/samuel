"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe } from "@/lib/api";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<{ github_username: string } | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        setLoading(false);
      })
      .catch(() => {
        router.push("/auth/login");
      });
  }, [router]);

  if (loading) {
    return <div style={{ padding: "2rem", textAlign: "center" }}>Loading...</div>;
  }

  return (
    <div>
      <header style={{ borderBottom: "1px solid #e0e0e0", padding: "1rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong>Samuel</strong>
        <span style={{ color: "#666", fontSize: "0.875rem" }}>{user?.github_username}</span>
      </header>
      <main style={{ padding: "2rem", maxWidth: "960px", margin: "0 auto" }}>
        {children}
      </main>
    </div>
  );
}