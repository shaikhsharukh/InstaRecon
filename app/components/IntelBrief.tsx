"use client";

import type { IntelBriefData } from "../hooks/useRecon";

interface IntelBriefProps {
  data: IntelBriefData;
  onExportPdf: () => void;
  onEmailReport: () => void;
  onRunCompetitor: () => void;
}

export default function IntelBrief({ data, onExportPdf, onEmailReport, onRunCompetitor }: IntelBriefProps) {
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerTop}>
          <span style={styles.headerIcon}>📋</span>
          <h2 style={styles.title}>INTEL BRIEF: {data.companyName || "Company Analysis"}</h2>
        </div>
        <div style={styles.meta}>
          Generated in {data.durationSeconds}s &middot; {data.agentsCompleted}/{data.totalAgents} agents completed
          &middot; {data.cached ? "⚡ Cached: Yes" : "⚡ Cached: No"}
          &middot; Sponsor calls: {data.sponsorCalls}
        </div>
      </div>

      <KeyInsightCallout insight={data.keyInsight} />

      <div style={styles.grid}>
        {data.agentSummaries.map((agent, i) => (
          <AgentSummaryCard key={agent.agentId} agent={agent} index={i} />
        ))}
      </div>

      {data.risks.length > 0 && (
        <RiskOpportunitySection title="Risks" items={data.risks} color="#f87171" />
      )}

      {data.opportunities.length > 0 && (
        <RiskOpportunitySection title="Opportunities" items={data.opportunities} color="#34d399" />
      )}

      <IntelBriefActionBar
        onExportPdf={onExportPdf}
        onEmailReport={onEmailReport}
        onRunCompetitor={onRunCompetitor}
      />
    </div>
  );
}

