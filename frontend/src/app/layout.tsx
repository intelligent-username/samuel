import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Samuel: Your Rewriter",
  description: "Tailor your resume to any job description using AI-powered semantic matching and smart rewriting.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  );
}
