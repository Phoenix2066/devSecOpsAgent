import { useState, useEffect } from "react";
import type { Node, Edge } from "reactflow";
import { fetchPipelineAgents } from "@/lib/api";
import { socket, type WSMessage } from "@/lib/socket";
import type { AgentNodeData } from "@/lib/mock-data";

const POS: Record<string, { x: number; y: number }> = {
  orchestrator:    { x: 380, y: 0 },
  log_analyzer:     { x: 0,   y: 160 },
  dependency_inspector:     { x: 230, y: 160 },
  memory:     { x: 460, y: 160 },
  config_analyzer:     { x: 690, y: 160 },
  web_search:     { x: 460, y: 320 },
  coordinator:   { x: 380, y: 480 },
  repair_imports: { x: 230, y: 640 },
  repair_yaml: { x: 530, y: 640 },
};

export function useAgentGraph(pipelineId: string) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const agents = await fetchPipelineAgents(pipelineId);
        const initialNodes = agents.map((a: any) => ({
          id: a.id,
          type: "agent",
          position: POS[a.agent_type] ?? { x: 0, y: 0 },
          data: {
            id: a.id,
            type: a.agent_type,
            label: a.agent_type.replace("_", " "),
            status: a.status,
            detail: a.result?.findings?.details || ""
          } as AgentNodeData,
        }));
        setNodes(initialNodes);
        
        // Build initial edges based on some logic or fixed structure for now
        // In a real app, edges might come from the backend or be derived from 'spawned_by'
      } catch (err) {
        console.error("Failed to load agents", err);
      }
    }

    load();

    function onMessage(msg: WSMessage) {
      if (msg.pipeline_id !== pipelineId) return;

      if (msg.event === "agent_spawned") {
        const newAgent = msg.data;
        setNodes((prev) => [
          ...prev,
          {
            id: newAgent.agent_id,
            type: "agent",
            position: POS[newAgent.agent_type] ?? { x: Math.random() * 500, y: Math.random() * 500 },
            data: {
              id: newAgent.agent_id,
              type: newAgent.agent_type,
              label: newAgent.agent_type.replace("_", " "),
              status: "spawned",
              detail: ""
            } as AgentNodeData,
          },
        ]);
        
        if (newAgent.spawned_by) {
            setEdges(prev => [
                ...prev,
                {
                    id: `e-${newAgent.spawned_by}-${newAgent.agent_id}`,
                    source: newAgent.spawned_by,
                    target: newAgent.agent_id,
                    animated: true,
                    type: "smoothstep"
                }
            ]);
        }
      } else if (msg.event === "agent_complete" || msg.event === "agent_failed") {
        setNodes((prev) =>
          prev.map((n) =>
            n.id === msg.data.agent_id
              ? { ...n, data: { ...n.data, status: msg.event === "agent_complete" ? "complete" : "failed" } }
              : n
          )
        );
      }
    }

    socket.on("message", onMessage);
    return () => {
      socket.off("message", onMessage);
    };
  }, [pipelineId]);

  return { nodes, edges };
}
