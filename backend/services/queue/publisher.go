package queue

import (
	"context"
	"log/slog"
)

// Publisher handles publishing typed events to Redis queues and channels
type Publisher struct {
	queue *RedisQueue
	log   *slog.Logger
}

func NewPublisher(queue *RedisQueue, log *slog.Logger) *Publisher {
	return &Publisher{
		queue: queue,
		log:   log,
	}
}

// PublishToOrchestrator publishes an event to the orchestrator queue.
// queue name: "queue:orchestrator"
func (p *Publisher) PublishToOrchestrator(ctx context.Context, event QueueEvent) error {
	return p.queue.Push(ctx, "queue:orchestrator", event)
}

// PublishWSEvent publishes a WebSocket event to the pipeline's Redis channel.
// channel: "ws:pipeline:{pipelineID}"
// Python agents also publish to this channel — Go reads and forwards to WS hub.
func (p *Publisher) PublishWSEvent(ctx context.Context, pipelineID string, msg WSMessage) error {
	channel := "ws:pipeline:" + pipelineID
	return p.queue.Publish(ctx, channel, msg)
}
