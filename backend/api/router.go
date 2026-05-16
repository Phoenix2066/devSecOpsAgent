package api

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"time"

	"anvil/backend/services/pipeline"
	"anvil/backend/services/webhook"
	"anvil/backend/services/websocket"
)

// Dependencies holds all handler dependencies
type Dependencies struct {
	WebhookHandler  *webhook.Handler
	PipelineManager *pipeline.Manager
	WSHandler       *websocket.Handler
	ProjectDB       ProjectDB
	Log             *slog.Logger
}

type ProjectDB interface {
	CreateProject(ctx context.Context, userID, repo, webhookSecret, githubToken string) (string, error)
	ListProjects(ctx context.Context, userID string) ([]*webhook.Project, error)
	DeleteProject(ctx context.Context, id string) error
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, DELETE, PATCH, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func loggingMiddleware(log *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		// We could wrap response writer to get status code, but simplified for now
		next.ServeHTTP(w, r)
		log.Info("http request", "method", r.Method, "path", r.URL.Path, "duration", time.Since(start).String())
	})
}

func recoveryMiddleware(log *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				log.Error("panic recovered", "error", err)
				http.Error(w, "internal server error", http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

// NewRouter builds and returns the HTTP router.
func NewRouter(deps Dependencies) http.Handler {
	mux := http.NewServeMux()

	// Webhook
	mux.Handle("POST /webhook/github", deps.WebhookHandler)

	// Pipeline endpoints
	mux.HandleFunc("GET /pipeline/{id}", deps.PipelineManager.GetPipelineHTTP)
	mux.HandleFunc("GET /pipeline/{id}/state", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		state, err := deps.PipelineManager.GetPipelineState(r.Context(), id)
		if err != nil {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		writeJSON(w, http.StatusOK, state)
	})
	mux.HandleFunc("GET /pipeline/{id}/runs", deps.PipelineManager.GetRunsHTTP)
	mux.HandleFunc("GET /pipeline/{id}/agents", deps.PipelineManager.GetAgentsHTTP)
	mux.HandleFunc("POST /pipeline/{id}/rerun", deps.PipelineManager.RerunPipelineHTTP)
	mux.HandleFunc("POST /pipeline/{id}/promote", deps.PipelineManager.PromotePipelineHTTP)

	// Projects
	mux.HandleFunc("POST /project/", func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		deps.Log.Info("raw request body", "body", string(body))
		
		var req struct {
			UserID        string `json:"user_id"`
			Repo          string `json:"github_repo"`
			WebhookSecret string `json:"webhook_secret"`
			GithubToken   string `json:"github_token"`
		}
		if err := json.Unmarshal(body, &req); err != nil {
			http.Error(w, "invalid request body", http.StatusBadRequest)
			return
		}
		id, err := deps.ProjectDB.CreateProject(r.Context(), req.UserID, req.Repo, req.WebhookSecret, req.GithubToken)
		if err != nil {
			deps.Log.Error("failed to create project", "error", err)
			http.Error(w, "failed to create project", http.StatusInternalServerError)
			return
		}
		writeJSON(w, http.StatusCreated, map[string]string{"id": id})
	})

	mux.HandleFunc("GET /project/", func(w http.ResponseWriter, r *http.Request) {
		projects, err := deps.ProjectDB.ListProjects(r.Context(), "default-user")
		if err != nil {
			deps.Log.Error("failed to list projects", "error", err)
			http.Error(w, "failed to list projects", http.StatusInternalServerError)
			return
		}
		if projects == nil {
			projects = []*webhook.Project{}
		}
		writeJSON(w, http.StatusOK, projects)
	})

	mux.HandleFunc("DELETE /project/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		if err := deps.ProjectDB.DeleteProject(r.Context(), id); err != nil {
			deps.Log.Error("failed to delete project", "error", err)
			http.Error(w, "failed to delete project", http.StatusInternalServerError)
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "deleted"})
	})

	mux.HandleFunc("GET /project/{id}/pipelines", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		pipelines, _ := deps.PipelineManager.ListForProject(r.Context(), id, 20)
		writeJSON(w, http.StatusOK, pipelines)
	})

	mux.HandleFunc("/ws/pipeline/", deps.WSHandler.ServeWS)

	// Health
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "timestamp": time.Now().UTC()})
	})

	// Wrap with middleware
	return recoveryMiddleware(deps.Log, loggingMiddleware(deps.Log, corsMiddleware(mux)))
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
