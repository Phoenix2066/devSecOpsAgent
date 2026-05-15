package models

type Project struct {
	ID              string `json:"id"`
	UserID          string `json:"user_id"`
	GithubRepo      string `json:"github_repo"`
	GithubInstallID int64  `json:"github_install_id,omitempty"`
	WebhookSecret   string `json:"-"`
}
