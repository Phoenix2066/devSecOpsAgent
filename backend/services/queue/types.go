package queue

type EventType string

const EventTypePipelineTriggered EventType = "pipeline_triggered"

type QueueEvent struct {
	Type    EventType `json:"type"`
	Payload any       `json:"payload"`
}
