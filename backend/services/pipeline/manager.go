package pipeline

import (
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"anvil/backend/services/queue"
)

type Manager struct {
	mu        sync.RWMutex
	pipelines map[string]Pipeline
	runs      map[string][]PipelineRun
	agents    map[string][]AgentRecord
	queue     *queue.MemoryQueue
}

func NewManager(q *queue.MemoryQueue) *Manager {
	return &Manager{
		pipelines: map[string]Pipeline{},
		runs:      map[string][]PipelineRun{},
		agents:    map[string][]AgentRecord{},
		queue:     q,
	}
}

func (m *Manager) StartPipeline(repo, branch, commitSHA, runID string) Pipeline {
	m.mu.Lock()
	defer m.mu.Unlock()
	id := "pipe-" + time.Now().UTC().Format("20060102150405.000000000")
	p := Pipeline{ID: id, Repo: repo, Branch: branch, CommitSHA: commitSHA, Status: StatePending, TriggeredAt: time.Now().UTC()}
	m.pipelines[id] = p
	m.runs[id] = []PipelineRun{{
		ID:         id + "-run-1",
		PipelineID: id,
		Iteration:  1,
		Status:     StatePending,
		Logs:       "pipeline accepted and queued",
		StartedAt:  time.Now().UTC(),
	}}
	m.queue.PublishEvent("queue:orchestrator", queue.QueueEvent{
		Type: queue.EventTypePipelineTriggered,
		Payload: map[string]any{
			"event_type":   "pipeline_triggered",
			"pipeline_id":  id,
			"repo":         repo,
			"commit_sha":   commitSHA,
			"branch":       branch,
			"run_id":       runID,
			"triggered_at": p.TriggeredAt.Format(time.RFC3339),
		},
	})
	return p
}

func (m *Manager) StartPipelineHTTP(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Repo      string `json:"repo"`
		Branch    string `json:"branch"`
		CommitSHA string `json:"commit_sha"`
		RunID     string `json:"run_id"`
	}
	_ = json.NewDecoder(r.Body).Decode(&input)
	if input.Repo == "" {
		input.Repo = "demo/dependency-mismatch"
	}
	if input.Branch == "" {
		input.Branch = "main"
	}
	if input.CommitSHA == "" {
		input.CommitSHA = "demo-sha"
	}
	writeJSON(w, http.StatusAccepted, m.StartPipeline(input.Repo, input.Branch, input.CommitSHA, input.RunID))
}

func (m *Manager) GetPipelineHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	m.mu.RLock()
	defer m.mu.RUnlock()
	p, ok := m.pipelines[id]
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "pipeline not found"})
		return
	}
	writeJSON(w, http.StatusOK, p)
}

func (m *Manager) GetAgentsHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	m.mu.RLock()
	defer m.mu.RUnlock()
	writeJSON(w, http.StatusOK, m.agents[id])
}

func (m *Manager) GetRunsHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	m.mu.RLock()
	defer m.mu.RUnlock()
	writeJSON(w, http.StatusOK, m.runs[id])
}

func (m *Manager) GetLogsHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("pipeline_id")
	m.mu.RLock()
	defer m.mu.RUnlock()
	logs := ""
	for _, run := range m.runs[id] {
		logs += run.Logs + "\n"
	}
	writeJSON(w, http.StatusOK, map[string]string{"pipeline_id": id, "logs": logs})
}

func (m *Manager) SearchMemoryHTTP(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query().Get("q")
	hit := query == "" || query == "pip_conflict:requests:2.28.0_vs_2.31.0"
	writeJSON(w, http.StatusOK, map[string]any{
		"hit":             hit,
		"incident_id":     "seed-requests-conflict",
		"error_signature": "pip_conflict:requests:2.28.0_vs_2.31.0",
		"fix_applied":     "upgrade requests to 2.31.0",
		"confidence":      0.91,
		"success_rate":    0.85,
		"reuse":           hit,
	})
}

func (m *Manager) GetTimelineHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("pipeline_id")
	writeJSON(w, http.StatusOK, []map[string]any{
		{"pipeline_id": id, "event": "pipeline_triggered", "timestamp": time.Now().UTC().Format(time.RFC3339)},
	})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
