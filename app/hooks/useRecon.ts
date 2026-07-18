"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { WebSocketManager, type WebSocketEvent } from "../lib/websocket";

export interface AgentStatus {
  agentId: string;
  agentName: string;
  status: "idle" | "pending" | "running" | "done" | "error";
  error?: string;
}

export interface Finding {
  agentId: string;
  agentName: string;
  timestamp: string;
  description: string;
}

export interface TelemetryData {
  service_name: string;
  calls: number;
  successes: number;
  failures: number;
  total_duration_ms: number;
  metrics: Record<string, number>;
}

export interface UseReconState {
  status: "idle" | "running" | "complete" | "error";
  jobId: string | null;
  agents: AgentStatus[];
  findings: Finding[];
  error: string | null;
  reconnecting: boolean;
  reconnectAttempt: number;
  overallProgress: number;
  telemetry: Record<string, TelemetryData>;
  cached: boolean;
  cachedAt: string | null;
}

const ALL_AGENTS: AgentStatus[] = [
  { agentId: "product_analyzer", agentName: "Product Analyzer", status: "idle" },
  { agentId: "competitor_finder", agentName: "Competitor Finder", status: "idle" },
  { agentId: "tech_stack", agentName: "Tech Stack Detective", status: "idle" },
  { agentId: "social_auditor", agentName: "Social Auditor", status: "idle" },
  { agentId: "seo_scanner", agentName: "SEO Scanner", status: "idle" },
  { agentId: "sentiment_analyzer", agentName: "Sentiment Analyzer", status: "idle" },
  { agentId: "hiring_agent", agentName: "Hiring Signal Detector", status: "idle" },
];

const INITIAL_STATE: UseReconState = {
  status: "idle",
  jobId: null,
  agents: ALL_AGENTS,
  findings: [],
  error: null,
  reconnecting: false,
  reconnectAttempt: 0,
  overallProgress: 0,
  telemetry: {},
  cached: false,
  cachedAt: null,
};

export function useRecon() {
  const [state, setState] = useState<UseReconState>(INITIAL_STATE);
  const wsRef = useRef<WebSocketManager | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const baseUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const startRecon = useCallback(
    async (url: string) => {
      setState((prev) => ({
        ...prev,
        status: "running",
        findings: [],
        agents: prev.agents.map((a) => ({ ...a, status: "idle" })),
        overallProgress: 0,
        telemetry: {},
        cached: false,
        cachedAt: null,
      }));

      try {
        const res = await fetch(`${baseUrl}/api/recon`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to start investigation");
        }

        const data = await res.json();
        const jobId = data.job_id;

        setState((prev) => ({ ...prev, jobId }));

        const wsUrl = baseUrl.replace(/^http/, "ws");
        const ws = new WebSocketManager(`${wsUrl}/ws/${jobId}`);
        wsRef.current = ws;

        ws.on("*", (event: WebSocketEvent) => {
          if (event.type === "reconnecting") {
            setState((prev) => ({
              ...prev,
              reconnecting: true,
              reconnectAttempt: (event.payload as { attempt: number }).attempt,
            }));
            return;
          }
          handleWsEvent(event, jobId);
        });

        ws.on("agent_update", () => {
          setState((prev) => (prev.reconnecting ? { ...prev, reconnecting: false } : prev));
        });

        ws.connect();
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "An unknown error occurred";
        setState((prev) => ({
          ...prev,
          status: "error",
          error: message,
        }));
      }
    },
    [baseUrl]
  );

  const computeProgress = (agents: AgentStatus[]): number => {
    if (agents.length === 0) return 0;
    const done = agents.filter(
      (a) => a.status === "done" || a.status === "error"
    ).length;
    return Math.round((done / agents.length) * 100);
  };

  const handleWsEvent = (event: WebSocketEvent, jobId: string) => {
    switch (event.type) {
      case "agent_update": {
        const payload = event.payload as {
          agent_id: string;
          agent_name: string;
          status: string;
          error?: string;
        };
        setState((prev) => {
          const updatedAgents = prev.agents.map((a) =>
            a.agentId === payload.agent_id
              ? {
                  ...a,
                  status: payload.status as AgentStatus["status"],
                  error: payload.error,
                }
              : a
          );
          return {
            ...prev,
            agents: updatedAgents,
            overallProgress: computeProgress(updatedAgents),
          };
        });
        break;
      }
      case "finding": {
        const payload = event.payload as {
          agent_id: string;
          agent_name: string;
          timestamp: string;
          description: string;
        };
        setState((prev) => ({
          ...prev,
          findings: [
            ...prev.findings,
            {
              agentId: payload.agent_id,
              agentName: payload.agent_name,
              timestamp: payload.timestamp,
              description: payload.description,
            },
          ],
        }));
        break;
      }
      case "job_complete": {
        const payload = event.payload as {
          status: string;
        };
        setState((prev) => ({
          ...prev,
          status:
            payload.status === "complete" ? "complete" : "error",
          overallProgress: 100,
        }));
        break;
      }
      case "telemetry.update": {
        const payload = event.payload as {
          job_id: string;
          service: string;
          data: TelemetryData;
        };
        setState((prev) => ({
          ...prev,
          telemetry: {
            ...prev.telemetry,
            [payload.service]: payload.data,
          },
        }));
        break;
      }
      case "error": {
        const payload = event.payload as { message: string };
        setState((prev) => ({
          ...prev,
          status: "error",
          error: payload.message,
        }));
        break;
      }
    }
  };

  const sendEmail = useCallback(async (email: string) => {
    if (!state.jobId) return;
    try {
      const res = await fetch(`${baseUrl}/api/investigations/${state.jobId}/email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      return await res.json();
    } catch (err) {
      return { status: "failed", error: String(err) };
    }
  }, [baseUrl, state.jobId]);

  const downloadPdf = useCallback(async () => {
    if (!state.jobId) return;
    try {
      const res = await fetch(`${baseUrl}/api/investigations/${state.jobId}/brief`);
      if (!res.ok) throw new Error("Failed to generate PDF");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `intel-brief-${state.jobId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download failed:", err);
    }
  }, [baseUrl, state.jobId]);

  useEffect(() => {
    return () => {
      wsRef.current?.disconnect();
    };
  }, []);

  const reset = useCallback(() => {
    wsRef.current?.disconnect();
    wsRef.current = null;
    setState(INITIAL_STATE);
  }, []);

  return { ...state, startRecon, sendEmail, downloadPdf, reset };
}
