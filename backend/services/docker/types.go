package docker

type Container struct {
	ID    string `json:"id"`
	Image string `json:"image"`
}

type ShadowEnv struct {
	ID          string `json:"id"`
	ContainerID string `json:"container_id"`
	NetworkID   string `json:"network_id"`
}

type BuildResult struct {
	ExitCode int    `json:"exit_code"`
	Output   string `json:"output"`
	Passed   bool   `json:"passed"`
}
