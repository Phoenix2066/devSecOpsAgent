package websocket

import "net/http"

type Hub struct {
	broadcast chan WSMessage
}

func NewHub() *Hub {
	return &Hub{broadcast: make(chan WSMessage, 64)}
}

func (h *Hub) Run() {
	for range h.broadcast {
	}
}

func (h *Hub) Broadcast(msg WSMessage) {
	select {
	case h.broadcast <- msg:
	default:
	}
}

func (h *Hub) HandleWebSocket(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	_, _ = w.Write([]byte(`{"error":"websocket upgrade is stubbed in local MVD backend; frontend uses mock events when disconnected"}`))
}
