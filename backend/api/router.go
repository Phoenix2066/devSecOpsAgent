package api

import (
	"encoding/json"
	"net/http"
	"strings"

	"anvil/backend/services/pipeline"
	"anvil/backend/services/queue"
	"anvil/backend/services/webhook"
	"anvil/backend/services/websocket"
)

type Dependencies struct {
	Pipelines *pipeline.Manager
	Queue     *queue.MemoryQueue
	Hub       *websocket.Hub
}

func NewRouter(deps Dependencies) http.Handler {
	wh := webhook.NewHandler(deps.Pipelines, deps.Queue)
	mux := http.NewServeMux()
	mux.HandleFunc("/health", method(http.MethodGet, func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	}))
	mux.HandleFunc("/webhook/github", method(http.MethodPost, wh.HandleGithubWebhook))
	mux.HandleFunc("/pipeline/start", method(http.MethodPost, deps.Pipelines.StartPipelineHTTP))
	mux.HandleFunc("/pipeline/", func(w http.ResponseWriter, r *http.Request) {
		id, suffix := splitIDPath(r.URL.Path, "/pipeline/")
		r.SetPathValue("id", id)
		switch {
		case r.Method == http.MethodGet && suffix == "":
			deps.Pipelines.GetPipelineHTTP(w, r)
		case r.Method == http.MethodGet && suffix == "/agents":
			deps.Pipelines.GetAgentsHTTP(w, r)
		case r.Method == http.MethodGet && suffix == "/runs":
			deps.Pipelines.GetRunsHTTP(w, r)
		default:
			http.NotFound(w, r)
		}
	})
	mux.HandleFunc("/logs/", method(http.MethodGet, func(w http.ResponseWriter, r *http.Request) {
		r.SetPathValue("pipeline_id", strings.TrimPrefix(r.URL.Path, "/logs/"))
		deps.Pipelines.GetLogsHTTP(w, r)
	}))
	mux.HandleFunc("/memory/search", method(http.MethodGet, deps.Pipelines.SearchMemoryHTTP))
	mux.HandleFunc("/timeline/", method(http.MethodGet, func(w http.ResponseWriter, r *http.Request) {
		r.SetPathValue("pipeline_id", strings.TrimPrefix(r.URL.Path, "/timeline/"))
		deps.Pipelines.GetTimelineHTTP(w, r)
	}))
	mux.HandleFunc("/ws/pipeline/", method(http.MethodGet, deps.Hub.HandleWebSocket))

	return LoggingMiddleware(CORSMiddleware(mux))
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func method(expected string, handler http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != expected {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handler(w, r)
	}
}

func splitIDPath(path, prefix string) (string, string) {
	rest := strings.TrimPrefix(path, prefix)
	index := strings.Index(rest, "/")
	if index == -1 {
		return rest, ""
	}
	return rest[:index], rest[index:]
}
