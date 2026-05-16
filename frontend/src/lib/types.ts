// Matches Go backend types exactly

export type PipelineStatus =
  | "pending" | "running" | "failed" | "healing"
  | "validating" | "promoted" | "rolled_back"

export type AgentStatus = "spawned" | "running" | "complete" | "failed"

export interface Pipeline {
  id: string
  project_id: string
  commit_sha: string
  branch: string
  status: PipelineStatus
  triggered_at: string
  completed_at: string | null
}

export interface PipelineRun {
  id: string
  pipeline_id: string
  iteration: number
  status: string
  logs: string
  error_signature: string
  started_at: string
  ended_at: string | null
}

export interface AgentRecord {
  id: string
  pipeline_id: string
  agent_type: string
  status: AgentStatus
  spawned_at: string
  completed_at: string | null
  result: any
}

export interface PipelineState {
  pipeline_id: string
  status: PipelineStatus
  current_iteration: number
  active_agents: string[]
  graph: GraphData | null
  last_updated: string
}

export interface GraphData {
  pipeline_id: string
  root_id: string
  nodes: Record<string, GraphNode>
}

export interface GraphNode {
  node_id: string
  node_type: string
  status: string
  parent_id: string | null
  children: string[]
  metadata: Record<string, any>
}

// WebSocket message envelope — matches Go WSMessage exactly
export interface WSMessage {
  event: WSEventType
  pipeline_id: string
  timestamp: string
  data: Record<string, any>
}

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
  | "rollback_triggered"
  | "pipeline_status_changed"

export interface Project {
  id: string
  github_repo: string
  created_at: string
}

export interface LogLine {
  id: string
  level: "info" | "warn" | "error" | "success" | "memory" | "search"
  message: string
  timestamp: string
  agent_type?: string
}
