package pipeline

// PipelineStatus constants — must match Python agent status strings exactly
const (
	StatusPending    = "pending"
	StatusRunning    = "running"
	StatusFailed     = "failed"
	StatusHealing    = "healing"
	StatusValidating = "validating"
	StatusPromoted   = "promoted"
	StatusRolledBack = "rolled_back"
)

// TerminalStatuses are statuses where completed_at should be set
var TerminalStatuses = map[string]bool{
	StatusPromoted:   true,
	StatusRolledBack: true,
	StatusFailed:     true,
}

// ValidTransitions defines legal pipeline status transitions
// From status → allowed next statuses
var ValidTransitions = map[string][]string{
	StatusPending:    {StatusRunning, StatusFailed},
	StatusRunning:    {StatusHealing, StatusFailed},
	StatusHealing:    {StatusValidating, StatusFailed, StatusRolledBack},
	StatusValidating: {StatusPromoted, StatusHealing, StatusRolledBack},
	StatusPromoted:   {},
	StatusRolledBack: {},
	StatusFailed:     {},
}

// IsValidTransition returns true if transitioning from → to is allowed
func IsValidTransition(from, to string) bool {
	allowed, ok := ValidTransitions[from]
	if !ok {
		return false
	}
	for _, a := range allowed {
		if a == to {
			return true
		}
	}
	return false
}

// IsTerminal returns true if status is a terminal state
func IsTerminal(status string) bool {
	return TerminalStatuses[status]
}
