package queue

import "sync"

type MemoryQueue struct {
	mu       sync.RWMutex
	channels map[string][]QueueEvent
}

func NewMemoryQueue() *MemoryQueue {
	return &MemoryQueue{channels: map[string][]QueueEvent{}}
}

func (q *MemoryQueue) PublishEvent(channel string, payload QueueEvent) {
	q.mu.Lock()
	defer q.mu.Unlock()
	q.channels[channel] = append(q.channels[channel], payload)
}

func (q *MemoryQueue) Events(channel string) []QueueEvent {
	q.mu.RLock()
	defer q.mu.RUnlock()
	events := q.channels[channel]
	return append([]QueueEvent(nil), events...)
}
