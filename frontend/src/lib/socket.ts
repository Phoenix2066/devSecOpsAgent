import { io } from "socket.io-client";

const SOCKET_URL = import.meta.env.VITE_WS_URL || "http://localhost:8080";

export const socket = io(SOCKET_URL, {
  autoConnect: false,
});

export type WSEventType =
  | "agent_spawned"
  | "agent_complete"
  | "agent_failed"
  | "pipeline_failed"
  | "memory_hit"
  | "memory_miss"
  | "repair_started"
  | "repair_iteration"
  | "web_search_started"
  | "web_search_complete"
  | "validation_passed"
  | "validation_failed"
  | "deployment_promoted"
  | "rollback_triggered";

export interface WSMessage {
  event: WSEventType;
  pipeline_id: string;
  timestamp: string;
  data: any;
}
