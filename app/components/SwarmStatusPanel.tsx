"use client";

import AgentCard from "./AgentCard";

export interface AgentMeta {
  agentId: string;
  agentName: string;
  icon: string;
  color: string;
}

export interface AgentState {
  agentId: string;
  agentName: string;
  status: "idle" | "pending" | "running" | "done" | "error";
  icon?: string;
  color?: string;
  error?: string;
}

interface SwarmStatusPanelProps {
  agents: AgentState[];
}

const AGENT_METADATA: Record<string, AgentMeta> = {
  product_analyzer: {
    agentId: "product_analyzer",
    agentName: "Product Analyzer",
    icon: "🏢",
    color: "#3B82F6",
  },
  competitor_finder: {
    agentId: "competitor_finder",
    agentName: "Competitor Finder",
    icon: "🏆",
    color: "#EF4444",
  },
  tech_stack: {
    agentId: "tech_stack",
    agentName: "Tech Stack Detective",
    icon: "⚙️",
    color: "#8B5CF6",
  },
  social_auditor: {
    agentId: "social_auditor",
    agentName: "Social Auditor",
    icon: "📱",
    color: "#10B981",
  },
  seo_scanner: {
    agentId: "seo_scanner",
    agentName: "SEO Scanner",
    icon: "🔍",
    color: "#F97316",
  },
  sentiment_analyzer: {
    agentId: "sentiment_analyzer",
    agentName: "Sentiment Analyzer",
    icon: "💬",
    color: "#f59e0b",
  },
  hiring_agent: {
    agentId: "hiring_agent",
    agentName: "Hiring Signal Detector",
    icon: "💼",
    color: "#8b5cf6",
  },
};

export function getAgentMeta(agentId: string): AgentMeta {
  return AGENT_METADATA[agentId] || {
    agentId,
    agentName: agentId,
    icon: "🤖",
    color: "#818cf8",
  };
}

export default function SwarmStatusPanel({ agents }: SwarmStatusPanelProps) {
  if (agents.length === 0) {
    return (
      <div style={styles.empty}>
        <div style={styles.emptyIcon}>🕵️</div>
        <div style={styles.emptyText}>No agents loaded</div>
      </div>
    );
  }

  return (
    <div style={styles.grid}>
      {agents.map((agent) => {
        const meta = getAgentMeta(agent.agentId);
        return (
          <AgentCard
            key={agent.agentId}
            name={agent.agentName}
            status={agent.status}
            icon={agent.icon || meta.icon}
            color={agent.color || meta.color}
            error={agent.error}
            progress={agent.status === "running" ? "indeterminate" : undefined}
          />
        );
      })}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
    gap: 12,
  },
  empty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    padding: 40,
    color: "rgba(255,255,255,0.3)",
  },
  emptyIcon: {
    fontSize: 32,
  },
  emptyText: {
    fontSize: 14,
  },
};
