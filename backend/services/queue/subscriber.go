package queue

import (
	"context"
	"log/slog"
	"time"

	"github.com/redis/go-redis/v9"
)

// Subscriber handles Redis pubsub subscriptions with auto-reconnect
type Subscriber struct {
	client *redis.Client
	log    *slog.Logger
}

func NewSubscriber(client *redis.Client, log *slog.Logger) *Subscriber {
	return &Subscriber{
		client: client,
		log:    log,
	}
}

// SubscribePattern subscribes to a Redis pattern and calls handler for each message.
// handler receives (channel string, payload []byte).
// Auto-reconnects with 2 second backoff if subscription drops.
// Exits when ctx is cancelled.
// Use for: "ws:pipeline:*" global WS forwarding
func (s *Subscriber) SubscribePattern(ctx context.Context, pattern string, handler func(channel string, payload []byte)) {
	for {
		select {
		case <-ctx.Done():
			return
		default:
			pubsub := s.client.PSubscribe(ctx, pattern)
			ch := pubsub.Channel()
			s.log.Info("redis pattern subscription started", "pattern", pattern)

		loop:
			for {
				select {
				case <-ctx.Done():
					pubsub.Close()
					return
				case msg, ok := <-ch:
					if !ok {
						s.log.Warn("redis subscription channel closed, reconnecting in 2s")
						break loop
					}
					handler(msg.Channel, []byte(msg.Payload))
				}
			}

			pubsub.Close()
			time.Sleep(2 * time.Second)
		}
	}
}
