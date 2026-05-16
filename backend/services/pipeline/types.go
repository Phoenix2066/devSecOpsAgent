package pipeline

import "time"

// Pipeline represents a full pipeline record
type Pipeline struct {
	ID          string     `json:"id"`
	ProjectID   string     `json:"project_id"`
	CommitSHA   string     `json:"commit_sha"`
	Branch      string     `json:"branch"`
	Status      string     `json:"status"`
	TriggeredAt time.Time  `json:"triggered_at"`
	CompletedAt *time.Time `json:"completed_at"`
}

// PipelineRun represents one repair iteration
type PipelineRun struct {
	ID             string     `json:"id"`
	PipelineID     string     `json:"pipeline_id"`
	Iteration      int        `json:"iteration"`
	Status         string     `json:"status"`
	Logs           string     `json:"logs"`
	ErrorSignature string     `json:"error_signature"`
	StartedAt      time.Time  `json:"started_at"`
	EndedAt        *time.Time `json:"ended_at"`
}

// AgentRecord represents an agent spawned for a pipeline
type AgentRecord struct {
	ID          string     `json:"id"`
	PipelineID  string     `json:"pipeline_id"`
	AgentType   string     `json:"agent_type"`
	Status      string     `json:"status"`
	SpawnedAt   time.Time  `json:"spawned_at"`
	CompletedAt *time.Time `json:"completed_at"`
	Result      any        `json:"result"`
}

// PipelineState is the full live state stored in Redis
// Updated by Python agents via Redis, read by Go for HTTP responses
type PipelineState struct {
	PipelineID       string    `json:"pipeline_id"`
	Status           string    `json:"status"`
	CurrentIteration int       `json:"current_iteration"`
	ActiveAgents     []string  `json:"active_agents"`
	Graph            any       `json:"graph"` // ReactFlow-ready graph
	LastUpdated      time.Time `json:"last_updated"`
}

// StatusChangedEvent is broadcast to WebSocket clients on status change
type StatusChangedEvent struct {
	Event      string    `json:"event"` // "pipeline_status_changed"
	PipelineID string    `json:"pipeline_id"`
	Status     string    `json:"status"`
	Timestamp  time.Time `json:"timestamp"`
}
