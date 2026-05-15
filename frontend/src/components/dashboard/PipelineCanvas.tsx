import ReactFlow, {
  Background, BackgroundVariant, Controls, MiniMap,
} from "reactflow";
import { AgentNode } from "./AgentNode";
import { useAgentGraph } from "@/hooks/useAgentGraph";

const nodeTypes = { agent: AgentNode };

export function PipelineCanvas({ pipelineId }: { pipelineId: string }) {
  const { nodes, edges } = useAgentGraph(pipelineId);

  return (
    <div className="h-full w-full bg-editor">
      <ReactFlow
        key={pipelineId}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="oklch(0.32 0.014 260)" />
        <Controls showInteractive={false} />
        <MiniMap
          pannable zoomable
          maskColor="oklch(0.18 0.012 260 / 0.7)"
          nodeColor={(n) => {
            const status = (n.data as any)?.status;
            if (status === "running") return "oklch(0.7 0.16 230)";
            if (status === "complete") return "oklch(0.78 0.17 155)";
            if (status === "failed") return "oklch(0.62 0.22 25)";
            return "oklch(0.55 0.015 255)";
          }}
          style={{
            background: "oklch(0.215 0.014 260)",
            border: "1px solid oklch(0.28 0.014 260)",
          }}
        />
      </ReactFlow>
    </div>
  );
}
