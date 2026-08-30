"use client";

import { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import BorromeanLoader from "@/components/BorromeanLoader";

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
    <main className="viewport-center">
      <BorromeanLoader size={96} label="Authenticating…" />
    </main>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <main className="viewport-center">
        <BorromeanLoader size={96} label="Loading…" />
      </main>
    }>
      <CallbackHandler />
    </Suspense>
  );
}