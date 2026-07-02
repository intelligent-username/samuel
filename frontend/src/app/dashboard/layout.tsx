"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { fetchMe, logout } from "@/lib/api";
import type { User } from "@/lib/types";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        setLoading(false);
      })
      .catch(() => router.push("/"));
  }, [router]);

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

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

  const navLinks = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/dashboard/history", label: "History" },
  ];

  const isDashboard = pathname.startsWith("/dashboard");

  return (
    <div style={{ background: "var(--color-background)" }}>
      {/* Header — hidden on all dashboard routes */}
      {!isDashboard && (
        <header
          style={{
            background: "rgba(18, 18, 22, 0.85)",
            backdropFilter: "blur(12px)",
            borderBottom: "1px solid var(--color-border)",
            position: "sticky",
            top: 0,
            zIndex: 100,
          }}
        >
          <div
            className="container"
            style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: "60px" }}
          >
            <Link href="/dashboard" style={{ display: "flex", alignItems: "center", gap: "0.6rem", textDecoration: "none" }} aria-label="Samuel Resume Rewriter">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span style={{ fontWeight: 700, fontSize: "1.05rem", color: "var(--color-foreground)" }}>Samuel</span>
            </Link>
            <nav style={{ display: "flex", gap: "1.5rem" }} aria-label="Main Navigation">
              {navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link key={link.href} href={link.href} style={{ fontSize: "0.8125rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", textDecoration: "none", color: isActive ? "var(--color-primary)" : "var(--color-muted-fg)", transition: "color 0.15s ease", borderBottom: isActive ? "2px solid var(--color-primary)" : "2px solid transparent", paddingBlock: "0.25rem" }}>
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </header>
      )}

      {/* Page content */}
      <main style={{ padding: 0 }}>
        {children}
      </main>
    </div>
  );
}