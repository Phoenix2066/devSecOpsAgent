package webhook

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"strings"
)

func ValidateSignature(secret string, body []byte, sig string) error {
	if secret == "" {
		return nil
	}
	if !strings.HasPrefix(sig, "sha256=") {
		return errors.New("missing sha256 signature")
	}
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(body)
	expected := "sha256=" + hex.EncodeToString(mac.Sum(nil))
	if !hmac.Equal([]byte(expected), []byte(sig)) {
		return errors.New("invalid webhook signature")
	}
	return nil
}
