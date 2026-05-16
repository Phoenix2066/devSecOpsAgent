package queue

import (
	"context"
	"encoding/json"
	"log/slog"
	"time"

	"github.com/redis/go-redis/v9"
)

// RedisQueue wraps go-redis for type-safe queue operations
type RedisQueue struct {
	client *redis.Client
	log    *slog.Logger
}

func NewRedisQueue(client *redis.Client, log *slog.Logger) *RedisQueue {
	return &RedisQueue{
		client: client,
		log:    log,
	}
}

// Push serializes payload to JSON and RPushes to queue name.
// Returns error if marshal or Redis push fails.
func (q *RedisQueue) Push(ctx context.Context, queueName string, payload any) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	return q.client.RPush(ctx, queueName, data).Err()
}

// Pop BLPOPs from queue with timeout. Returns nil, nil on timeout.
// Deserializes JSON into map[string]any.
func (q *RedisQueue) Pop(ctx context.Context, queueName string, timeout time.Duration) (map[string]any, error) {
	result, err := q.client.BLPop(ctx, timeout, queueName).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // timeout
		}
		return nil, err
	}

	if len(result) < 2 {
		return nil, nil
	}

	var payload map[string]any
	if err := json.Unmarshal([]byte(result[1]), &payload); err != nil {
		return nil, err
	}

	return payload, nil
}

// Publish publishes a message to a Redis pubsub channel.
func (q *RedisQueue) Publish(ctx context.Context, channel string, message any) error {
	data, err := json.Marshal(message)
	if err != nil {
		return err
	}
	return q.client.Publish(ctx, channel, data).Err()
}

// Subscribe returns a Redis PubSub subscription to a channel.
func (q *RedisQueue) Subscribe(ctx context.Context, channel string) *redis.PubSub {
	return q.client.Subscribe(ctx, channel)
}

// PSubscribe returns a Redis PubSub pattern subscription.
func (q *RedisQueue) PSubscribe(ctx context.Context, pattern string) *redis.PubSub {
	return q.client.PSubscribe(ctx, pattern)
}
