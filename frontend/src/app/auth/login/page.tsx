"use client";

import { useEffect, useState } from "react";

import { getLoginUrl } from "@/lib/api";

export default function LoginPage() {
  const [loginUrl, setLoginUrl] = useState("");

  useEffect(() => {
    getLoginUrl().then((url) => setLoginUrl(url)).catch((err) => console.error("Failed to get login URL:", err));
  }, []);

  return (
    <main style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>Samuel</h1>
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