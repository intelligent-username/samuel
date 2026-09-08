"use client";

import React, { useRef, useState } from "react";
import type { Generation } from "@/lib/types";
import GenerationStatusChip from "./GenerationStatusChip";

interface GenerationCardProps {
  gen: Generation;
  compact?: boolean;
  isChecked: boolean;
  isSelectMode: boolean;
  actionGenId: string | null;
  hoveredTagGenId: string | null;
  onHoverTag: (id: string | null) => void;
  onClick: (id: string) => void;
  onCheck: (id: string, e: React.MouseEvent | React.ChangeEvent) => void;
  onDeleteRequest: (gen: Generation) => void;
  onStop: (gen: Generation, e: React.MouseEvent) => void;
  onRetry: (gen: Generation, e: React.MouseEvent) => void;
  onUpdated?: (id: string, updated: Generation) => void;
  updateGenerationFn: (id: string, title: string) => Promise<Generation>;
}

export default function GenerationCard({
  gen,
  compact = false,
  isChecked,
  isSelectMode,
  actionGenId,
  hoveredTagGenId,
  onHoverTag,
  onClick,
  onCheck,
  onDeleteRequest,
  onStop,
  onRetry,
  onUpdated,
  updateGenerationFn,
}: GenerationCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const editInputRef = useRef<HTMLInputElement | null>(null);

  const createdAt = new Date(gen.created_at).toLocaleString();
  const snippet = gen.job_description_text?.slice(0, 140).replace(/\n/g, " ");

  const startRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditing(true);
    const initial = gen.title ?? gen.job_description_text?.slice(0, 140).replace(/\n/g, " ") ?? "";
    setEditValue(initial);
    setTimeout(() => {
      editInputRef.current?.focus();
      editInputRef.current?.select();
    }, 50);
  };

  const cancelRename = () => {
    setIsEditing(false);
    setEditValue("");
  };

  const saveRename = async () => {
    if (isSaving) return;
    const trimmed = editValue.trim();
    setIsSaving(true);
    try {
      const updated = await updateGenerationFn(gen.id, trimmed);
      if (onUpdated) onUpdated(gen.id, updated);
      setIsEditing(false);
    } catch {
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className="nm-card"
      style={{
        cursor: "pointer",
        transition: "border-color 0.18s ease, background 0.15s ease",
        padding: compact ? "0.875rem 1rem" : "1.25rem 1.5rem",
        position: "relative",
        borderColor: isChecked ? "var(--color-primary)" : "var(--color-border)",
        background: isChecked ? "rgba(0, 102, 153, 0.08)" : "var(--color-card)",
      }}
      onClick={() => onClick(gen.id)}
      onMouseEnter={(e) => {
        if (!isChecked) e.currentTarget.style.borderColor = "var(--color-primary)";
      }}
      onMouseLeave={(e) => {
        if (!isChecked) e.currentTarget.style.borderColor = "var(--color-border)";
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.75rem" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {isEditing ? (
            <div
              onClick={(e) => e.stopPropagation()}
              style={{ marginBottom: "0.35rem", display: "flex", alignItems: "center", gap: "0.4rem" }}
            >
              <input
                ref={editInputRef}
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveRename();
                  else if (e.key === "Escape") cancelRename();
                }}
                onBlur={saveRename}
                disabled={isSaving}
                maxLength={255}
                className="input"
                style={{
                  padding: "0.2rem 0.45rem",
                  fontSize: compact ? "0.84rem" : "0.9rem",
                  fontWeight: 500,
                  width: "100%",
                  background: "var(--color-background)",
                  borderColor: "var(--color-primary)",
                  borderRadius: "4px",
                }}
                placeholder="Name this generation..."
              />
            </div>
          ) : (
            <p
              title="Double-click to rename"
              onClick={(e) => e.stopPropagation()}
              onDoubleClick={startRename}
              style={{
                fontWeight: 500,
                fontSize: compact ? "0.84rem" : "0.9rem",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                marginBottom: "0.35rem",
                paddingRight: "0.5rem",
                cursor: "text",
                color: "var(--color-foreground)",
              }}
            >
              {gen.title ? gen.title : `${snippet || "No job description"}...`}
            </p>
          )}
          <span className="text-xs text-muted">{createdAt}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexShrink: 0 }}>
          <GenerationStatusChip
            gen={gen}
            compact={compact}
            actionGenId={actionGenId}
            hoveredTagGenId={hoveredTagGenId}
            onHoverTag={onHoverTag}
            onStop={onStop}
            onRetry={onRetry}
          />

          {isSelectMode ? (
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                width: "24px",
                height: "24px",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <input
                type="checkbox"
                checked={isChecked}
                onChange={(e) => onCheck(gen.id, e)}
                className="checkbox-control"
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteRequest(gen);
              }}
              title="Delete generation"
              aria-label={`Delete generation from ${createdAt}`}
              style={{
                width: "24px",
                height: "24px",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "4px",
                border: "1px solid transparent",
                background: "transparent",
                color: "var(--color-muted-fg)",
                cursor: "pointer",
                fontSize: "1rem",
                lineHeight: 1,
                transition: "all 0.15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(153,27,27,0.14)";
                e.currentTarget.style.color = "var(--color-destructive)";
                e.currentTarget.style.borderColor = "rgba(153,27,27,0.2)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = "var(--color-muted-fg)";
                e.currentTarget.style.borderColor = "transparent";
              }}
            >
              ×
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
