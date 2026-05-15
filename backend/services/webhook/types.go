package webhook

type GithubPayload struct {
	Ref        string `json:"ref"`
	After      string `json:"after"`
	Repository struct {
		FullName string `json:"full_name"`
	} `json:"repository"`
	WorkflowRun struct {
		ID         int64  `json:"id"`
		HeadBranch string `json:"head_branch"`
		HeadSHA    string `json:"head_sha"`
		Conclusion string `json:"conclusion"`
	} `json:"workflow_run"`
}

type PushEvent = GithubPayload
type PREvent = GithubPayload
