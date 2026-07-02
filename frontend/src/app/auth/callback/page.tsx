import { redirect } from "next/navigation";

export default function AuthCallback({
  searchParams,
}: {
  searchParams: { code?: string; state?: string };
}) {
  const code = searchParams.code;
  const state = searchParams.state;
  if (!code || !state) {
    redirect("/");
  }

  return <AuthCallbackHandler code={code} state={state} />;
}

async function AuthCallbackHandler({ code, state }: { code: string; state: string }) {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
    { credentials: "include" },
  );

  if (!res.ok) {
    return <p>Authentication failed. <a href="/">Try again</a></p>;
  }

  redirect("/dashboard");
}