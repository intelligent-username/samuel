"use client";

type AtsThresholdControlProps = {
  value: number;
  onValueChange: (value: number) => void;
};

export default function AtsThresholdControl({ value, onValueChange }: AtsThresholdControlProps) {
  const clamp = (n: number) => Math.max(70, Math.min(100, n));

  return (
    <div className="nm-card" style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem" }}>
        <label
          htmlFor="ats-threshold"
          style={{
            fontSize: "0.72rem",
            fontWeight: 700,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            color: "var(--color-muted-fg)",
            display: "inline-flex",
            alignItems: "center",
          }}
        >
          Target ATS score
        </label>
        <span
          className="font-mono"
          aria-live="polite"
          style={{
            fontSize: "0.72rem",
            fontWeight: 600,
            fontVariantNumeric: "tabular-nums",
            letterSpacing: "0.02em",
            padding: "0.2rem 0.5rem",
            borderRadius: 6,
            border: "1px solid var(--color-border)",
            background: "var(--color-muted)",
            color:
              value < 80 ? "var(--color-muted-fg)" : value < 90 ? "var(--color-primary)" : "var(--color-success)",
            minWidth: "3.2rem",
            textAlign: "center",
          }}
        >
          {`${value} / 100`}
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.4rem", minWidth: 0 }}>
          <input
            id="ats-threshold"
            name="ats_threshold"
            type="range"
            min={70}
            max={100}
            step={1}
            value={value}
            aria-label="Target ATS score"
            aria-describedby="ats-threshold-help"
            autoComplete="off"
            inputMode="numeric"
            onChange={(e) => onValueChange(clamp(Number(e.target.value)))}
            onKeyDown={(e) => {
              if (e.key === "ArrowUp" || e.key === "ArrowRight") {
                e.preventDefault();
                onValueChange(clamp(value + 1));
              }
              if (e.key === "ArrowDown" || e.key === "ArrowLeft") {
                e.preventDefault();
                onValueChange(clamp(value - 1));
              }
            }}
            style={{
              width: "100%",
              accentColor: "var(--color-primary)",
              touchAction: "manipulation",
              WebkitTapHighlightColor: "transparent",
              height: 16,
              cursor: "pointer",
            }}
          />
          <div
            style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", lineHeight: 1, fontVariantNumeric: "tabular-nums" }}
            className="font-mono text-muted"
          >
            <span>70</span>
            <span>75</span>
            <span>80</span>
            <span>85</span>
            <span>90</span>
            <span>95</span>
            <span>100</span>
          </div>
        </div>

        <label
          htmlFor="ats-threshold-number"
          className="text-xs"
          style={{
            position: "absolute",
            width: 1,
            height: 1,
            overflow: "hidden",
            clip: "rect(0 0 0 0)",
            clipPath: "inset(50%)",
            whiteSpace: "nowrap",
          }}
        >
          Target score number
        </label>
        <input
          id="ats-threshold-number"
          name="ats_threshold_number"
          type="number"
          inputMode="numeric"
          autoComplete="off"
          spellCheck={false}
          min={70}
          max={100}
          step={1}
          value={value}
          aria-label="Target ATS score number"
          onChange={(e) => {
            const val = Number(e.target.value);
            if (!Number.isNaN(val)) {
              onValueChange(clamp(val));
            }
          }}
          onBlur={(e) => {
            const n = Number(e.target.value);
            if (Number.isNaN(n) || n < 70) onValueChange(70);
            else if (n > 100) onValueChange(100);
            (e.currentTarget as HTMLInputElement).style.borderColor = "var(--color-border)";
          }}
          style={{
            width: "4rem",
            padding: "0.35rem 0.5rem",
            borderRadius: 8,
            border: "1px solid var(--color-border)",
            background: "var(--color-background)",
            color: "var(--color-foreground)",
            fontFamily: "Fira Code, monospace",
            fontSize: "0.85rem",
            fontVariantNumeric: "tabular-nums",
            textAlign: "center",
            outline: "none",
            flexShrink: 0,
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = "var(--color-primary)";
          }}
        />
      </div>

      <div
        id="ats-threshold-help"
        style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.72rem", color: "var(--color-muted-fg)", lineHeight: 1.4 }}
      >
        <span
          aria-hidden="true"
          style={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            border: "1px solid var(--color-border)",
            display: "inline-grid",
            placeItems: "center",
            flexShrink: 0,
            fontSize: 8,
            lineHeight: 1,
          }}
        >
          i
        </span>
        <span className="font-mono" style={{ fontSize: "0.7rem" }}>
          {value < 80
            ? "Standard alignment: fast generation."
            : value < 90
              ? "High precision: retries if score is low."
              : "Strict optimization: retries until cap."}
        </span>
      </div>
    </div>
  );
}
