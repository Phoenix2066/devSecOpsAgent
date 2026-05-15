package models

type Incident struct {
	ID             string  `json:"id"`
	ErrorSignature string  `json:"error_signature"`
	RootCause      string  `json:"root_cause"`
	FixApplied     string  `json:"fix_applied"`
	Confidence     float64 `json:"confidence"`
	SuccessRate    float64 `json:"success_rate"`
}
