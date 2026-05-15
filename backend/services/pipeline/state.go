package pipeline

type PipelineState string

const (
	StatePending    PipelineState = "pending"
	StateRunning    PipelineState = "running"
	StateFailed     PipelineState = "failed"
	StateHealed     PipelineState = "healed"
	StatePromoted   PipelineState = "promoted"
	StateRolledBack PipelineState = "rolled_back"
)

func CanTransition(from, to PipelineState) bool {
	allowed := map[PipelineState][]PipelineState{
		StatePending:  {StateRunning, StateFailed},
		StateRunning:  {StateFailed, StateHealed, StatePromoted},
		StateFailed:   {StateRunning, StateRolledBack},
		StateHealed:   {StatePromoted, StateRolledBack},
		StatePromoted: {},
	}
	for _, candidate := range allowed[from] {
		if candidate == to {
			return true
		}
	}
	return false
}
