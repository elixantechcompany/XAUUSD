"use client";
import { useState, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConfirmDialogProps {
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  requireTyped?: string; // user must type this string to confirm
  onConfirm: () => void | Promise<void>;
  children: ReactNode;
}

export function ConfirmDialog({
  title, description, confirmLabel = "Confirm", cancelLabel = "Cancel",
  danger, requireTyped, onConfirm, children,
}: ConfirmDialogProps) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped]   = useState("");
  const [loading, setLoading] = useState(false);

  const canConfirm = !requireTyped || typed === requireTyped;

  async function handleConfirm() {
    if (!canConfirm) return;
    setLoading(true);
    try {
      await onConfirm();
    } finally {
      setLoading(false);
      setOpen(false);
      setTyped("");
    }
  }

  return (
    <>
      <span onClick={() => setOpen(true)} className="contents">{children}</span>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/60"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
        >
          <div className="bg-surface border border-border rounded-card w-full max-w-sm p-6 space-y-4 shadow-xl">
            {danger && (
              <div className="flex items-center gap-2 text-loss">
                <AlertTriangle className="w-5 h-5" aria-hidden />
                <span className="text-sm font-medium">Dangerous action</span>
              </div>
            )}
            <h2 id="confirm-title" className="text-text-primary font-semibold text-base">
              {title}
            </h2>
            <p className="text-text-secondary text-sm">{description}</p>

            {requireTyped && (
              <div className="space-y-1">
                <label className="text-xs text-text-secondary">
                  Type <code className="text-loss font-mono">{requireTyped}</code> to confirm
                </label>
                <input
                  type="text"
                  value={typed}
                  onChange={e => setTyped(e.target.value)}
                  className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
                  autoFocus
                />
              </div>
            )}

            <div className="flex gap-3 pt-1">
              <button
                onClick={() => { setOpen(false); setTyped(""); }}
                className="flex-1 px-4 py-2.5 text-sm font-medium rounded bg-surface-2 border border-border text-text-primary hover:bg-border transition-colors min-h-[44px]"
              >
                {cancelLabel}
              </button>
              <button
                onClick={handleConfirm}
                disabled={!canConfirm || loading}
                className={cn(
                  "flex-1 px-4 py-2.5 text-sm font-medium rounded transition-colors min-h-[44px]",
                  danger
                    ? "bg-loss text-white hover:bg-red-600 disabled:opacity-40"
                    : "bg-accent text-white hover:bg-blue-600 disabled:opacity-40"
                )}
              >
                {loading ? "Working…" : confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
