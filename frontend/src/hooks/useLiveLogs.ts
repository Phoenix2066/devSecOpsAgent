import { useState, useEffect } from "react";
import { usePipelineSocket } from "@/lib/socket";
import type { LogLine, WSEventType } from "@/lib/types";

export function useLiveLogs(pipelineId: string) {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const socket = usePipelineSocket(pipelineId);

  useEffect(() => {
    if (!pipelineId) return;

    const handleEvent = (event: WSEventType, data: any) => {
      let level: LogLine["level"] = "info";
      let message = "";
      let agent_type = "system";

      switch (event) {
        case "agent_spawned":
          message = `Spawned agent of type [${data.agent_type}] to investigate issue. Pipeline ID: ${data.pipeline_id}`;
          agent_type = "orchestrator";
          break;
        case "agent_complete":
          message = `[${data.agent_type}] has completed its task successfully. Result: ${JSON.stringify(data.result || "OK")}`;
          agent_type = data.agent_type;
          level = "success";
          break;
        case "agent_failed":
          message = `[${data.agent_type}] encountered a critical failure! Error: ${data.error || "Unknown error"}`;
          agent_type = data.agent_type;
          level = "error";
          break;
        case "repair_iteration":
          message = `Started repair iteration #${data.iteration}. Current status is: ${data.status}`;
          agent_type = "feedback_loop";
          level = data.status === "success" ? "success" : "warn";
          break;
        case "memory_hit":
          message = `Memory hit! Found similar past incident: ${data.incident_id}. Match confidence: ${(data.similarity_score * 100).toFixed(1)}%`;
          agent_type = "memory";
          level = "memory";
          break;
        case "memory_miss":
          message = `Memory miss. No similar past incidents found for signature: ${data.error_signature}`;
          agent_type = "memory";
          level = "warn";
          break;
        case "web_search_started":
          message = `Initiating web search to find solutions for: ${data.error_signature}`;
          agent_type = "web_search";
          level = "search";
          break;
        case "web_search_complete":
          message = `Web search complete. Successfully analyzed ${data.sources?.length || 0} external sources for potential fixes.`;
          agent_type = "web_search";
          level = "success";
          break;
        case "validation_passed":
          message = `Shadow environment validation PASSED on iteration ${data.iteration}. Fix confidence metric: ${data.confidence}`;
          agent_type = "validator";
          level = "success";
          break;
        case "validation_failed":
          message = `Shadow environment validation FAILED on iteration ${data.iteration}. Reason: ${data.reason}`;
          agent_type = "validator";
          level = "error";
          break;
        case "deployment_promoted":
          message = `Fix verified and PROMOTED to production. PR created successfully at: ${data.pr_url || "unknown"}`;
          agent_type = "orchestrator";
          level = "success";
          break;
        case "rollback_triggered":
          message = `ROLLBACK triggered! Returning to safe state due to: ${data.reason}`;
          agent_type = "orchestrator";
          level = "error";
          break;
        default:
          return;
      }

      setLogs((prev) => [
        ...prev,
        {
          id: Math.random().toString(36).substr(2, 9),
          level,
          msg: message,
          ts: new Date().toLocaleTimeString([], { hour12: false }),
          agent: agent_type
        },
      ]);
    };

    const events: WSEventType[] = [
      "agent_spawned", "agent_complete", "agent_failed",
      "repair_iteration", "memory_hit", "memory_miss",
      "web_search_started", "web_search_complete",
      "validation_passed", "validation_failed",
      "deployment_promoted", "rollback_triggered"
    ];

    events.forEach(e => socket.on(e, (data) => handleEvent(e, data)));

    return () => {
      events.forEach(e => socket.off(e, (data) => handleEvent(e, data)));
    };
  }, [pipelineId]);

  return { logs, clear: () => setLogs([]) };
}
