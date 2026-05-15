package websocket

type WSEventType string

const (
	EventAgentSpawned       WSEventType = "agent_spawned"
	EventAgentComplete      WSEventType = "agent_complete"
	EventAgentFailed        WSEventType = "agent_failed"
	EventPipelineFailed     WSEventType = "pipeline_failed"
	EventMemoryHit          WSEventType = "memory_hit"
	EventMemoryMiss         WSEventType = "memory_miss"
	EventRepairStarted      WSEventType = "repair_started"
	EventRepairIteration    WSEventType = "repair_iteration"
	EventWebSearchStarted   WSEventType = "web_search_started"
	EventWebSearchComplete  WSEventType = "web_search_complete"
	EventValidationPassed   WSEventType = "validation_passed"
	EventValidationFailed   WSEventType = "validation_failed"
	EventDeploymentPromoted WSEventType = "deployment_promoted"
	EventRollbackTriggered  WSEventType = "rollback_triggered"
)

type WSMessage struct {
	Event      WSEventType    `json:"event"`
	PipelineID string         `json:"pipeline_id"`
	Timestamp  string         `json:"timestamp"`
	Data       map[string]any `json:"data"`
}
