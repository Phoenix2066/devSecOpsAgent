package websocket

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	// Allow all origins for hackathon — restrict in production
	CheckOrigin: func(r *http.Request) bool { return true },
}

// Handler handles WebSocket upgrade requests
type Handler struct {
	Hub *Hub
	Log *slog.Logger
}

func NewHandler(hub *Hub, log *slog.Logger) *Handler {
	return &Handler{
		Hub: hub,
		Log: log,
	}
}

// ServeWS handles GET /ws/pipeline/:id
func (h *Handler) ServeWS(w http.ResponseWriter, r *http.Request) {
	// 1. Extract pipeline_id from URL path parameter
	pathParts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(pathParts) < 3 || pathParts[0] != "ws" || pathParts[1] != "pipeline" {
		http.Error(w, "invalid path", http.StatusBadRequest)
		return
	}
	pipelineID := pathParts[2]

	// 2. Upgrade HTTP connection to WebSocket
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		h.Log.Error("failed to upgrade websocket connection", "error", err)
		return
	}

	// 3. Create Client
	client := &Client{
		ID:         uuid.New().String(),
		PipelineID: pipelineID,
		conn:       conn,
		send:       make(chan []byte, 256),
		hub:        h.Hub,
	}

	// 4. Register client
	h.Hub.Register(client)

	// 5. Start read/write pumps
	go client.writePump()
	client.readPump() // blocks until client disconnects
}

// readPump reads messages from WebSocket connection.
func (c *Client) readPump() {
	defer func() {
		c.hub.Unregister(c)
		c.conn.Close()
	}()

	// Set initial read deadline
	c.conn.SetReadDeadline(time.Now().Add(60 * time.Second))

	for {
		_, message, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				c.hub.log.Error("websocket read error", "error", err)
			}
			break
		}

		// Reset deadline on successful read
		c.conn.SetReadDeadline(time.Now().Add(60 * time.Second))

		var subMsg SubscribeMessage
		if err := json.Unmarshal(message, &subMsg); err == nil && subMsg.Action == "subscribe" && subMsg.PipelineID != "" {
			// Handle subscription change if needed (re-register)
			c.hub.Unregister(c)
			c.PipelineID = subMsg.PipelineID
			c.hub.Register(c)
		}
	}
}

// writePump writes messages from send channel to WebSocket connection.
func (c *Client) writePump() {
	ticker := time.NewTicker(30 * time.Second)
	defer func() {
		ticker.Stop()
		c.conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				// The hub closed the channel.
				c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)

			// Add queued messages to the current websocket message.
			n := len(c.send)
			for i := 0; i < n; i++ {
				w.Write(<-c.send)
			}

			if err := w.Close(); err != nil {
				return
			}
		case <-ticker.C:
			c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
