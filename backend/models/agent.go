package models

type Agent struct {
	ID         string         `json:"id"`
	PipelineID string         `json:"pipeline_id"`
	AgentType  string         `json:"agent_type"`
	Status     string         `json:"status"`
	Result     map[string]any `json:"result,omitempty"`
}
