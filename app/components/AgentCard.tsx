"use client";

interface AgentCardProps {
  name: string;
  status: "idle" | "pending" | "running" | "done" | "error";
  icon?: string;
  color?: string;
  error?: string;
  progress?: "determinate" | "indeterminate";
}

const STATUS_CONFIG: Record<string, { label: string; border: string; glow: string }> = {
  idle: {
    label: "Idle",
    border: "1px solid rgba(255,255,255,0.08)",
    glow: "0 0 8px rgba(99, 102, 241, 0.3)",
  },
  pending: {
    label: "Pending",
    border: "1px solid rgba(255,255,255,0.08)",
    glow: "none",
  },
  running: {
    label: "Running",
    border: "1px solid rgba(99, 102, 241, 0.5)",
    glow: "0 0 20px rgba(99, 102, 241, 0.15)",
  },
  done: {
    label: "Done",
    border: "1px solid rgba(34, 197, 94, 0.5)",
    glow: "0 0 20px rgba(34, 197, 94, 0.25)",
  },
  error: {
    label: "Error",
    border: "1px solid rgba(239, 68, 68, 0.5)",
    glow: "0 0 20px rgba(239, 68, 68, 0.15)",
  },
};

const STATUS_COLORS: Record<string, string> = {
  idle: "rgba(255,255,255,0.4)",
  pending: "rgba(255,255,255,0.4)",
  running: "#818cf8",
  done: "#34d399",
  error: "#f87171",
};

const ANIMATIONS: Record<string, string> = {
  idle: "glowPulse 2s ease-in-out infinite",
  pending: "none",
  running: "colorCycle 3s ease-in-out infinite",
  done: "scalePop 0.4s ease 2",
  error: "shake 0.3s ease 1",
};

export default function AgentCard({ name, status, icon, color, error, progress }: AgentCardProps) {
  const config = STATUS_CONFIG[status];
  const dotColor = color || STATUS_COLORS[status];
  const anim = ANIMATIONS[status];
  const assignedGlow = error ? `0 0 20px rgba(239, 68, 68, 0.25)` : config.glow;

  return (
    <div
      style={{
        ...styles.card,
        border: config.border,
        boxShadow: assignedGlow,
        animation: anim,
      }}
    >
      <div style={styles.iconRow}>
        {icon && <span style={styles.icon}>{icon}</span>}
        <span
          style={{
            ...styles.dot,
            background: dotColor,
            boxShadow: `0 0 8px ${dotColor}`,
          }}
        />
      </div>
      <div style={styles.info}>
        <div style={styles.name}>{name}</div>
        <div style={{ ...styles.statusLabel, color: dotColor }}>{config.label}</div>
        {progress === "indeterminate" && status === "running" && (
          <div style={styles.progressBar}>
            <div style={styles.progressFill} />
          </div>
        )}
      </div>
      {error && <div style={styles.errorTooltip}>{error}</div>}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: 14,
    borderRadius: 12,
    background: "rgba(255,255,255,0.04)",
    backdropFilter: "blur(12px)",
    position: "relative",
    transition: "all 0.3s ease",
  },
  iconRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  icon: {
    fontSize: 18,
    flexShrink: 0,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    flexShrink: 0,
  },
  info: {
    flex: 1,
  },
  name: {
    fontSize: 13,
    fontWeight: 600,
    color: "#e2e8f0",
    marginBottom: 2,
  },
  statusLabel: {
    fontSize: 11,
    fontWeight: 500,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  progressBar: {
    width: "100%",
    height: 3,
    background: "rgba(255,255,255,0.1)",
    borderRadius: 2,
    marginTop: 6,
    overflow: "hidden",
  },
  progressFill: {
    width: "40%",
    height: "100%",
    background: "linear-gradient(90deg, transparent, #818cf8, transparent)",
    borderRadius: 2,
    animation: "progressSlide 1.5s ease-in-out infinite",
  },
  errorTooltip: {
    position: "absolute",
    top: "100%",
    left: 0,
    right: 0,
    marginTop: 4,
    padding: "6px 10px",
    borderRadius: 6,
    background: "rgba(239,68,68,0.15)",
    color: "#fca5a5",
    fontSize: 11,
    zIndex: 10,
  },
};
