package github

type RepoRef struct {
	Owner string `json:"owner"`
	Repo  string `json:"repo"`
}

type BranchRef struct {
	Name string `json:"name"`
	SHA  string `json:"sha"`
}

type PRRef struct {
	URL string `json:"url"`
}
