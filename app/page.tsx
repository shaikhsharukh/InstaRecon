"use client";

import { useState } from "react";
import { useRecon } from "./hooks/useRecon";
import UrlInputBar from "./components/UrlInputBar";
import SwarmStatusPanel from "./components/SwarmStatusPanel";
import LiveFindingsFeed from "./components/LiveFindingsFeed";
import SponsorTelemetry from "./components/SponsorTelemetry";

export default function Home() {
  const {
    status,
    agents,
    findings,
    error,
    reconnecting,
    reconnectAttempt,
    startRecon,
    sendEmail,
    downloadPdf,
    reset,
    overallProgress,
    telemetry,
    cached,
    cachedAt,
  } = useRecon();
  const [email, setEmail] = useState("");
  const [emailStatus, setEmailStatus] = useState<string | null>(null);

  const isRunning = status === "running";
  const isComplete = status === "complete";

  const handleSendEmail = async () => {
    if (!email || !email.includes("@")) return;
    setEmailStatus("sending...");
    const result = await sendEmail(email);
    setEmailStatus(result?.status === "sent" ? "✓ Sent!" : "✗ Failed");
    setTimeout(() => setEmailStatus(null), 3000);
  };

  return (
    <main style={styles.main}>
      <div style={styles.container}>
        <header style={styles.header}>
          <h1 style={styles.title}>InstaRecon</h1>
          <p style={styles.tagline}>Instant Company Intelligence</p>
        </header>

        <div style={styles.inputSection}>
          <UrlInputBar onSubmit={startRecon} disabled={isRunning} />
        </div>

        {cached && (
          <div style={styles.cacheBanner}>
            <span>📦 Cached result (from {cachedAt})</span>
          </div>
        )}

        {error && (
          <div style={styles.banner}>
            <span>{error}</span>
            <button onClick={reset} style={styles.retryButton}>
              Try Again
            </button>
          </div>
        )}

        {reconnecting && (
          <div style={styles.reconnectBanner}>
            <span>🔄 Reconnecting... (attempt {reconnectAttempt})</span>
          </div>
        )}

        {isRunning && (
          <div style={styles.progressSection}>
            <div style={styles.progressHeader}>
              <span style={styles.progressLabel}>Overall Progress</span>
              <span style={styles.progressPercent}>{overallProgress}%</span>
            </div>
            <div style={styles.progressTrack}>
              <div
                style={{
                  ...styles.progressBar,
                  width: `${overallProgress}%`,
                }}
              />
            </div>
          </div>
        )}

        <div style={styles.panelSection}>
          <SwarmStatusPanel agents={agents} />
        </div>

        <div style={styles.feedSection}>
          <LiveFindingsFeed findings={findings} />
        </div>

        {isComplete && (
          <div style={styles.completeSection}>
            <div style={styles.completeBanner}>
              Investigation complete.
            </div>
            <div style={styles.actionRow}>
              <button onClick={downloadPdf} style={styles.actionButton}>
                📄 Download PDF
              </button>
              <div style={styles.emailRow}>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  style={styles.emailInput}
                />
                <button
                  onClick={handleSendEmail}
                  disabled={!email || !email.includes("@")}
                  style={{
                    ...styles.actionButton,
                    ...(!email || !email.includes("@") ? styles.buttonDisabled : {}),
                  }}
                >
                  {emailStatus || "📧 Send Email"}
                </button>
              </div>
              <button onClick={reset} style={styles.newButton}>
                New Investigation
              </button>
            </div>
          </div>
        )}

        <div style={styles.telemetrySection}>
          <SponsorTelemetry
            telemetry={telemetry}
            isLoading={isRunning}
            jobComplete={isComplete}
          />
        </div>
      </div>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  main: {
    minHeight: "100vh",
    background: "#0a0a0f",
    color: "#e2e8f0",
    fontFamily:
      "'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  container: {
    maxWidth: 840,
    margin: "0 auto",
    padding: "40px 24px",
    display: "flex",
    flexDirection: "column",
    gap: 24,
  },
  header: {
    textAlign: "center",
    marginBottom: 8,
  },
  title: {
    fontSize: 32,
    fontWeight: 700,
    margin: 0,
    background: "linear-gradient(135deg, #6366f1, #a78bfa)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  tagline: {
    fontSize: 14,
    color: "rgba(255,255,255,0.4)",
    margin: "4px 0 0",
  },
  inputSection: {
    display: "flex",
    justifyContent: "center",
  },
  cacheBanner: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "10px 16px",
    borderRadius: 10,
    background: "rgba(251, 191, 36, 0.1)",
    border: "1px solid rgba(251, 191, 36, 0.3)",
    color: "#fbbf24",
    fontSize: 13,
    fontWeight: 500,
  },
  progressSection: {
    background: "rgba(255,255,255,0.03)",
    borderRadius: 12,
    padding: "12px 16px",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  progressHeader: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  progressLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: "rgba(255,255,255,0.5)",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  progressPercent: {
    fontSize: 12,
    fontWeight: 700,
    color: "#818cf8",
  },
  progressTrack: {
    width: "100%",
    height: 6,
    background: "rgba(255,255,255,0.08)",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressBar: {
    height: "100%",
    background: "linear-gradient(90deg, #6366f1, #a78bfa)",
    borderRadius: 3,
    transition: "width 0.5s ease",
  },
  panelSection: {},
  feedSection: {},
  telemetrySection: {},
  banner: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 16px",
    borderRadius: 10,
    background: "rgba(239, 68, 68, 0.12)",
    border: "1px solid rgba(239, 68, 68, 0.3)",
    color: "#fca5a5",
    fontSize: 14,
  },
  reconnectBanner: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "10px 16px",
    borderRadius: 10,
    background: "rgba(251, 191, 36, 0.1)",
    border: "1px solid rgba(251, 191, 36, 0.3)",
    color: "#fbbf24",
    fontSize: 13,
    fontWeight: 500,
  },
  retryButton: {
    padding: "6px 14px",
    borderRadius: 8,
    border: "1px solid rgba(239,68,68,0.4)",
    background: "transparent",
    color: "#fca5a5",
    cursor: "pointer",
    fontSize: 12,
  },
  completeSection: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  completeBanner: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "14px 18px",
    borderRadius: 10,
    background: "rgba(34, 197, 94, 0.1)",
    border: "1px solid rgba(34, 197, 94, 0.25)",
    color: "#34d399",
    fontSize: 14,
    fontWeight: 500,
  },
  actionRow: {
    display: "flex",
    gap: 12,
    alignItems: "center",
    flexWrap: "wrap",
  },
  actionButton: {
    padding: "10px 20px",
    borderRadius: 10,
    border: "1px solid rgba(99,102,241,0.4)",
    background: "rgba(99,102,241,0.15)",
    color: "#a78bfa",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
    whiteSpace: "nowrap",
  },
  buttonDisabled: {
    opacity: 0.4,
    cursor: "not-allowed",
  },
  emailRow: {
    display: "flex",
    gap: 8,
    alignItems: "center",
    flex: 1,
  },
  emailInput: {
    flex: 1,
    padding: "10px 14px",
    borderRadius: 10,
    border: "1px solid rgba(255,255,255,0.1)",
    background: "rgba(255,255,255,0.06)",
    color: "#fff",
    fontSize: 13,
    outline: "none",
    minWidth: 160,
  },
  newButton: {
    padding: "10px 20px",
    borderRadius: 10,
    border: "1px solid rgba(34,197,94,0.4)",
    background: "transparent",
    color: "#34d399",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
  },
};
