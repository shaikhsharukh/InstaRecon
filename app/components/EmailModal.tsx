"use client";

import { useState, useRef, useEffect, FormEvent } from "react";

interface EmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSend: (email: string, note?: string) => Promise<void>;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function EmailModal({ isOpen, onClose, onSend }: EmailModalProps) {
  const [email, setEmail] = useState("");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setEmail("");
      setNote("");
      setStatus("idle");
      setErrorMessage(null);
      setValidationError(null);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!EMAIL_REGEX.test(email.trim())) {
      setValidationError("Please enter a valid email address.");
      return;
    }

    setStatus("sending");
    try {
      await onSend(email.trim(), note.trim() || undefined);
      setStatus("success");
    } catch {
      setStatus("error");
      setErrorMessage("Failed to send report. Please try again.");
    }
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      style={styles.overlay}
    >
      <div style={styles.modal}>
        {status === "success" ? (
          <div style={styles.successState}>
            <div style={styles.successIcon}>✓</div>
            <div style={styles.successText}>
              Report sent to {email}!
            </div>
            <button onClick={onClose} style={styles.doneButton}>
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={styles.form}>
            <h3 style={styles.title}>Email Report</h3>

            <label style={styles.label}>
              Email Address
              <input
                ref={inputRef}
                type="text"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setValidationError(null);
                }}
                placeholder="you@example.com"
                disabled={status === "sending"}
                style={{
                  ...styles.input,
                  ...(status === "sending" ? styles.inputDisabled : {}),
                  ...(validationError ? styles.inputError : {}),
                }}
              />
              {validationError && (
                <div style={styles.fieldError}>{validationError}</div>
              )}
            </label>

            <label style={styles.label}>
              Add a Note (optional)
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Optional message..."
                disabled={status === "sending"}
                rows={3}
                style={{
                  ...styles.textarea,
                  ...(status === "sending" ? styles.inputDisabled : {}),
                }}
              />
            </label>

            {status === "error" && errorMessage && (
              <div style={styles.errorBanner}>
                <span>{errorMessage}</span>
              </div>
            )}

            <div style={styles.buttonRow}>
              <button
                type="button"
                onClick={onClose}
                disabled={status === "sending"}
                style={styles.cancelButton}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={status === "sending"}
                style={{
                  ...styles.sendButton,
                  ...(status === "sending" ? styles.sendButtonDisabled : {}),
                }}
              >
                {status === "sending" ? (
                  <span style={styles.spinner} />
                ) : (
                  "Send"
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0, 0, 0, 0.6)",
    backdropFilter: "blur(4px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
    animation: "fadeIn 0.15s ease",
  },
  modal: {
    width: "90%",
    maxWidth: 420,
    background: "rgba(20, 20, 30, 0.95)",
    backdropFilter: "blur(16px)",
    borderRadius: 16,
    border: "1px solid rgba(255, 255, 255, 0.1)",
    boxShadow: "0 16px 48px rgba(0, 0, 0, 0.5)",
    padding: 24,
    animation: "fadeInUp 0.2s ease",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    color: "#e2e8f0",
    margin: 0,
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: "rgba(255,255,255,0.6)",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  input: {
    padding: "10px 14px",
    fontSize: 14,
    borderRadius: 10,
    border: "1px solid rgba(255,255,255,0.1)",
    background: "rgba(255,255,255,0.06)",
    color: "#e2e8f0",
    outline: "none",
    transition: "border-color 0.2s",
  },
  inputError: {
    borderColor: "rgba(239, 68, 68, 0.5)",
  },
  inputDisabled: {
    opacity: 0.5,
  },
  textarea: {
    padding: "10px 14px",
    fontSize: 14,
    borderRadius: 10,
    border: "1px solid rgba(255,255,255,0.1)",
    background: "rgba(255,255,255,0.06)",
    color: "#e2e8f0",
    outline: "none",
    resize: "vertical",
    fontFamily: "inherit",
    transition: "border-color 0.2s",
  },
  fieldError: {
    fontSize: 12,
    color: "#f87171",
    marginTop: 2,
  },
  errorBanner: {
    padding: "10px 14px",
    borderRadius: 8,
    background: "rgba(239, 68, 68, 0.15)",
    color: "#fca5a5",
    fontSize: 13,
  },
  buttonRow: {
    display: "flex",
    gap: 10,
    justifyContent: "flex-end",
  },
  cancelButton: {
    padding: "10px 18px",
    borderRadius: 10,
    border: "1px solid rgba(255,255,255,0.1)",
    background: "transparent",
    color: "rgba(255,255,255,0.5)",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 500,
  },
  sendButton: {
    padding: "10px 24px",
    borderRadius: 10,
    border: "none",
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#fff",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  sendButtonDisabled: {
    opacity: 0.6,
    cursor: "not-allowed",
  },
  spinner: {
    width: 16,
    height: 16,
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "#fff",
    borderRadius: "50%",
    animation: "spin 0.6s linear infinite",
  },
  successState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 12,
    padding: "20px 0",
  },
  successIcon: {
    width: 48,
    height: 48,
    borderRadius: "50%",
    background: "rgba(34, 197, 94, 0.2)",
    color: "#34d399",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 24,
    fontWeight: 700,
  },
  successText: {
    fontSize: 15,
    color: "#e2e8f0",
    textAlign: "center",
  },
  doneButton: {
    marginTop: 8,
    padding: "10px 28px",
    borderRadius: 10,
    border: "none",
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#fff",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
  },
};
