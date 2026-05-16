package webhook

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"strings"
)

// ValidateSignature validates a GitHub HMAC-SHA256 webhook signature.
// sig format from header X-Hub-Signature-256: "sha256=<hex>"
// Returns nil if valid, error if invalid or malformed.
func ValidateSignature(secret string, body []byte, sig string) error {
	if !strings.HasPrefix(sig, "sha256=") {
		return errors.New("invalid signature format")
	}

	hexSig := strings.TrimPrefix(sig, "sha256=")
	expectedSig, err := hex.DecodeString(hexSig)
	if err != nil {
		return errors.New("invalid hex in signature")
	}

	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(body)
	actualSig := mac.Sum(nil)

	if !hmac.Equal(actualSig, expectedSig) {
		return errors.New("signature mismatch")
	}

	return nil
}

// ExtractBranch extracts branch name from GitHub ref string.
// "refs/heads/main" → "main"
// "refs/heads/feature/my-branch" → "feature/my-branch"
// Returns empty string if ref format unrecognized.
func ExtractBranch(ref string) string {
	if !strings.HasPrefix(ref, "refs/heads/") {
		return ""
	}
	return strings.TrimPrefix(ref, "refs/heads/")
}
