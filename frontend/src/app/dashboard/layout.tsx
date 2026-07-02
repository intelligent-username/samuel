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

  return (
    <div style={{ minHeight: "100vh", background: "var(--color-background)" }}>
      {/* Header */}
      <header
        style={{
          background: "var(--color-card)",
          borderBottom: "1px solid var(--color-border)",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <div
          className="container"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            height: "60px",
          }}
        >
          {/* Brand */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "6px",
                background: "var(--color-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary-fg)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <span style={{ fontWeight: 700, fontSize: "1.05rem" }}>Samuel</span>
          </div>

          {/* Nav links */}
          <nav style={{ display: "flex", gap: "0.25rem" }}>
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="btn btn-ghost btn-sm"
                style={{
                  fontWeight: pathname === link.href ? 700 : 500,
                  color: pathname === link.href ? "var(--color-primary)" : undefined,
                }}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* User + logout */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div className="nm-card-sm" style={{ padding: "0.35rem 0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{ opacity: 0.6 }}>
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              <span className="text-sm" style={{ fontWeight: 500 }}>{user?.github_username}</span>
            </div>
            <button id="logout-btn" onClick={handleLogout} className="btn btn-ghost btn-sm">
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="container" style={{ paddingBlock: "2rem" }}>
        {children}
      </main>
    </div>
  );
}