import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Samuel - AI Resume Rewriter",
  description: "Tailor your resume to any job description using AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
