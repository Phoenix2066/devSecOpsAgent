package models

type User struct {
	ID             string `json:"id"`
	Email          string `json:"email"`
	GithubUsername string `json:"github_username,omitempty"`
	AvatarURL      string `json:"avatar_url,omitempty"`
}
