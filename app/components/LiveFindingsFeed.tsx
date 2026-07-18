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

export default function LiveFindingsFeed({ findings }: LiveFindingsFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
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
          return (
            <div
              key={i}
              style={{
                ...styles.entry,
                borderLeft: `3px solid ${color}`,
                cursor: "pointer",
              }}
              onClick={() => toggleExpand(i)}
            >
              <div style={styles.entryIcon}>{meta.icon}</div>
              <div style={styles.entryBody}>
                <div style={styles.entryHeader}>
                  <span style={{ ...styles.entryAgent, color }}>{finding.agentName}</span>
                  <span style={styles.entryTime}>
                    {new Date(finding.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div style={styles.entryDescription}>{finding.description}</div>
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
  entryTime: {
    fontSize: 11,
    color: "rgba(255,255,255,0.3)",
  },
  entryDescription: {
    fontSize: 13,
    color: "rgba(255,255,255,0.8)",
    lineHeight: 1.4,
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
