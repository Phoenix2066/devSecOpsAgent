package pipeline

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

// DBClient interface — what the pipeline manager needs from PostgreSQL
type DBClient interface {
	// Pipeline CRUD
	CreatePipeline(ctx context.Context, projectID, commitSHA, branch string) (string, error)
	GetPipeline(ctx context.Context, id string) (*Pipeline, error)
	UpdatePipelineStatus(ctx context.Context, id, status string) error
	ListPipelinesForProject(ctx context.Context, projectID string, limit int) ([]*Pipeline, error)

	// Pipeline runs
	CreatePipelineRun(ctx context.Context, pipelineID string, iteration int) (string, error)
	GetPipelineRuns(ctx context.Context, pipelineID string) ([]*PipelineRun, error)

	// Agents
	GetAgentsForPipeline(ctx context.Context, pipelineID string) ([]*AgentRecord, error)
	GetProjectByID(ctx context.Context, id string) (*ProjectInfo, error)
}

type ProjectInfo struct {
	ID          string
	GithubRepo  string
	GithubToken string
}

// RedisClient interface — what the pipeline manager needs from Redis
type RedisClient interface {
	Get(ctx context.Context, key string) *redis.StringCmd
	Set(ctx context.Context, key string, value interface{}, expiration time.Duration) *redis.StatusCmd
	Publish(ctx context.Context, channel string, message interface{}) *redis.IntCmd
	Subscribe(ctx context.Context, channels ...string) *redis.PubSub
	PSubscribe(ctx context.Context, channels ...string) *redis.PubSub
	RPush(ctx context.Context, key string, values ...interface{}) *redis.IntCmd
}

// WSHub interface — WebSocket hub for broadcasting to connected clients
type WSHub interface {
	BroadcastToPipeline(pipelineID string, message []byte)
}

// Manager handles pipeline lifecycle and state coordination
type Manager struct {
	DB    DBClient
	Redis RedisClient
	Hub   WSHub
	Log   *slog.Logger
}

// NewManager constructs a pipeline Manager
func NewManager(db DBClient, redis RedisClient, hub WSHub, log *slog.Logger) *Manager {
	return &Manager{
		DB:    db,
		Redis: redis,
		Hub:   hub,
		Log:   log,
	}
}

// CreatePipeline creates a new pipeline record in PostgreSQL and
// initializes its state in Redis.
func (m *Manager) CreatePipeline(ctx context.Context, projectID,
	commitSHA, branch string) (string, error) {
	id, err := m.DB.CreatePipeline(ctx, projectID, commitSHA, branch)
	if err != nil {
		return "", err
	}

	state := PipelineState{
		PipelineID:       id,
		Status:           StatusPending,
		CurrentIteration: 0,
		LastUpdated:      time.Now().UTC(),
	}

	stateJSON, _ := json.Marshal(state)
	if err := m.Redis.Set(ctx, fmt.Sprintf("pipeline:%s:state", id), stateJSON, 24*time.Hour).Err(); err != nil {
		m.Log.Error("failed to initialize pipeline state in redis", "pipeline_id", id, "error", err)
	}

	return id, nil
}

// GetPipeline returns pipeline from Redis (fast path) or PostgreSQL (fallback).
func (m *Manager) GetPipeline(ctx context.Context, id string) (*Pipeline, error) {
	// 1. Try Redis
	val, err := m.Redis.Get(ctx, fmt.Sprintf("pipeline:%s:state", id)).Result()
	if err == nil {
		var state PipelineState
		if err := json.Unmarshal([]byte(val), &state); err == nil {
			return &Pipeline{
				ID:     state.PipelineID,
				Status: state.Status,
			}, nil
		}
	}

	// 2. Fallback to DB
	return m.DB.GetPipeline(ctx, id)
}

// GetPipelineState returns the full live PipelineState from Redis.
func (m *Manager) GetPipelineState(ctx context.Context, id string) (*PipelineState, error) {
	var state PipelineState
	
	val, err := m.Redis.Get(ctx, fmt.Sprintf("pipeline:%s:state", id)).Result()
	if err == nil {
		_ = json.Unmarshal([]byte(val), &state)
	} else {
		// Fallback to DB if state isn't in Redis
		p, err := m.DB.GetPipeline(ctx, id)
		if err != nil || p == nil {
			return nil, fmt.Errorf("pipeline not found")
		}
		state.PipelineID = p.ID
		state.Status = p.Status
	}

	// Fetch graph separately since Python updates it in a different key
	graphVal, err := m.Redis.Get(ctx, fmt.Sprintf("pipeline:%s:graph", id)).Result()
	if err == nil && graphVal != "" {
		var graph any
		if err := json.Unmarshal([]byte(graphVal), &graph); err == nil {
			state.Graph = graph
		}
	}

	return &state, nil
}

// GetPipelineRuns returns all iteration runs for a pipeline from PostgreSQL.
func (m *Manager) GetPipelineRuns(ctx context.Context, pipelineID string) ([]*PipelineRun, error) {
	return m.DB.GetPipelineRuns(ctx, pipelineID)
}

// GetAgents returns all agent records for a pipeline from PostgreSQL.
func (m *Manager) GetAgents(ctx context.Context, pipelineID string) ([]*AgentRecord, error) {
	return m.DB.GetAgentsForPipeline(ctx, pipelineID)
}

// ListForProject returns recent pipelines for a project.
func (m *Manager) ListForProject(ctx context.Context, projectID string, limit int) ([]*Pipeline, error) {
	if limit <= 0 {
		limit = 20
	}
	return m.DB.ListPipelinesForProject(ctx, projectID, limit)
}

