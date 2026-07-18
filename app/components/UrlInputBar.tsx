"use client";

import { useState, FormEvent } from "react";

interface UrlInputBarProps {
  onSubmit: (url: string) => void;
  disabled?: boolean;
}

const LOOSE_URL = /^https?:\/\//i;
const HAS_DOT = /\./;

export default function UrlInputBar({ onSubmit, disabled }: UrlInputBarProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const trimmed = url.trim();
  const hasProtocol = LOOSE_URL.test(trimmed);
  const looksLikeDomain = HAS_DOT.test(trimmed) && !hasProtocol;
  const isValid = hasProtocol || looksLikeDomain;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const raw = url.trim();
    if (!raw) {
      setError("Please enter a URL.");
      return;
    }

    let normalized = raw;
    if (!LOOSE_URL.test(raw)) {
      normalized = `https://${raw}`;
    }

    onSubmit(normalized);
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.inputWrapper}>
        <input
          type="text"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setError(null);
          }}
          placeholder="Enter a company URL to investigate..."
          disabled={disabled}
          style={{
            ...styles.input,
            ...(disabled ? styles.inputDisabled : {}),
          }}
        />
        <button
          type="submit"
          disabled={disabled || !isValid}
          style={{
            ...styles.button,
            ...(disabled || !isValid ? styles.buttonDisabled : {}),
          }}
        >
          {disabled ? "Investigating..." : "Investigate"}
        </button>
      </div>
      {error && <div style={styles.error}>{error}</div>}
    </form>
  );
}

const styles: Record<string, React.CSSProperties> = {
  form: {
    width: "100%",
    maxWidth: 700,
    margin: "0 auto",
  },
  inputWrapper: {
    display: "flex",
    gap: 12,
    alignItems: "center",
  },
  input: {
    flex: 1,
    padding: "14px 20px",
    fontSize: 16,
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.1)",
    background: "rgba(255,255,255,0.06)",
    color: "#fff",
    outline: "none",
    backdropFilter: "blur(12px)",
    transition: "border-color 0.2s",
  },
  inputDisabled: {
    opacity: 0.5,
  },
  button: {
    padding: "14px 28px",
    fontSize: 16,
    fontWeight: 600,
    borderRadius: 12,
    border: "none",
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#fff",
    cursor: "pointer",
    whiteSpace: "nowrap",
    transition: "opacity 0.2s",
  },
  buttonDisabled: {
    opacity: 0.4,
    cursor: "not-allowed",
  },
  error: {
    marginTop: 8,
    padding: "8px 14px",
    borderRadius: 8,
    background: "rgba(239, 68, 68, 0.15)",
    color: "#fca5a5",
    fontSize: 14,
  },
};
