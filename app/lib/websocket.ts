export type WsEventType =
  | "agent_update"
  | "finding"
  | "job_complete"
  | "error"
  | "reconnecting"
  | "telemetry.update"
  | "synthesis.completed"
  | "email.sent"
  | "email.failed"
  | "pdf.generated";

export interface WebSocketEvent {
  type: WsEventType;
  payload: Record<string, unknown>;
}

export type EventHandler = (event: WebSocketEvent) => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private shouldReconnect = true;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(url: string) {
    this.url = url;
  }

  connect() {
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;
    this.doConnect();
  }

  private doConnect() {
    if (this.ws) {
      this.ws.close();
    }

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const parsed: WebSocketEvent = JSON.parse(event.data);
        this.dispatch(parsed.type, parsed);
      } catch {
        console.error("Failed to parse WebSocket message:", event.data);
      }
    };

    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      console.error("WebSocket error");
    };
  }

  private scheduleReconnect() {
    const delay = Math.min(
      1000 * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.dispatch("reconnecting", {
        type: "reconnecting",
        payload: { attempt: this.reconnectAttempts, delay },
      });
      this.doConnect();
    }, delay);
  }

  on(eventType: string, handler: EventHandler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);
  }

  off(eventType: string, handler: EventHandler) {
    this.handlers.get(eventType)?.delete(handler);
  }

  private dispatch(eventType: string, event: WebSocketEvent) {
    this.handlers.get(eventType)?.forEach((handler) => handler(event));
    this.handlers.get("*")?.forEach((handler) => handler(event));
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
