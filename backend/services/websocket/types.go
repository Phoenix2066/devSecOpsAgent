package websocket

import "github.com/gorilla/websocket"

// Client represents a connected WebSocket client
type Client struct {
	ID         string
	PipelineID string // which pipeline this client is watching
	conn       *websocket.Conn
	send       chan []byte
	hub        *Hub
}

// SubscribeMessage is sent by client to subscribe to a pipeline
type SubscribeMessage struct {
	Action     string `json:"action"`      // "subscribe"
	PipelineID string `json:"pipeline_id"`
}
