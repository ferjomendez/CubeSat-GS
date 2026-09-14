import type { WsMessage } from "./types";

export function connectWs(onMessage: (m: WsMessage) => void, onStatus: (connected: boolean) => void): { close(): void } {
  let ws: WebSocket | null = null;
  let closed = false;
  let delay = 1000;
  let ping: number | undefined;
  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;

  const open = () => {
    ws = new WebSocket(url);
    ws.onopen = () => {
      delay = 1000;
      onStatus(true);
      ping = window.setInterval(() => ws?.send(JSON.stringify({ type: "ping" })), 20000);
    };
    ws.onmessage = (ev) => {
      try {
        onMessage(JSON.parse(ev.data));
      } catch (e) {
        console.warn("ws: bad message", e);
      }
    };
    ws.onclose = () => {
      window.clearInterval(ping);
      onStatus(false);
      if (!closed) {
        setTimeout(open, delay);
        delay = Math.min(delay * 2, 10000);
      }
    };
    ws.onerror = () => ws?.close();
  };
  open();

  return {
    close() {
      closed = true;
      window.clearInterval(ping);
      ws?.close();
    },
  };
}
