"use client";

import React from "react";
import Borromean3DViewer from "@/components/Borromean3DViewer";

interface BorromeanLoaderProps {
  size?: number;
  label?: string | null;
  className?: string;
  style?: React.CSSProperties;
}

export default function BorromeanLoader({
  size = 80,
  label = "Loading…",
  className,
  style,
}: BorromeanLoaderProps) {
  return (
    <div
      className={className}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: label ? "0.75rem" : 0,
        ...style,
      }}
    >
      <Borromean3DViewer
        width={size}
        height={size}
        color="blue"
        interactive={false}
        speed="normal"
      />
      {label && (
        <p className="text-muted" style={{ margin: 0, fontSize: "0.875rem", fontWeight: 500 }}>
          {label}
        </p>
      )}
    </div>
  );
}
