const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8080";

export async function fetchPipeline(id: string) {
  const res = await fetch(`${API_BASE_URL}/pipeline/${id}`);
  if (!res.ok) throw new Error("Failed to fetch pipeline");
  return res.json();
}

export async function fetchPipelineAgents(id: string) {
  const res = await fetch(`${API_BASE_URL}/pipeline/${id}/agents`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function fetchPipelineRuns(id: string) {
  const res = await fetch(`${API_BASE_URL}/pipeline/${id}/runs`);
  if (!res.ok) throw new Error("Failed to fetch runs");
  return res.json();
}

export async function fetchTimeline(id: string) {
  const res = await fetch(`${API_BASE_URL}/timeline/${id}`);
  if (!res.ok) throw new Error("Failed to fetch timeline");
  return res.json();
}
