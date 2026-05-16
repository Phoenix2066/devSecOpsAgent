package webhook

// GithubEventType represents supported GitHub webhook event types
type GithubEventType string

const (
	EventPush        GithubEventType = "push"
	EventPullRequest GithubEventType = "pull_request"
	EventWorkflowRun GithubEventType = "workflow_run"
	EventCheckRun    GithubEventType = "check_run"
)

// PushPayload represents a GitHub push event
type PushPayload struct {
	Ref        string     `json:"ref"`   // "refs/heads/main"
	After      string     `json:"after"` // commit SHA
	Repository RepoInfo   `json:"repository"`
	Pusher     PusherInfo `json:"pusher"`
	HeadCommit CommitInfo `json:"head_commit"`
}

// WorkflowRunPayload represents a GitHub workflow_run event
type WorkflowRunPayload struct {
	Action      string      `json:"action"` // "completed"
	WorkflowRun WorkflowRun `json:"workflow_run"`
	Repository  RepoInfo    `json:"repository"`
}

type WorkflowRun struct {
	ID         int64  `json:"id"`
	Name       string `json:"name"`
	Status     string `json:"status"`     // "completed"
	Conclusion string `json:"conclusion"` // "failure" | "success"
	HeadSHA    string `json:"head_sha"`
	HeadBranch string `json:"head_branch"`
	HTMLURL    string `json:"html_url"`
}

type RepoInfo struct {
	FullName string `json:"full_name"` // "owner/repo"
	CloneURL string `json:"clone_url"`
	HTMLURL  string `json:"html_url"`
}

type PusherInfo struct {
	Name  string `json:"name"`
	Email string `json:"email"`
}

type CommitInfo struct {
	ID      string `json:"id"`
	Message string `json:"message"`
	URL     string `json:"url"`
}

// OrchestratorEvent is the normalized event published to Redis queue:orchestrator
type OrchestratorEvent struct {
	EventType   string `json:"event_type"`  // always "pipeline_triggered"
	PipelineID  string `json:"pipeline_id"` // UUID generated here
	Repo        string `json:"repo"`        // "owner/repo"
	CommitSHA   string `json:"commit_sha"`
	Branch      string `json:"branch"`       // "main" (stripped from ref)
	RunID       string `json:"run_id"`       // GitHub Actions run ID if known
	GithubToken string `json:"github_token"` // from project record
	TriggeredAt string `json:"triggered_at"` // ISO8601 UTC
}
