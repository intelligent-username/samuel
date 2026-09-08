"use client";

interface DeleteConfirmModalProps {
  isOpen: boolean;
  count: number;
  isDeleting: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export default function DeleteConfirmModal({
  isOpen,
  count,
  isDeleting,
  error,
  onCancel,
  onConfirm,
}: DeleteConfirmModalProps) {
  if (!isOpen) return null;

  const isMulti = count > 1;

  return (
    <div
      className="modal-backdrop"
      onClick={() => !isDeleting && onCancel()}
    >
      <div
        className="nm-card modal-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>
          {isMulti ? `Delete ${count} Generations` : "Delete Generation"}
        </h3>
        <p className="text-muted" style={{ fontSize: "0.875rem", marginBottom: "1.25rem", color: "var(--color-foreground)" }}>
          Are you sure? This is permanent
        </p>
        {error && (
          <p style={{ color: "var(--color-destructive)", fontSize: "0.8rem", marginBottom: "1rem" }}>
            {error}
          </p>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={onCancel}
            disabled={isDeleting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-sm btn-destructive"
            onClick={onConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <span className="spinner spinner-sm" />
            ) : isMulti ? (
              `Delete (${count})`
            ) : (
              "Delete"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
