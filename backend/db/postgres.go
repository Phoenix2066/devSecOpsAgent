package db

import (
	"context"
	"errors"

	"anvil/backend/services/pipeline"
	"anvil/backend/services/webhook"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Client implements webhook.DBClient and pipeline.DBClient
type Client struct {
	pool *pgxpool.Pool
}

func NewClient(pool *pgxpool.Pool) *Client {
	return &Client{pool: pool}
}

// --- webhook.DBClient implementation ---

// GetProjectByRepo fetches a project by github_repo field.
func (c *Client) GetProjectByRepo(ctx context.Context, repo string) (*webhook.Project, error) {
	var p webhook.Project
	err := c.pool.QueryRow(ctx,
		"SELECT id, user_id, github_repo, webhook_secret, github_token FROM projects WHERE github_repo = $1 LIMIT 1",
		repo).Scan(&p.ID, &p.UserID, &p.GithubRepo, &p.WebhookSecret, &p.GithubToken)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &p, nil
}

// CreatePipeline inserts a new pipeline row with status="pending".
func (c *Client) CreatePipeline(ctx context.Context, projectID, commitSHA, branch string) (string, error) {
	var id string
	err := c.pool.QueryRow(ctx,
		"INSERT INTO pipelines (id, project_id, commit_sha, branch, status, triggered_at) VALUES (gen_random_uuid(), $1, $2, $3, 'pending', NOW()) RETURNING id",
		projectID, commitSHA, branch).Scan(&id)

	if err != nil {
		return "", err
	}
	return id, nil
}

// --- pipeline.DBClient implementation ---

// GetPipeline fetches a pipeline by ID.
func (c *Client) GetPipeline(ctx context.Context, id string) (*pipeline.Pipeline, error) {
	var p pipeline.Pipeline
	err := c.pool.QueryRow(ctx,
		"SELECT id, project_id, commit_sha, branch, status, triggered_at, completed_at FROM pipelines WHERE id = $1",
		id).Scan(&p.ID, &p.ProjectID, &p.CommitSHA, &p.Branch, &p.Status, &p.TriggeredAt, &p.CompletedAt)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &p, nil
}

// UpdatePipelineStatus updates pipeline status.
func (c *Client) UpdatePipelineStatus(ctx context.Context, id, status string) error {
	var err error
	if pipeline.IsTerminal(status) {
		_, err = c.pool.Exec(ctx, "UPDATE pipelines SET status=$1, completed_at=NOW() WHERE id=$2", status, id)
	} else {
		_, err = c.pool.Exec(ctx, "UPDATE pipelines SET status=$1 WHERE id=$2", status, id)
	}
	return err
}

// ListPipelinesForProject returns recent pipelines for a project.
func (c *Client) ListPipelinesForProject(ctx context.Context, projectID string, limit int) ([]*pipeline.Pipeline, error) {
	rows, err := c.pool.Query(ctx,
		"SELECT id, project_id, commit_sha, branch, status, triggered_at, completed_at FROM pipelines WHERE project_id = $1 ORDER BY triggered_at DESC LIMIT $2",
		projectID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var pipelines []*pipeline.Pipeline
	for rows.Next() {
		var p pipeline.Pipeline
		if err := rows.Scan(&p.ID, &p.ProjectID, &p.CommitSHA, &p.Branch, &p.Status, &p.TriggeredAt, &p.CompletedAt); err != nil {
			return nil, err
		}
		pipelines = append(pipelines, &p)
	}
	return pipelines, nil
}

// CreatePipelineRun inserts a new pipeline_run row.
func (c *Client) CreatePipelineRun(ctx context.Context, pipelineID string, iteration int) (string, error) {
	var id string
	err := c.pool.QueryRow(ctx,
		"INSERT INTO pipeline_runs (id, pipeline_id, iteration, status, started_at) VALUES (gen_random_uuid(), $1, $2, 'running', NOW()) RETURNING id",
		pipelineID, iteration).Scan(&id)

	if err != nil {
		return "", err
	}
	return id, nil
}

// GetPipelineRuns returns all runs for a pipeline ordered by iteration.
func (c *Client) GetPipelineRuns(ctx context.Context, pipelineID string) ([]*pipeline.PipelineRun, error) {
	rows, err := c.pool.Query(ctx,
		"SELECT id, pipeline_id, iteration, status, logs, error_signature, started_at, ended_at FROM pipeline_runs WHERE pipeline_id = $1 ORDER BY iteration ASC",
		pipelineID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var runs []*pipeline.PipelineRun
	for rows.Next() {
		var r pipeline.PipelineRun
		if err := rows.Scan(&r.ID, &r.PipelineID, &r.Iteration, &r.Status, &r.Logs, &r.ErrorSignature, &r.StartedAt, &r.EndedAt); err != nil {
			return nil, err
		}
		runs = append(runs, &r)
	}
	return runs, nil
}

// GetAgentsForPipeline returns all agent records for a pipeline.
func (c *Client) GetAgentsForPipeline(ctx context.Context, pipelineID string) ([]*pipeline.AgentRecord, error) {
	rows, err := c.pool.Query(ctx,
		"SELECT id, pipeline_id, agent_type, status, spawned_at, completed_at, result FROM agents WHERE pipeline_id = $1 ORDER BY spawned_at ASC",
		pipelineID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var records []*pipeline.AgentRecord
	for rows.Next() {
		var r pipeline.AgentRecord
		if err := rows.Scan(&r.ID, &r.PipelineID, &r.AgentType, &r.Status, &r.SpawnedAt, &r.CompletedAt, &r.Result); err != nil {
			return nil, err
		}
		records = append(records, &r)
	}
	return records, nil
}

func (c *Client) GetProjectByID(ctx context.Context, id string) (*pipeline.ProjectInfo, error) {
	var p pipeline.ProjectInfo
	err := c.pool.QueryRow(ctx,
		"SELECT id, github_repo, github_token FROM projects WHERE id = $1",
		id).Scan(&p.ID, &p.GithubRepo, &p.GithubToken)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &p, nil
}

// --- Additional methods used by Python via HTTP proxy ---

// CreateProject inserts a new project row.
func (c *Client) CreateProject(ctx context.Context, userID, repo, webhookSecret, githubToken string) (string, error) {
	var id string
	err := c.pool.QueryRow(ctx,
		"INSERT INTO projects (id, user_id, github_repo, webhook_secret, github_token) VALUES (gen_random_uuid(), $1, $2, $3, $4) RETURNING id",
		userID, repo, webhookSecret, githubToken).Scan(&id)

	if err != nil {
		return "", err
	}
	return id, nil
}

// GetProject fetches a project by ID.
func (c *Client) GetProject(ctx context.Context, id string) (*webhook.Project, error) {
	var p webhook.Project
	err := c.pool.QueryRow(ctx,
		"SELECT id, user_id, github_repo, webhook_secret, github_token FROM projects WHERE id = $1",
		id).Scan(&p.ID, &p.UserID, &p.GithubRepo, &p.WebhookSecret, &p.GithubToken)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &p, nil
}

// ListProjects returns all projects for a user.
func (c *Client) ListProjects(ctx context.Context, userID string) ([]*webhook.Project, error) {
	rows, err := c.pool.Query(ctx,
		"SELECT id, user_id, github_repo, webhook_secret, github_token FROM projects WHERE user_id = $1 ORDER BY created_at DESC",
		userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var projects []*webhook.Project
	for rows.Next() {
		var p webhook.Project
		if err := rows.Scan(&p.ID, &p.UserID, &p.GithubRepo, &p.WebhookSecret, &p.GithubToken); err != nil {
			return nil, err
		}
		projects = append(projects, &p)
	}
	return projects, nil
}

// DeleteProject deletes a project and all cascading data.
func (c *Client) DeleteProject(ctx context.Context, id string) error {
	// 1. Get pipelines for this project
	rows, err := c.pool.Query(ctx, "SELECT id FROM pipelines WHERE project_id = $1", id)
	if err != nil {
		return err
	}
	var pids []string
	for rows.Next() {
		var pid string
		rows.Scan(&pid)
		pids = append(pids, pid)
	}
	rows.Close()

	// 2. Delete data for each pipeline
	for _, pid := range pids {
		_, _ = c.pool.Exec(ctx, "DELETE FROM agents WHERE pipeline_id = $1", pid)
		_, _ = c.pool.Exec(ctx, "DELETE FROM pipeline_runs WHERE pipeline_id = $1", pid)
	}

	// 3. Delete pipelines
	_, err = c.pool.Exec(ctx, "DELETE FROM pipelines WHERE project_id = $1", id)
	if err != nil {
		return err
	}

	// 4. Finally delete the project
	_, err = c.pool.Exec(ctx, "DELETE FROM projects WHERE id = $1", id)
	return err
}
