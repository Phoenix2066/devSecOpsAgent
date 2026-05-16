// Real data for the DevSecOps dashboard
export type PipelineStatus = "running" | "failed" | "healed" | "promoted" | "pending";
export type AgentStatus = "spawned" | "running" | "complete" | "failed";
export type AgentType =
  | "orchestrator" | "coordinator" | "memory" | "monitor"
  | "log_analyzer" | "dependency_inspector" | "web_search"
  | "config_analyzer" | "code_analyzer"
  | "repair_docker" | "repair_yaml" | "repair_imports";

export interface Pipeline {
  id: string;
  repo: string;
  branch: string;
  commit: string;
  status: PipelineStatus;
  iteration: number;
  startedAt: string;
  message: string;
}

export interface AgentNodeData {
  id: string;
  type: AgentType;
  label: string;
  status: AgentStatus;
  detail: string;
}

export interface LogLine {
  ts: string;
  level: "info" | "warn" | "error" | "success" | "debug";
  agent: string;
  msg: string;
}

export interface MemoryHit {
  signature: string;
  similarity: number;
  fix: string;
  successRate: number;
  timesSeen: number;
}

export interface TimelineEvent {
  iter: number;
  title: string;
  status: "ok" | "fail" | "running";
  detail: string;
  duration: string;
}

export interface PipelineDetail {
  nodes: AgentNodeData[];
  edges: { source: string; target: string; animated?: boolean }[];
  logs: LogLine[];
  memory: MemoryHit[];
  timeline: TimelineEvent[];
  problems: { level: "error" | "warn"; agent: string; msg: string }[];
}

export const pipelines: Pipeline[] = [];

export const pipelineDetails: Record<string, PipelineDetail> = {};

export function getPipelineDetail(id: string): PipelineDetail | null {
  return pipelineDetails[id] || null;
}

export const fileTree = [
  { type: "folder", name: "Active Pipelines", count: 0, children: [] },
  { type: "folder", name: "Recent Runs", count: 0, children: [] },
  { type: "folder", name: "Shadow Environments", count: 0, children: [] },
];
