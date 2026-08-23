"use client";

import { useEffect, useState } from "react";

import { getLoginUrl } from "@/lib/api";
import BorromeanLogo from "@/components/BorromeanLogo";

export default function LoginPage() {
  const [loginUrl, setLoginUrl] = useState("");

  useEffect(() => {
    getLoginUrl().then((url) => setLoginUrl(url)).catch((err) => console.error("Failed to get login URL:", err));
  }, []);

  return (
    <main style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", marginBottom: "0.5rem" }}>
        <BorromeanLogo size={32} />
        <h1 style={{ fontSize: "2rem", margin: 0 }}>Samuel</h1>
      </div>
      <p style={{ color: "#666", marginBottom: "2rem" }}>
        AI-powered resume rewriting
      </p>
      <a
        href={loginUrl || "#"}
        style={{
          padding: "0.75rem 1.5rem",
          background: "#24292f",
          color: "#fff",
          borderRadius: "6px",
          fontWeight: 600,
          textDecoration: "none",
        }}
      >
        Login with GitHub
      </a>
    </main>
  );
}