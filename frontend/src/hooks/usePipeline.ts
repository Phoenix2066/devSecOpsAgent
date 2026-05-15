import { useState, useEffect } from "react";
import { fetchPipeline } from "@/lib/api";
import { socket, type WSMessage } from "@/lib/socket";
import type { Pipeline, PipelineStatus } from "@/lib/mock-data";

export function usePipeline(pipelineId: string) {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [status, setStatus] = useState<PipelineStatus>("pending");
  const [currentIteration, setCurrentIteration] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      try {
        const data = await fetchPipeline(pipelineId);
        setPipeline(data);
        setStatus(data.status);
        setCurrentIteration(data.iteration);
      } catch (err) {
        console.error("Failed to load pipeline", err);
      } finally {
        setIsLoading(false);
      }
    }

    load();

    function onMessage(msg: WSMessage) {
      if (msg.pipeline_id !== pipelineId) return;

      if (msg.event === "repair_iteration") {
        setCurrentIteration(msg.data.iteration);
      } else if (msg.event === "deployment_promoted") {
        setStatus("promoted");
      } else if (msg.event === "pipeline_failed") {
        setStatus("failed");
      } else if (msg.event === "validation_passed") {
        setStatus("healed");
      }
    }

    socket.on("message", onMessage);
    return () => {
      socket.off("message", onMessage);
    };
  }, [pipelineId]);

  return { pipeline, status, currentIteration, isLoading };
}
