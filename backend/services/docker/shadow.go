package docker

func CreateShadowEnv(id string) ShadowEnv {
	return ShadowEnv{ID: id, ContainerID: "container-" + id, NetworkID: "network-" + id}
}
