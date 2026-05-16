// All API calls to Go backend at VITE_API_URL
import { Pipeline, PipelineState, PipelineRun, AgentRecord, Project } from "./types"

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8080"

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(BASE + path, options)
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`API error ${response.status}: ${text}`)
  }
  return response.json() as Promise<T>
}

// --- Pipeline ---

export async function getPipeline(id: string): Promise<Pipeline> {
  return apiFetch<Pipeline>(`/pipeline/${id}`)
}

export async function getPipelineState(id: string): Promise<PipelineState | null> {
  try {
    return await apiFetch<PipelineState>(`/pipeline/${id}/state`)
  } catch (e) {
    return null
  }
}

export async function getPipelineRuns(id: string): Promise<PipelineRun[]> {
  return apiFetch<PipelineRun[]>(`/pipeline/${id}/runs`)
}

export async function getPipelineAgents(id: string): Promise<AgentRecord[]> {
  return apiFetch<AgentRecord[]>(`/pipeline/${id}/agents`)
}

export async function listPipelines(projectId: string): Promise<Pipeline[]> {
  return apiFetch<Pipeline[]>(`/project/${projectId}/pipelines`)
}

export async function listProjects(): Promise<Project[]> {
  // Assuming a generic endpoint for now or user-specific
  return apiFetch<Project[]>("/project/")
}

export async function createProject(repo: string, token: string): Promise<{ id: string }> {
  return apiFetch<{ id: string }>("/project/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: "default-user",
      github_repo: repo,
      github_token: token,
      webhook_secret: Math.random().toString(36).substring(2),
    }),
  })
}

export async function deleteProject(id: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/project/${id}`, {
    method: "DELETE",
  })
}

export async function rerunPipeline(id: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/pipeline/${id}/rerun`, {
    method: "POST",
  })
}

export async function promotePipeline(id: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/pipeline/${id}/promote`, {
    method: "POST",
  })
}

// --- Health ---

export async function getHealth(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/health")
}
