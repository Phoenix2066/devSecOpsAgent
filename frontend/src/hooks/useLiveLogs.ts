import { useState, useEffect } from "react";
import { socket, type WSMessage } from "@/lib/socket";
import type { LogLine } from "@/lib/mock-data";

export function useLiveLogs(pipelineId: string) {
  const [logs, setLogs] = useState<LogLine[]>([]);

  useEffect(() => {
    // Initial logs might be fetched from API
    // For now we just handle live stream

    function onMessage(msg: WSMessage) {
      if (msg.pipeline_id !== pipelineId) return;

      // Map WS events to log lines
      let level: LogLine["level"] = "info";
      let agent = "system";
      let message = "";

      switch (msg.event) {
        case "agent_spawned":
          message = `Spawned ${msg.data.agent_type}`;
          agent = "orchestrator";
          break;
        case "agent_complete":
          message = `Completed ${msg.data.agent_type}`;
          agent = "orchestrator";
          level = "success";
          break;
        case "agent_failed":
          message = `Failed ${msg.data.agent_type}: ${msg.data.error || "Unknown error"}`;
          agent = "orchestrator";
          level = "error";
          break;
        case "repair_iteration":
          message = `Repair iteration ${msg.data.iteration}: ${msg.data.status}`;
          agent = "feedback_loop";
          break;
        case "memory_hit":
          message = `Memory hit: ${msg.data.incident_id} (sim: ${msg.data.similarity_score})`;
          agent = "memory";
          level = "success";
          break;
        default:
          return; // Ignore other events for logs for now
      }

      setLogs((prev) => [
        ...prev,
        {
          ts: new Date().toLocaleTimeString(),
          level,
          agent,
          msg: message,
        },
      ]);
    }

    socket.on("message", onMessage);
    return () => {
      socket.off("message", onMessage);
    };
  }, [pipelineId]);

  return { logs, clear: () => setLogs([]) };
}
