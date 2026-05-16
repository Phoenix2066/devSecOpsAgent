package websocket

import "log/slog"

// Hub maintains all active WebSocket connections.
// Thread-safe — all operations go through the run loop channel.
type Hub struct {
	// clients grouped by pipeline_id
	pipelines  map[string]map[*Client]bool
	broadcast  chan broadcastMsg
	register   chan *Client
	unregister chan *Client
	log        *slog.Logger
}

type broadcastMsg struct {
	pipelineID string
	payload    []byte
}

func NewHub(log *slog.Logger) *Hub {
	return &Hub{
		pipelines:  make(map[string]map[*Client]bool),
		broadcast:  make(chan broadcastMsg, 256),
		register:   make(chan *Client, 256),
		unregister: make(chan *Client, 256),
		log:        log,
	}
}

// Run starts the hub event loop. Call as goroutine: go hub.Run()
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			if _, ok := h.pipelines[client.PipelineID]; !ok {
				h.pipelines[client.PipelineID] = make(map[*Client]bool)
			}
			h.pipelines[client.PipelineID][client] = true
			h.log.Info("client registered", "client_id", client.ID, "pipeline_id", client.PipelineID)

		case client := <-h.unregister:
			if clients, ok := h.pipelines[client.PipelineID]; ok {
				if _, ok := clients[client]; ok {
					delete(clients, client)
					close(client.send)
					h.log.Info("client unregistered", "client_id", client.ID, "pipeline_id", client.PipelineID)
					if len(clients) == 0 {
						delete(h.pipelines, client.PipelineID)
					}
				}
			}

		case msg := <-h.broadcast:
			if clients, ok := h.pipelines[msg.pipelineID]; ok {
				for client := range clients {
					select {
					case client.send <- msg.payload:
					default:
						// send channel full: unregister client (slow consumer)
						h.log.Warn("client send buffer full, disconnecting", "client_id", client.ID)
						delete(clients, client)
						close(client.send)
						if len(clients) == 0 {
							delete(h.pipelines, msg.pipelineID)
						}
					}
				}
			}
		}
	}
}

// BroadcastToPipeline queues a message for all clients watching a pipeline.
// Non-blocking — drops message if broadcast channel is full (log warning).
func (h *Hub) BroadcastToPipeline(pipelineID string, payload []byte) {
	msg := broadcastMsg{
		pipelineID: pipelineID,
		payload:    payload,
	}
	select {
	case h.broadcast <- msg:
	default:
		h.log.Warn("hub broadcast channel full, dropping message", "pipeline_id", pipelineID)
	}
}

// Register adds a client to the hub.
func (h *Hub) Register(client *Client) {
	h.register <- client
}

// Unregister removes a client from the hub.
func (h *Hub) Unregister(client *Client) {
	h.unregister <- client
}
