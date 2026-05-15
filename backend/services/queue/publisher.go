package queue

func PublishEvent(q *MemoryQueue, channel string, payload QueueEvent) {
	q.PublishEvent(channel, payload)
}
