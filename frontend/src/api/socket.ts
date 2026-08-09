import type { TaskEvent } from "./types";

export const reconnectDelay = (attempt: number) => Math.min(10_000, 500 * 2 ** attempt);

export class TaskSocket {
  private socket: WebSocket | null = null;
  private attempt = 0;
  constructor(private readonly threadId: string, private readonly onEvent: (event: TaskEvent) => void) {}

  connect() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    this.socket = new WebSocket(`${scheme}://${location.host}/ws/${encodeURIComponent(this.threadId)}`);
    this.socket.onopen = () => { this.attempt = 0; };
    this.socket.onmessage = ({ data }) => {
      try {
        const event = JSON.parse(data) as TaskEvent;
        if (event.version === 1) this.onEvent(event);
      } catch { /* Ignore non-event ping/pong messages. */ }
    };
  }

  close() { this.socket?.close(); this.socket = null; }
}
