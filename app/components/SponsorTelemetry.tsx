"use client";

import { useEffect, useState, useRef } from "react";
import type { TelemetryData } from "../hooks/useRecon";

interface SponsorTelemetryProps {
  telemetry: Record<string, TelemetryData>;
  isLoading?: boolean;
  jobComplete?: boolean;
}

interface AnimatedValue {
  current: number;
  target: number;
}

const SPONSOR_INFO: Record<string, { name: string; icon: string; color: string; url: string }> = {
  oxylabs: { name: "Oxylabs", icon: "🌐", color: "#3b82f6", url: "https://oxylabs.io" },
  kimi: { name: "Kimi AI", icon: "🧠", color: "#8b5cf6", url: "https://kimi.moonshot.cn" },
  daytona: { name: "Daytona", icon: "⚡", color: "#f97316", url: "https://daytona.io" },
};

const EXTENDED_METRICS: Record<string, Array<{ label: string; key: string }>> = {
  daytona: [
    { label: "Sandboxes", key: "sandbox_count" },
    { label: "Avg Spin-up", key: "avg_spin_up_ms" },
    { label: "Runtime", key: "cumulative_runtime_s" },
  ],
  oxylabs: [
    { label: "Web Scrapes", key: "web_scrape_count" },
    { label: "SERP Queries", key: "serp_count" },
    { label: "Data Volume", key: "data_volume_kb" },
  ],
  kimi: [
    { label: "Tokens In", key: "tokens_in" },
    { label: "Tokens Out", key: "tokens_out" },
    { label: "Est. Cost", key: "estimated_cost_usd" },
  ],
};

function useCountUp(target: number, duration = 400): number {
  const [value, setValue] = useState(0);
  const prevTarget = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const start = prevTarget.current;
    const diff = target - start;
    if (diff === 0) return;
    const startTime = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(start + diff * eased));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    rafRef.current = requestAnimationFrame(animate);
    prevTarget.current = target;

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration]);

  return value;
}

function RelativeTime({ timestamp: _timestamp }: { timestamp: string | null }) {
  const [label, setLabel] = useState("");

  useEffect(() => {
    if (!_timestamp) { setLabel(""); return; }

    const update = () => {
      const diff = Date.now() - new Date(_timestamp).getTime();
      const secs = Math.floor(diff / 1000);
      if (secs < 5) setLabel("just now");
      else if (secs < 60) setLabel(`${secs}s ago`);
      else if (secs < 3600) setLabel(`${Math.floor(secs / 60)}m ago`);
      else setLabel(`${Math.floor(secs / 3600)}h ago`);
    };

    update();
    const interval = setInterval(update, 5000);
    return () => clearInterval(interval);
  }, [_timestamp]);

  return <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>{label}</span>;
}

function ServiceStatusDot({ data }: { data: TelemetryData | undefined }) {
  if (!data || data.calls === 0) {
    return <span style={{ ...styles.statusDot, background: "#6b7280" }} title="Inactive" />;
  }

  const successRate = data.calls > 0 ? data.successes / data.calls : 0;
  const statusColor = successRate >= 0.9 ? "#22c55e" : successRate >= 0.5 ? "#fbbf24" : "#ef4444";
  const statusLabel = successRate >= 0.9 ? "Active" : successRate >= 0.5 ? "Rate Limited" : "Error";

  return (
    <span
      style={{
        ...styles.statusDot,
        background: statusColor,
        boxShadow: `0 0 6px ${statusColor}`,
      }}
      title={statusLabel}
    />
  );
}

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
          const animatedCalls = useCountUp(data?.calls ?? 0);
          const animatedSuccessRate = useCountUp(
            data && data.calls > 0 ? Math.round((data.successes / data.calls) * 100) : 0
          );
          const animatedLatency = useCountUp(
            data && data.calls > 0 ? Math.round(data.total_duration_ms / data.calls) : 0
          );
          const metrics = EXTENDED_METRICS[key] ?? [];
          const lastTimestamp = null; // Would need backend to provide this

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
                <ServiceStatusDot data={data} />
              </div>
              {active ? (
                <div style={styles.cardBody}>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Calls</span>
                    <span style={styles.statValue}>{animatedCalls}</span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Success Rate</span>
                    <span style={styles.statValue}>{animatedSuccessRate}%</span>
                  </div>
                  <div style={styles.statRow}>
                    <span style={styles.statLabel}>Avg Latency</span>
                    <span style={styles.statValue}>{animatedLatency}ms</span>
                  </div>
                  {metrics.length > 0 && (
                    <div style={styles.extendedMetrics}>
                      {metrics.map((m) => {
                        const metricVal = data?.metrics?.[m.key];
                        if (metricVal === undefined) return null;
                        return (
                          <div key={m.key} style={styles.statRow}>
                            <span style={styles.statLabel}>{m.label}</span>
                            <span style={styles.statValue}>
                              {typeof metricVal === "number" && metricVal > 1000
                                ? metricVal.toLocaleString()
                                : metricVal}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  <RelativeTime timestamp={lastTimestamp} />
                  {data.calls > 0 && (
                    <div style={styles.progressTrack}>
                      <div
                        style={{
                          ...styles.progressBar,
                          width: `${Math.min(100, animatedSuccessRate)}%`,
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
      <div style={styles.footer}>
        <div style={styles.footerDivider} />
        <div style={styles.footerContent}>
          Powered by{" "}
          {Object.entries(SPONSOR_INFO).map(([key, info], i) => (
            <span key={key}>
              <a
                href={info.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ ...styles.footerLink, color: info.color }}
              >
                {info.icon} {info.name}
              </a>
              {i < Object.keys(SPONSOR_INFO).length - 1 && (
                <span style={styles.footerSep}> · </span>
              )}
            </span>
          ))}
        </div>
      </div>
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
    gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
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
    flex: 1,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    flexShrink: 0,
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
  extendedMetrics: {
    borderTop: "1px solid rgba(255,255,255,0.06)",
    marginTop: 4,
    paddingTop: 4,
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
    borderTop: "1px solid rgba(255,255,255,0.06)",
  },
  footerDivider: {
    height: 1,
    background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)",
    animation: "progressSlide 2s ease-in-out infinite",
  },
  footerContent: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    padding: "10px 14px",
    fontSize: 11,
    color: "rgba(255,255,255,0.4)",
    flexWrap: "wrap",
  },
  footerLink: {
    textDecoration: "none",
    fontWeight: 500,
  },
  footerSep: {
    color: "rgba(255,255,255,0.2)",
  },
};
