package pipeline

import "time"

type Pipeline struct {
	ID          string        `json:"id"`
	ProjectID   string        `json:"project_id,omitempty"`
	CommitSHA   string        `json:"commit_sha"`
	Branch      string        `json:"branch"`
	Repo        string        `json:"repo"`
	Status      PipelineState `json:"status"`
	TriggeredAt time.Time     `json:"triggered_at"`
	CompletedAt *time.Time    `json:"completed_at,omitempty"`
}

type PipelineRun struct {
	ID             string        `json:"id"`
	PipelineID     string        `json:"pipeline_id"`
	Iteration      int           `json:"iteration"`
	Status         PipelineState `json:"status"`
	Logs           string        `json:"logs"`
	ErrorSignature string        `json:"error_signature,omitempty"`
	StartedAt      time.Time     `json:"started_at"`
	EndedAt        *time.Time    `json:"ended_at,omitempty"`
}

type Stage struct {
	Name   string `json:"name"`
	Status string `json:"status"`
}

type AgentRecord struct {
	ID          string         `json:"id"`
	PipelineID  string         `json:"pipeline_id"`
	AgentType   string         `json:"agent_type"`
	Status      string         `json:"status"`
	SpawnedAt   time.Time      `json:"spawned_at"`
	CompletedAt *time.Time     `json:"completed_at,omitempty"`
	Result      map[string]any `json:"result,omitempty"`
}
