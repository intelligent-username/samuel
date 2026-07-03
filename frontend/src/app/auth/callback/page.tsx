"use client";

import { useEffect, useRef, Suspense } from "react";

import { useRouter, useSearchParams } from "next/navigation";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const called = useRef(false);
  const params = searchParams ?? new URLSearchParams();

  const code = params.get("code");
  const state = params.get("state");

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    if (!code || !state) {
      router.replace("/");
      return;
    }

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(
      `${apiBase}/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
      { credentials: "include" }
    )
      .then((res) => {
        if (res.ok) {
          router.replace("/dashboard");
        } else {
          router.replace("/?error=auth_failed");
        }
      })
      .catch(() => {
        router.replace("/?error=auth_failed");
      });
  }, [code, state, router]);

  return (
    <main style={{ minHeight: "100vh", background: "var(--color-background)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <span className="spinner spinner-lg" />
    </main>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <main style={{ minHeight: "100vh", background: "var(--color-background)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span className="spinner spinner-lg" />
      </main>
    }>
      <CallbackHandler />
    </Suspense>
  );
}