// StartWSForwarder subscribes to Redis pubsub for a pipeline and
// forwards all events to the WebSocket hub.
func (m *Manager) StartWSForwarder(ctx context.Context, pipelineID string) {
	channel := fmt.Sprintf("ws:pipeline:%s", pipelineID)
	pubsub := m.Redis.Subscribe(ctx, channel)
	defer pubsub.Close()

	ch := pubsub.Channel()
	for {
		select {
		case <-ctx.Done():
			return
		case msg, ok := <-ch:
			if !ok {
				return
			}
			m.Hub.BroadcastToPipeline(pipelineID, []byte(msg.Payload))
		}
	}
}

// StartGlobalWSForwarder subscribes to all pipeline WS channels using
// Redis pattern subscription: "ws:pipeline:*"
func (m *Manager) StartGlobalWSForwarder(ctx context.Context) {
	const pattern = "ws:pipeline:*"

	for {
		select {
		case <-ctx.Done():
			return
		default:
			pubsub := m.Redis.PSubscribe(ctx, pattern)
			ch := pubsub.Channel()

			m.Log.Info("global WS forwarder started", "pattern", pattern)

		loop:
			for {
				select {
				case <-ctx.Done():
					pubsub.Close()
					return
				case msg, ok := <-ch:
					if !ok {
						m.Log.Warn("redis subscription channel closed, reconnecting in 2s")
						break loop
					}

					pipelineID := strings.TrimPrefix(msg.Channel, "ws:pipeline:")
					m.Hub.BroadcastToPipeline(pipelineID, []byte(msg.Payload))
				}
			}

			pubsub.Close()
			time.Sleep(2 * time.Second)
		}
	}
}

// broadcastStatusChange broadcasts a StatusChangedEvent to WebSocket clients.
func (m *Manager) broadcastStatusChange(pipelineID, status string) {
	event := StatusChangedEvent{
		Event:      "pipeline_status_changed",
		PipelineID: pipelineID,
		Status:     status,
		Timestamp:  time.Now().UTC(),
	}

	msg, _ := json.Marshal(event)
	m.Hub.BroadcastToPipeline(pipelineID, msg)
}

// --- HTTP Handlers ---

func (m *Manager) GetPipelineHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	p, err := m.GetPipeline(r.Context(), id)
	if err != nil || p == nil {
		http.Error(w, "pipeline not found", http.StatusNotFound)
		return
	}
	writeJSON(w, http.StatusOK, p)
}

func (m *Manager) GetAgentsHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	agents, err := m.GetAgents(r.Context(), id)
	if err != nil {
		agents = []*AgentRecord{}
	}
	writeJSON(w, http.StatusOK, agents)
}

func (m *Manager) GetRunsHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	runs, err := m.GetPipelineRuns(r.Context(), id)
	if err != nil {
		runs = []*PipelineRun{}
	}
	writeJSON(w, http.StatusOK, runs)
}

func (m *Manager) GetLogsHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("pipeline_id")
	runs, _ := m.GetPipelineRuns(r.Context(), id)
	logs := ""
	for _, run := range runs {
		logs += run.Logs + "\n"
	}
	writeJSON(w, http.StatusOK, map[string]string{"pipeline_id": id, "logs": logs})
}

func (m *Manager) SearchMemoryHTTP(w http.ResponseWriter, r *http.Request) {
	// This would call the Python agent or a shared DB
	writeJSON(w, http.StatusOK, map[string]any{"hit": false})
}

func (m *Manager) GetTimelineHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("pipeline_id")
	writeJSON(w, http.StatusOK, []map[string]any{
		{"pipeline_id": id, "event": "pipeline_triggered", "timestamp": time.Now().UTC()},
	})
}

func (m *Manager) RerunPipelineHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	m.Log.Info("rerun requested", "pipeline_id", id)
	p, err := m.DB.GetPipeline(r.Context(), id)
	if err != nil {
		m.Log.Error("db error", "error", err)
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	if p == nil {
		m.Log.Warn("pipeline not found", "pipeline_id", id)
		http.Error(w, "pipeline not found", http.StatusNotFound)
		return
	}

	project, err := m.DB.GetProjectByID(r.Context(), p.ProjectID)
	if err != nil {
		http.Error(w, "project not found", http.StatusInternalServerError)
		return
	}

	event := map[string]any{
		"event_type":   "pipeline_triggered",
		"pipeline_id":  id,
		"repo":         project.GithubRepo,
		"commit_sha":   p.CommitSHA,
		"branch":       p.Branch,
		"github_token": project.GithubToken,
		"triggered_at": time.Now().UTC().Format(time.RFC3339),
	}

	eventJSON, _ := json.Marshal(event)
	if err := m.Redis.RPush(r.Context(), "queue:orchestrator", eventJSON).Err(); err != nil {
		http.Error(w, "failed to trigger rerun", http.StatusInternalServerError)
		return
	}

	m.Log.Info("triggered manual rerun", "pipeline_id", id)
	writeJSON(w, http.StatusOK, map[string]string{"status": "triggered"})
}

func (m *Manager) PromotePipelineHTTP(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	m.Log.Info("promote requested", "pipeline_id", id)
	if err := m.DB.UpdatePipelineStatus(r.Context(), id, "promoted"); err != nil {
		m.Log.Error("failed to update status", "pipeline_id", id, "error", err)
		http.Error(w, "failed to update status", http.StatusInternalServerError)
		return
	}
	m.broadcastStatusChange(id, "promoted")
	writeJSON(w, http.StatusOK, map[string]string{"status": "promoted"})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
