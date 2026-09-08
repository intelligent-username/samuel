"use client";

import GenerateButton from "@/components/GenerateButton";
import StatusPopover from "@/components/StatusPopover";

type GenerateActionProps = {
  generating: boolean;
  disabled: boolean;
  onGenerate: () => void;
  message: { text: string; type: "info" | "success" | "error" } | null;
};

export default function GenerateAction({ generating, disabled, onGenerate, message }: GenerateActionProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", flexShrink: 0, position: "relative" }}>
      <GenerateButton generating={generating} disabled={disabled} onClick={onGenerate} />
      <StatusPopover message={message} />
    </div>
  );
}
