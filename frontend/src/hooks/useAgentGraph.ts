import { useState, useEffect } from "react";
import type { Node, Edge } from "reactflow";
import { getPipelineState } from "@/lib/api";
import { usePipelineSocket } from "@/lib/socket";
import type { AgentStatus, AgentType } from "@/lib/types";

// Keep positions for visualization
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

export interface AgentNodeData {
  id: string;
  type: string;
  label: string;
  status: string;
  detail: string;
}

export function useAgentGraph(pipelineId: string) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  const socket = usePipelineSocket(pipelineId);

  useEffect(() => {
    async function load() {
      if (!pipelineId) return;
      try {
        const state = await getPipelineState(pipelineId);
        if (state && state.graph) {
          const g = state.graph as any;
          const initialNodes: Node[] = Object.values(g.nodes || {}).map((n: any) => ({
            id: n.node_id,
            type: "agent",
            position: POS[n.node_type] ?? { x: Math.random() * 500, y: Math.random() * 500 },
            data: {
              id: n.node_id,
              type: n.node_type,
              label: n.node_type.replace("_", " "),
              status: n.status,
              detail: n.metadata?.detail || ""
            } as AgentNodeData,
          }));
          setNodes(initialNodes);

          const initialEdges: Edge[] = [];
          Object.values(g.nodes || {}).forEach((n: any) => {
            if (n.parent_id) {
              initialEdges.push({
                id: `e-${n.parent_id}-${n.node_id}`,
                source: n.parent_id,
                target: n.node_id,
                animated: n.status === "running",
                type: "smoothstep"
              });
            }
          });
          setEdges(initialEdges);
        }
      } catch (err) {
        console.error("Failed to load agent graph", err);
      }
    }

    load();

    const handleSpawned = (data: any) => {
      setNodes((prev) => [
        ...prev,
        {
          id: data.agent_id,
          type: "agent",
          position: POS[data.agent_type] ?? { x: Math.random() * 500, y: Math.random() * 500 },
          data: {
            id: data.agent_id,
            type: data.agent_type,
            label: data.agent_type.replace("_", " "),
            status: "spawned",
            detail: ""
          } as AgentNodeData,
        },
      ]);
      
      if (data.spawned_by) {
        setEdges(prev => [
          ...prev,
          {
            id: `e-${data.spawned_by}-${data.agent_id}`,
            source: data.spawned_by,
            target: data.agent_id,
            animated: true,
            type: "smoothstep"
          }
        ]);
      }
    };

    const handleComplete = (data: any) => {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === data.agent_id
            ? { ...n, data: { ...n.data, status: "complete" }, animated: false }
            : n
        )
      );
      setEdges(prev => prev.map(e => e.target === data.agent_id ? { ...e, animated: false } : e));
    };

    const handleFailed = (data: any) => {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === data.agent_id
            ? { ...n, data: { ...n.data, status: "failed" }, animated: false }
            : n
        )
      );
      setEdges(prev => prev.map(e => e.target === data.agent_id ? { ...e, animated: false } : e));
    };

    socket.on("agent_spawned", handleSpawned);
    socket.on("agent_complete", handleComplete);
    socket.on("agent_failed", handleFailed);

    return () => {
      socket.off("agent_spawned", handleSpawned);
      socket.off("agent_complete", handleComplete);
      socket.off("agent_failed", handleFailed);
    };
  }, [pipelineId]);

  return { nodes, edges };
}
