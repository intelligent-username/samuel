"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  const code = searchParams.get("code");
  const state = searchParams.get("state");

  useEffect(() => {
    if (!code || !state) {
      router.push("/");
      return;
    }

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:1112";
    fetch(
      `${apiBase}/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
      { credentials: "include" }
    )
      .then((res) => {
        if (!res.ok) throw new Error("Auth failed");
        router.push("/dashboard");
      })
      .catch((err) => {
        setError(err.message);
      });
  }, [code, state, router]);

  if (error) {
    return (
      <p>
        Authentication failed. <a href="/">Try again</a>
      </p>
    );
  }

  return <p>Authenticating...</p>;
}

export default function AuthCallback() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <CallbackHandler />
    </Suspense>
  );
}