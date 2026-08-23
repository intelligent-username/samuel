import React from "react";

interface BorromeanLogoProps {
  size?: number | string;
  className?: string;
  style?: React.CSSProperties;
}

export default function BorromeanLogo({
  size = 24,
  className,
  style,
}: BorromeanLogoProps) {
  const s = typeof size === "number" ? `${size}px` : size;

  return (
    <span
      className={className}
      style={{
        width: s,
        height: s,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        flexShrink: 0,
        verticalAlign: "middle",
        userSelect: "none",
        ...style,
      }}
      aria-label="Samuel 3D Borromean Sculpture Logo"
    >
      <img
        src="/logo.png"
        alt="Samuel Borromean Logo"
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          display: "block",
          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.4))",
        }}
      />
    </span>
  );
}
