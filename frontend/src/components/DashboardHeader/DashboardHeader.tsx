"use client";

type DashboardHeaderProps = {
  title?: string;
  subtitle?: string;
};

export default function DashboardHeader({
  title = "Samuel: Your Resume Tailor",
  subtitle = "Paste a job description and upload your resume to generate a tailored version.",
}: DashboardHeaderProps) {
  return (
    <>
      <h1 style={{ fontSize: "2.5rem", fontWeight: 800, textAlign: "center", marginBottom: "0.5rem", letterSpacing: "-0.025em" }}>
        {title}
      </h1>
      <p className="text-muted" style={{ textAlign: "center", marginBottom: "3rem", fontSize: "0.9rem" }}>
        {subtitle}
      </p>
    </>
  );
}
