"use client";

type StatusPopoverProps = {
  message: { text: string; type: "info" | "success" | "error" } | null;
};

export default function StatusPopover({ message }: StatusPopoverProps) {
  if (message === null) return null;

  const color =
    message.type === "error"
      ? "var(--color-destructive)"
      : message.type === "success"
        ? "var(--color-success)"
        : "var(--color-primary)";

  return (
    <div
      className="popover-card"
      style={{
        top: "calc(100% + 0.75rem)",
        left: 0,
        right: 0,
        padding: "0.75rem 1rem",
        borderRadius: "8px",
        color,
        fontSize: "0.875rem",
        fontWeight: 500,
        zIndex: 10,
      }}
    >
      {message.text}
    </div>
  );
}
