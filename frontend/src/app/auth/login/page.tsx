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
    <main className="viewport-center" style={{ flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", marginBottom: "0.5rem" }}>
        <BorromeanLogo size={32} />
        <h1 style={{ fontSize: "2rem", margin: 0 }}>Samuel</h1>
      </div>
      <p className="text-muted" style={{ marginBottom: "2rem" }}>
        AI-powered resume rewriting
      </p>
      <a
        href={loginUrl || "#"}
        className="btn btn-primary btn-lg"
      >
        Login with GitHub
      </a>
    </main>
  );
}