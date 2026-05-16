package webhook

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

// Handler holds dependencies for the webhook handler
type Handler struct {
	DB    DBClient      // interface
	Redis RedisClient   // interface
	Log   *slog.Logger
}

// DBClient interface — only what the webhook handler needs from PostgreSQL
type DBClient interface {
	GetProjectByRepo(ctx context.Context, repo string) (*Project, error)
	CreatePipeline(ctx context.Context, projectID, commitSHA, branch string) (string, error)
}

// RedisClient interface — only what the webhook handler needs from Redis
type RedisClient interface {
	RPush(ctx context.Context, key string, values ...interface{}) *redis.IntCmd
}

// Project represents a project record from PostgreSQL
type Project struct {
	ID            string `json:"id"`
	UserID        string `json:"user_id"`
	GithubRepo    string `json:"github_repo"`
	WebhookSecret string `json:"webhook_secret"`
	GithubToken   string `json:"github_token"`
}

// NewHandler constructs a webhook Handler with dependencies
func NewHandler(db DBClient, redis RedisClient, log *slog.Logger) *Handler {
	return &Handler{
		DB:    db,
		Redis: redis,
		Log:   log,
	}
}

// ServeHTTP implements http.Handler — registers as POST /webhook/github
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	// 1. Read full request body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		h.Log.Error("failed to read request body", "error", err)
		writeError(w, http.StatusBadRequest, "failed to read body")
		return
	}
	defer r.Body.Close()

	// 2. Get X-GitHub-Event header
	eventType := r.Header.Get("X-GitHub-Event")
	if eventType == "" {
		writeError(w, http.StatusBadRequest, "missing X-GitHub-Event header")
		return
	}

	// 3. Get X-Hub-Signature-256 header
	sig := r.Header.Get("X-Hub-Signature-256")
	if sig == "" {
		writeError(w, http.StatusBadRequest, "missing X-Hub-Signature-256 header")
		return
	}

	// 4. Parse repo from payload to look up project
	var partial struct {
		Repository struct {
			FullName string `json:"full_name"`
		} `json:"repository"`
	}
	if err := json.Unmarshal(body, &partial); err != nil {
		h.Log.Error("failed to parse repo from payload", "error", err)
		writeError(w, http.StatusBadRequest, "invalid JSON payload")
		return
	}
	repo := partial.Repository.FullName

	// 5. Get project from DB
	project, err := h.DB.GetProjectByRepo(ctx, repo)
	if err != nil {
		h.Log.Error("project not found", "repo", repo, "error", err)
		writeError(w, http.StatusNotFound, "project not found")
		return
	}

	// 6. ValidateSignature
	if err := ValidateSignature(project.WebhookSecret, body, sig); err != nil {
		h.Log.Warn("invalid signature", "repo", repo, "error", err)
		writeError(w, http.StatusForbidden, "invalid signature")
		return
	}

	h.Log.Info("received github event", "repo", repo, "event", eventType)

	// 7. Dispatch on event type
	switch GithubEventType(eventType) {
	case EventPush:
		err = h.handlePush(ctx, body, project)
	case EventWorkflowRun:
		err = h.handleWorkflowRun(ctx, body, project)
	default:
		h.Log.Debug("ignoring event type", "event", eventType)
		writeJSON(w, http.StatusOK, map[string]string{"status": "ignored"})
		return
	}

	if err != nil {
		h.Log.Error("failed to handle event", "event", eventType, "error", err)
		writeError(w, http.StatusInternalServerError, "event processing failed")
		return
	}

	// 8. Return 200
	writeJSON(w, http.StatusOK, map[string]string{"status": "accepted"})
}

// handlePush processes a push event.
func (h *Handler) handlePush(ctx context.Context, body []byte, project *Project) error {
	var payload PushPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		return err
	}

	branch := ExtractBranch(payload.Ref)
	if branch != "main" && branch != "master" {
		h.Log.Debug("skipping push to non-default branch", "branch", branch)
		return nil
	}

	// Create pipeline record
	pipelineID, err := h.DB.CreatePipeline(ctx, project.ID, payload.After, branch)
	if err != nil {
		return fmt.Errorf("failed to create pipeline: %w", err)
	}

	// Build OrchestratorEvent
	event := OrchestratorEvent{
		EventType:   "pipeline_triggered",
		PipelineID:  pipelineID,
		Repo:        project.GithubRepo,
		CommitSHA:   payload.After,
		Branch:      branch,
		GithubToken: project.GithubToken,
		TriggeredAt: time.Now().UTC().Format(time.RFC3339),
	}

	return h.publishToOrchestrator(ctx, event)
}

// handleWorkflowRun processes a workflow_run completed event.
func (h *Handler) handleWorkflowRun(ctx context.Context, body []byte, project *Project) error {
	var payload WorkflowRunPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		return err
	}

	if payload.WorkflowRun.Conclusion != "failure" {
		h.Log.Debug("skipping successful workflow run", "run_id", payload.WorkflowRun.ID)
		return nil
	}

	branch := payload.WorkflowRun.HeadBranch
	if branch == "" {
		branch = "main" // fallback
	}

	// Create pipeline record
	pipelineID, err := h.DB.CreatePipeline(ctx, project.ID, payload.WorkflowRun.HeadSHA, branch)
	if err != nil {
		return fmt.Errorf("failed to create pipeline: %w", err)
	}

	// Build OrchestratorEvent
	event := OrchestratorEvent{
		EventType:   "pipeline_triggered",
		PipelineID:  pipelineID,
		Repo:        project.GithubRepo,
		CommitSHA:   payload.WorkflowRun.HeadSHA,
		Branch:      branch,
		RunID:       strconv.FormatInt(payload.WorkflowRun.ID, 10),
		GithubToken: project.GithubToken,
		TriggeredAt: time.Now().UTC().Format(time.RFC3339),
	}

	return h.publishToOrchestrator(ctx, event)
}

// publishToOrchestrator serializes event to JSON and RPushes to Redis.
func (h *Handler) publishToOrchestrator(ctx context.Context, event OrchestratorEvent) error {
	eventJSON, err := json.Marshal(event)
	if err != nil {
		return err
	}

	if err := h.Redis.RPush(ctx, "queue:orchestrator", eventJSON).Err(); err != nil {
		return fmt.Errorf("failed to push to redis: %w", err)
	}

	h.Log.Info("triggered autonomous repair", "pipeline_id", event.PipelineID, "repo", event.Repo)
	return nil
}

// writeJSON writes a JSON response with given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

// writeError writes a JSON error response: {"error": message}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
