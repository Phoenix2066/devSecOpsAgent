package webhook

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"

	"anvil/backend/services/pipeline"
	"anvil/backend/services/queue"
)

type Handler struct {
	pipelines *pipeline.Manager
	queue     *queue.MemoryQueue
	secret    string
}

func NewHandler(pm *pipeline.Manager, q *queue.MemoryQueue) *Handler {
	return &Handler{pipelines: pm, queue: q, secret: os.Getenv("GITHUB_WEBHOOK_SECRET")}
}

func (h *Handler) HandleGithubWebhook(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if err := ValidateSignature(h.secret, body, r.Header.Get("X-Hub-Signature-256")); err != nil {
		http.Error(w, err.Error(), http.StatusUnauthorized)
		return
	}
	var payload GithubPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	event := r.Header.Get("X-GitHub-Event")
	var p pipeline.Pipeline
	switch event {
	case "push", "pull_request":
		p, err = h.handlePush(payload)
	case "check_run", "workflow_run":
		p, err = h.handleWorkflowRun(payload)
	default:
		w.WriteHeader(http.StatusAccepted)
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ignored", "event": event})
		return
	}
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(p)
}

func (h *Handler) handlePush(payload GithubPayload) (pipeline.Pipeline, error) {
	branch := strings.TrimPrefix(payload.Ref, "refs/heads/")
	return h.pipelines.StartPipeline(payload.Repository.FullName, branch, payload.After, ""), nil
}

func (h *Handler) handleWorkflowRun(payload GithubPayload) (pipeline.Pipeline, error) {
	runID := strconv.FormatInt(payload.WorkflowRun.ID, 10)
	return h.pipelines.StartPipeline(payload.Repository.FullName, payload.WorkflowRun.HeadBranch, payload.WorkflowRun.HeadSHA, runID), nil
}
