package queue

type Handler func(QueueEvent)

func Subscribe(q *MemoryQueue, channel string, handler Handler) {
	for _, event := range q.Events(channel) {
		handler(event)
	}
}
