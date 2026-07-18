"use client";

import type { TelemetryData } from "../hooks/useRecon";

interface SponsorTelemetryProps {
  telemetry: Record<string, TelemetryData>;
  isLoading?: boolean;
  jobComplete?: boolean;
}

const SPONSOR_INFO: Record<string, { name: string; icon: string; color: string }> = {
  oxylabs: { name: "Oxylabs", icon: "🌐", color: "#3b82f6" },
  kimi: { name: "Kimi AI", icon: "🧠", color: "#8b5cf6" },
  daytona: { name: "Daytona", icon: "⚡", color: "#f97316" },
};

export default function SponsorTelemetry({ telemetry, isLoading, jobComplete }: SponsorTelemetryProps) {
  const services = Object.keys(SPONSOR_INFO);
  const hasData = services.some((s) => telemetry[s] && telemetry[s].calls > 0);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>⚡ Sponsor Telemetry</span>
        {isLoading && <span style={styles.liveBadge}>LIVE</span>}
      </div>
      <div style={styles.grid}>
        {services.map((key) => {
          const info = SPONSOR_INFO[key];
          const data = telemetry[key];
          const active = data && data.calls > 0;

          return (
            <div
              key={key}
              style={{
                ...styles.card,
                borderColor: active ? info.color + "40" : "rgba(255,255,255,0.06)",
                opacity: active ? 1 : 0.5,
              }}
            >
              <div style={styles.cardHeader}>
                <span style={styles.cardIcon}>{info.icon}</span>
                <span style={{ ...styles.cardName, color: info.color }}>{info.name}</span>
              </div>
              {active ? (
                <div style={styles.cardBody}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Calls</span>
                    <span style={styles.statValue}>{data.calls}</span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Success Rate</span>
                    <span style={styles.statValue}>
                      {data.calls > 0
                        ? Math.round((data.successes / data.calls) * 100)
                        : 0}
                      %
                    </span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Avg Latency</span>
                    <span style={styles.statValue}>
                      {data.calls > 0
                        ? Math.round(data.total_duration_ms / data.calls)
                        : 0}
                      ms
                    </span>
                  </div>
                  {data.calls > 0 && (
                    <div style={styles.progressTrack}>
                      <div
                        style={{
                          ...styles.progressBar,
                          width: `${Math.min(
                            100,
                            Math.round((data.successes / data.calls) * 100)
                          )}%`,
                          background: info.color,
                        }}
                      />
                    </div>
                  )}
                </div>
              ) : (
                <div style={styles.inactive}>
                  {isLoading ? "Waiting..." : "No calls"}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {hasData && jobComplete && (
        <div style={styles.footer}>
          {services
            .filter((s) => telemetry[s] && telemetry[s].calls > 0)
            .map((s) => {
              const d = telemetry[s];
              return (
                <span key={s} style={styles.footerItem}>
                  {SPONSOR_INFO[s].name}: {d.calls} calls,{" "}
                  {d.calls > 0
                    ? Math.round((d.successes / d.calls) * 100)
                    : 0}
                  % success
                </span>
              );
            })}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    borderRadius: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.06)",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 14px",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
  },
  title: {
    fontSize: 12,
    fontWeight: 600,
    color: "rgba(255,255,255,0.5)",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  liveBadge: {
    fontSize: 10,
    fontWeight: 700,
    color: "#22c55e",
    padding: "2px 8px",
    borderRadius: 4,
    background: "rgba(34,197,94,0.15)",
    animation: "pulse 2s ease-in-out infinite",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 8,
    padding: 10,
  },
  card: {
    borderRadius: 8,
    border: "1px solid",
    padding: 10,
    transition: "all 0.3s ease",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    marginBottom: 8,
  },
  cardIcon: {
    fontSize: 14,
  },
  cardName: {
    fontSize: 11,
    fontWeight: 600,
  },
  cardBody: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  statRow: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 11,
  },
  statLabel: {
    color: "rgba(255,255,255,0.4)",
  },
  statValue: {
    fontWeight: 600,
    color: "#e2e8f0",
  },
  progressTrack: {
    width: "100%",
    height: 3,
    background: "rgba(255,255,255,0.08)",
    borderRadius: 2,
    marginTop: 4,
    overflow: "hidden",
  },
  progressBar: {
    height: "100%",
    borderRadius: 2,
    transition: "width 0.3s ease",
  },
  inactive: {
    fontSize: 11,
    color: "rgba(255,255,255,0.25)",
    textAlign: "center",
    padding: "8px 0",
  },
  footer: {
    display: "flex",
    gap: 16,
    padding: "8px 14px",
    borderTop: "1px solid rgba(255,255,255,0.06)",
    fontSize: 10,
    color: "rgba(255,255,255,0.35)",
    flexWrap: "wrap",
  },
  footerItem: {
    whiteSpace: "nowrap",
  },
};
