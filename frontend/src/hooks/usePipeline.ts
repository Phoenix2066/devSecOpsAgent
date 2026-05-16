import { useState, useEffect } from "react";
import { getPipeline, getPipelineState } from "@/lib/api";
import { usePipelineSocket } from "@/lib/socket";
import type { Pipeline, PipelineStatus } from "@/lib/types";

export function usePipeline(pipelineId: string) {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [status, setStatus] = useState<PipelineStatus>("pending");
  const [currentIteration, setCurrentIteration] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const socket = usePipelineSocket(pipelineId);

  useEffect(() => {
    async function load() {
      if (!pipelineId) {
        setPipeline(null);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const [pData, sData] = await Promise.all([
          getPipeline(pipelineId),
          getPipelineState(pipelineId).catch(() => null)
        ]);
        
        if (pData) {
          setPipeline(pData);
          setStatus(sData?.status ?? pData.status);
          setCurrentIteration(sData?.current_iteration ?? 0);
        }
      } catch (err) {
        console.error("Failed to load pipeline", err);
      } finally {
        setIsLoading(false);
      }
    }

    load();

    const handleIteration = (data: any) => setCurrentIteration(data.iteration);
    const handleStatus = (data: any) => setStatus(data.status as PipelineStatus);
    const handlePromoted = () => setStatus("promoted");
    const handleFailed = () => setStatus("failed");
    const handleValidationPassed = () => setStatus("healing"); // Map to StatusHealing if needed

    socket.on("repair_iteration", handleIteration);
    socket.on("pipeline_status_changed", handleStatus);
    socket.on("deployment_promoted", handlePromoted);
    socket.on("pipeline_failed", handleFailed);
    socket.on("validation_passed", handleValidationPassed);

    return () => {
      socket.off("repair_iteration", handleIteration);
      socket.off("pipeline_status_changed", handleStatus);
      socket.off("deployment_promoted", handlePromoted);
      socket.off("pipeline_failed", handleFailed);
      socket.off("validation_passed", handleValidationPassed);
    };
  }, [pipelineId]);

  return { pipeline, status, currentIteration, isLoading };
}
