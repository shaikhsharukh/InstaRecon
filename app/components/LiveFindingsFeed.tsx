"use client";

import { useEffect, useRef, useState } from "react";
import { getAgentMeta } from "./SwarmStatusPanel";

export interface FindingData {
  agentId: string;
  agentName: string;
  timestamp: string;
  description: string;
}

interface LiveFindingsFeedProps {
  findings: FindingData[];
}

const AGENT_COLORS: Record<string, string> = {
  product_analyzer: "#3B82F6",
  competitor_finder: "#EF4444",
  tech_stack: "#8B5CF6",
  social_auditor: "#10B981",
  seo_scanner: "#F97316",
};

const NEW_BADGE_DURATION = 3000;

function RelativeTime({ timestamp }: { timestamp: string }) {
  const [label, setLabel] = useState("");

  useEffect(() => {
    const update = () => {
      const diff = Date.now() - new Date(timestamp).getTime();
      const secs = Math.floor(diff / 1000);
      if (secs < 5) setLabel("just now");
      else if (secs < 60) setLabel(`${secs}s ago`);
      else if (secs < 3600) setLabel(`${Math.floor(secs / 60)}m ago`);
      else setLabel(`${Math.floor(secs / 3600)}h ago`);
    };

    update();
    const interval = setInterval(update, 5000);
    return () => clearInterval(interval);
  }, [timestamp]);

  return <span style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", flexShrink: 0 }}>{label}</span>;
}

function TypingText({ text, startedAt }: { text: string; startedAt: number }) {
  const [displayed, setDisplayed] = useState("");
  const idxRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    idxRef.current = 0;
    setDisplayed("");

    const charsPerTick = 3;
    const tick = () => {
      const next = idxRef.current + charsPerTick;
      if (idxRef.current < text.length) {
        setDisplayed(text.slice(0, next));
        idxRef.current = next;
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [text, startedAt]);

  return <>{displayed}</>;
}

export default function LiveFindingsFeed({ findings }: LiveFindingsFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [visibleBadges, setVisibleBadges] = useState<Set<number>>(new Set());

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [findings.length]);

  useEffect(() => {
    if (findings.length === 0) return;
    const idx = findings.length - 1;
    setVisibleBadges((prev) => new Set(prev).add(idx));
    const timer = setTimeout(() => {
      setVisibleBadges((prev) => {
        const next = new Set(prev);
        next.delete(idx);
        return next;
      });
    }, NEW_BADGE_DURATION);
    return () => clearTimeout(timer);
  }, [findings.length]);

  const toggleExpand = (i: number) => {
    setExpandedIndex(expandedIndex === i ? null : i);
  };

  if (findings.length === 0) {
    return (
      <div style={styles.container}>
        <h3 style={styles.heading}>Live Findings</h3>
        <div style={styles.empty}>
          <div style={styles.emptyIcon}>📡</div>
          <div style={styles.emptyText}>
            Submit a URL to see findings appear here in real-time.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.heading}>Live Findings ({findings.length})</h3>
      <div style={styles.feed}>
        {findings.map((finding, i) => {
          const color = AGENT_COLORS[finding.agentId] || "#818cf8";
          const meta = getAgentMeta(finding.agentId);
          const isExpanded = expandedIndex === i;
          const isNew = visibleBadges.has(i);
          const entryStart = i === findings.length - 1 ? Date.now() : 0;

          return (
            <div
              key={i}
              style={{
                ...styles.entry,
                borderLeft: `3px solid ${color}`,
                cursor: "pointer",
                animation: isNew ? "fadeIn 0.2s ease" : "none",
              }}
              onClick={() => toggleExpand(i)}
            >
              <span style={styles.entryIcon}>{meta.icon}</span>
              <div style={styles.entryBody}>
                <div style={styles.entryHeader}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ ...styles.entryAgent, color }}>{finding.agentName}</span>
                    {isNew && (
                      <span style={styles.newBadge}>New</span>
                    )}
                  </div>
                  <RelativeTime timestamp={finding.timestamp} />
                </div>
                <div style={styles.entryDescription}>
                  {entryStart > 0 ? (
                    <TypingText text={finding.description} startedAt={entryStart} />
                  ) : (
                    finding.description
                  )}
                </div>
                {isExpanded && (
                  <div style={styles.expandedDetail}>
                    <div style={styles.detailRow}>
                      <span style={styles.detailLabel}>Agent:</span>
                      <span style={styles.detailValue}>{finding.agentName}</span>
                    </div>
                    <div style={styles.detailRow}>
                      <span style={styles.detailLabel}>Time:</span>
                      <span style={styles.detailValue}>
                        {new Date(finding.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div style={styles.detailRow}>
                      <span style={styles.detailLabel}>Description:</span>
                      <span style={styles.detailValue}>{finding.description}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: "rgba(255,255,255,0.03)",
    borderRadius: 16,
    padding: 20,
    border: "1px solid rgba(255,255,255,0.06)",
  },
  heading: {
    fontSize: 14,
    fontWeight: 600,
    color: "rgba(255,255,255,0.6)",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    marginBottom: 16,
    margin: 0,
    paddingBottom: 12,
    borderBottom: "1px solid rgba(255,255,255,0.06)",
  },
  feed: {
    maxHeight: 400,
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  entry: {
    display: "flex",
    gap: 10,
    padding: "8px 0 8px 10px",
    borderBottom: "1px solid rgba(255,255,255,0.03)",
    transition: "background 0.2s ease",
  },
  entryIcon: {
    fontSize: 16,
    flexShrink: 0,
    marginTop: 2,
  },
  entryBody: {
    flex: 1,
  },
  entryHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 2,
  },
  entryAgent: {
    fontSize: 12,
    fontWeight: 600,
  },
  entryDescription: {
    fontSize: 13,
    color: "rgba(255,255,255,0.8)",
    lineHeight: 1.4,
  },
  newBadge: {
    fontSize: 9,
    fontWeight: 700,
    color: "#22c55e",
    padding: "1px 5px",
    borderRadius: 4,
    background: "rgba(34,197,94,0.15)",
    animation: "newBadgePulse 1s ease-in-out 2",
  },
  expandedDetail: {
    marginTop: 8,
    padding: 8,
    borderRadius: 8,
    background: "rgba(255,255,255,0.05)",
  },
  detailRow: {
    display: "flex",
    gap: 6,
    marginBottom: 4,
    fontSize: 12,
  },
  detailLabel: {
    color: "rgba(255,255,255,0.4)",
    fontWeight: 600,
    minWidth: 80,
  },
  detailValue: {
    color: "rgba(255,255,255,0.8)",
  },
  empty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    padding: "40px 20px",
    textAlign: "center",
  },
  emptyIcon: {
    fontSize: 28,
  },
  emptyText: {
    fontSize: 14,
    color: "rgba(255,255,255,0.3)",
  },
};
