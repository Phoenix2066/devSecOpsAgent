package queue

// EventType represents all possible queue event types
type EventType string

const (
	EventPipelineTriggered     EventType = "pipeline_triggered"
	EventInvestigationComplete EventType = "investigation_complete"
	EventRepairIterationFailed EventType = "repair_iteration_failed"
	EventAgentSpawned          EventType = "agent_spawned"
	EventAgentComplete         EventType = "agent_complete"
	EventAgentFailed           EventType = "agent_failed"
	EventMemoryHit             EventType = "memory_hit"
	EventMemoryMiss            EventType = "memory_miss"
	EventRepairStarted         EventType = "repair_started"
	EventRepairIteration       EventType = "repair_iteration"
	EventValidationPassed      EventType = "validation_passed"
	EventValidationFailed      EventType = "validation_failed"
	EventDeploymentPromoted    EventType = "deployment_promoted"
	EventRollbackTriggered     EventType = "rollback_triggered"
)

// QueueEvent is the envelope for all Redis queue messages
type QueueEvent struct {
	Type      EventType      `json:"event_type"`
	Payload   map[string]any `json:"payload"`
	Timestamp string         `json:"timestamp"` // ISO8601 UTC
}

// WSMessage is the envelope for all WebSocket messages sent to frontend
// Must match the TypeScript WSMessage type in frontend/lib/types.ts exactly
type WSMessage struct {
	Event      string         `json:"event"`
	PipelineID string         `json:"pipeline_id"`
	Timestamp  string         `json:"timestamp"`
	Data       map[string]any `json:"data"`
}