function KeyInsightCallout({ insight }: { insight: { text: string; supportingAgents: string[] } }) {
  return (
    <div style={styles.insightCard}>
      <div style={styles.insightIcon}>🔑</div>
      <div style={styles.insightBody}>
        <div style={styles.insightLabel}>KEY INSIGHT</div>
        <div style={styles.insightText}>{insight.text}</div>
        {insight.supportingAgents.length > 0 && (
          <div style={styles.citationRow}>
            {insight.supportingAgents.map((agent) => (
              <span key={agent} style={styles.citationBadge}>
                {agent}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AgentSummaryCard({ agent, index }: { agent: IntelBriefData["agentSummaries"][0]; index: number }) {
  const qualityColor =
    agent.dataQuality === "good" ? "#34d399" :
    agent.dataQuality === "warning" ? "#fbbf24" : "#f87171";

  return (
    <div
      style={{
        ...styles.agentCard,
        animation: `fadeInUp 0.3s ease ${index * 0.1}s both`,
      }}
    >
      <div style={styles.agentHeader}>
        <span style={styles.agentIcon}>{agent.icon || "🤖"}</span>
        <span style={{ ...styles.agentName, color: agent.color || "#e2e8f0" }}>
          {agent.agentName}
        </span>
        <span
          style={{
            ...styles.qualityDot,
            background: qualityColor,
            boxShadow: `0 0 6px ${qualityColor}`,
          }}
        />
      </div>
      <div style={styles.agentFinding}>{agent.keyFinding}</div>
    </div>
  );
}

function RiskOpportunitySection({
  title,
  items,
  color,
}: {
  title: string;
  items: Array<{ text: string; supportingAgents: string[] }>;
  color: string;
}) {
  return (
    <div style={styles.section}>
      <h3 style={{ ...styles.sectionTitle, color }}>{title}</h3>
      {items.map((item, i) => (
        <div key={i} style={styles.sectionItem}>
          <div style={styles.itemBullet}>&bull;</div>
          <div style={styles.itemContent}>
            <div style={styles.itemText}>{item.text}</div>
            <div style={styles.itemAgents}>
              {item.supportingAgents.map((a) => (
                <span key={a} style={styles.agentTag}>{a}</span>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function IntelBriefActionBar({
  onExportPdf,
  onEmailReport,
  onRunCompetitor,
}: {
  onExportPdf: () => void;
  onEmailReport: () => void;
  onRunCompetitor: () => void;
}) {
  return (
    <div style={styles.actionBar}>
      <button onClick={onExportPdf} style={styles.actionButton}>
        📄 Download PDF
      </button>
      <button onClick={onEmailReport} style={styles.actionButton}>
        📧 Email Report
      </button>
      <button onClick={onRunCompetitor} style={styles.actionButton}>
        🔄 Run on Competitor
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  header: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    padding: "16px 20px",
    borderRadius: 16,
    background: "rgba(255, 255, 255, 0.05)",
    backdropFilter: "blur(12px)",
    border: "1px solid rgba(255, 255, 255, 0.1)",
  },
  headerTop: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  headerIcon: {
    fontSize: 24,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    color: "#e2e8f0",
    margin: 0,
  },
  meta: {
    fontSize: 12,
    color: "rgba(255,255,255,0.45)",
    letterSpacing: "0.3px",
  },
  insightCard: {
    display: "flex",
    gap: 14,
    padding: "18px 20px",
    borderRadius: 16,
    background: "rgba(99, 102, 241, 0.1)",
    border: "1px solid rgba(99, 102, 241, 0.3)",
    boxShadow: "0 0 30px rgba(99, 102, 241, 0.15)",
    animation: "fadeIn 0.4s ease 0.5s both",
  },
  insightIcon: {
    fontSize: 28,
    flexShrink: 0,
    marginTop: 2,
  },
  insightBody: {
    flex: 1,
  },
  insightLabel: {
    fontSize: 11,
    fontWeight: 700,
    color: "#a78bfa",
    textTransform: "uppercase",
    letterSpacing: "1px",
    marginBottom: 6,
  },
  insightText: {
    fontSize: 15,
    fontWeight: 500,
    color: "#e2e8f0",
    lineHeight: 1.5,
    marginBottom: 10,
  },
  citationRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
  },
  citationBadge: {
    fontSize: 11,
    padding: "3px 8px",
    borderRadius: 6,
    background: "rgba(99, 102, 241, 0.2)",
    color: "#a78bfa",
    fontWeight: 500,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
    gap: 12,
  },
  agentCard: {
    padding: 12,
    borderRadius: 12,
    background: "rgba(255, 255, 255, 0.04)",
    backdropFilter: "blur(8px)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    opacity: 0,
  },
  agentHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  agentIcon: {
    fontSize: 16,
  },
  agentName: {
    fontSize: 12,
    fontWeight: 600,
    flex: 1,
  },
  qualityDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    flexShrink: 0,
  },
  agentFinding: {
    fontSize: 13,
    color: "rgba(255,255,255,0.75)",
    lineHeight: 1.4,
  },
  section: {
    padding: "14px 18px",
    borderRadius: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    margin: "0 0 10px",
  },
  sectionItem: {
    display: "flex",
    gap: 8,
    padding: "8px 0",
    borderBottom: "1px solid rgba(255,255,255,0.04)",
  },
  itemBullet: {
    fontSize: 16,
    color: "rgba(255,255,255,0.3)",
    flexShrink: 0,
    marginTop: -1,
  },
  itemContent: {
    flex: 1,
  },
  itemText: {
    fontSize: 13,
    color: "rgba(255,255,255,0.8)",
    marginBottom: 4,
    lineHeight: 1.4,
  },
  itemAgents: {
    display: "flex",
    gap: 4,
    flexWrap: "wrap",
  },
  agentTag: {
    fontSize: 10,
    padding: "2px 6px",
    borderRadius: 4,
    background: "rgba(255,255,255,0.06)",
    color: "rgba(255,255,255,0.4)",
  },
  actionBar: {
    display: "flex",
    gap: 12,
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
    transition: "all 0.2s ease",
  },
};
