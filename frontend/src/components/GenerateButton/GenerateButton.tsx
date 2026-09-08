"use client";

type GenerateButtonProps = {
  generating: boolean;
  disabled: boolean;
  onClick: () => void;
};

export default function GenerateButton({ generating, disabled, onClick }: GenerateButtonProps) {
  return (
    <button id="generate-btn" onClick={onClick} disabled={disabled} className="btn btn-accent btn-lg">
      {generating && <span className="spinner spinner-sm" />}
      {generating ? "Starting generation..." : "Generate Rewritten Resume"}
    </button>
  );
}
