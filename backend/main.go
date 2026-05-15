package main

import (
	"log"
	"net/http"
	"os"

	"anvil/backend/api"
	"anvil/backend/services/pipeline"
	"anvil/backend/services/queue"
	"anvil/backend/services/websocket"
)

func main() {
	port := getenv("PORT", "8080")
	queueClient := queue.NewMemoryQueue()
	pipelineManager := pipeline.NewManager(queueClient)
	hub := websocket.NewHub()
	go hub.Run()

	router := api.NewRouter(api.Dependencies{
		Pipelines: pipelineManager,
		Queue:     queueClient,
		Hub:       hub,
	})

	log.Printf("backend listening on :%s", port)
	if err := http.ListenAndServe(":"+port, router); err != nil {
		log.Fatal(err)
	}
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
