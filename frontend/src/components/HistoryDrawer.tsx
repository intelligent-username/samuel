"use client";

import React from "react";
import HistoryList from "@/components/HistoryList";
import type { Generation } from "@/lib/types";

interface HistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  loading: boolean;
  generations: Generation[];
  onDeleted: (delId: string) => void;
  onUpdated: (upId: string, updated: Generation) => void;
  onSelect: (selectedId: string) => void;
}

export default function HistoryDrawer({
  open,
  onClose,
  loading,
  generations,
  onDeleted,
  onUpdated,
  onSelect,
}: HistoryDrawerProps) {
  if (!open) return null;

  return (
    <aside
      className="side-panel-right"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="side-dialog-panel nm-card"
        style={{
          background: "var(--color-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "14px",
          padding: "1.25rem",
          display: "flex",
          flexDirection: "column",
          animation: "historyDialogIn 0.28s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1rem",
            borderBottom: "1px solid var(--color-border)",
            paddingBottom: "0.75rem",
          }}
        >
          <div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>
              Generation History
            </h3>
            <p className="text-muted text-xs" style={{ margin: "0.2rem 0 0" }}>
              Your past tailored resumes & logs
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn btn-ghost btn-xs"
            style={{
              fontSize: "1.25rem",
              lineHeight: 1,
              padding: "0.2rem 0.45rem",
              borderRadius: "4px",
            }}
            title="Close (Esc)"
          >
            ×
          </button>
        </div>

        {loading ? (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              flex: 1,
              padding: "3rem 0",
            }}
          >
            <span className="spinner spinner-lg" />
          </div>
        ) : (
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              maxHeight: "calc(100vh - 10rem)",
            }}
            className="custom-scrollbar"
          >
            <HistoryList
              generations={generations}
              compact
              onDeleted={onDeleted}
              onUpdated={onUpdated}
              onSelect={onSelect}
            />
          </div>
        )}
      </div>
    </aside>
  );
}
