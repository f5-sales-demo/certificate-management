package main

import (
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"errors"
	"net/http"
	"net/url"
	"regexp"
	"strings"
)

// XFCC is identity forwarded by the qualified edge, not proof of the upstream
// TLS peer. The edge must sanitize client headers before policy evaluation.
// Parsing rejects ambiguity; it does not independently establish edge trust.
var xfccField = regexp.MustCompile(`^([A-Za-z]+)=(?:"([^"\r\n]*)"|([^";,\r\n]*))$`)
var challengeValue = regexp.MustCompile(`^[A-Za-z0-9_-]{1,128}$`)

func forwardedFingerprint(r *http.Request) (string, error) {
	values := r.Header.Values("X-Forwarded-Client-Cert")
	if len(values) == 0 {
		return "", nil
	}
	invalid := errors.New("invalid forwarded identity")
	if len(values) != 1 || len(values[0]) > 65536 || strings.ContainsAny(values[0], ",\r\n") {
		return "", invalid
	}
	fields := map[string]string{}
	for _, part := range strings.Split(values[0], ";") {
		match := xfccField.FindStringSubmatch(strings.TrimSpace(part))
		if match == nil {
			return "", invalid
		}
		if _, exists := fields[match[1]]; exists {
			return "", invalid
		}
		value := match[2]
		if value == "" {
			value = match[3]
		}
		fields[match[1]] = value
	}
	hash, err := hex.DecodeString(fields["Hash"])
	if err != nil || len(hash) != 32 || fields["Cert"] == "" || fields["Chain"] == "" {
		return "", invalid
	}
	certPEM, err := url.PathUnescape(fields["Cert"])
	if err != nil {
		return "", invalid
	}
	block, rest := pem.Decode([]byte(certPEM))
	if block == nil || block.Type != "CERTIFICATE" || len(strings.TrimSpace(string(rest))) != 0 {
		return "", invalid
	}
	leaf, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		return "", invalid
	}
	sum := sha256.Sum256(leaf.Raw)
	fingerprint := hex.EncodeToString(sum[:])
	if fingerprint != strings.ToLower(fields["Hash"]) {
		return "", invalid
	}
	chain, err := url.PathUnescape(fields["Chain"])
	if err != nil {
		return "", invalid
	}
	chainBytes := []byte(chain)
	count := 0
	for len(strings.TrimSpace(string(chainBytes))) > 0 {
		cert, remaining := pem.Decode(chainBytes)
		if cert == nil || cert.Type != "CERTIFICATE" {
			return "", invalid
		}
		if _, err := x509.ParseCertificate(cert.Bytes); err != nil {
			return "", invalid
		}
		chainBytes = remaining
		count++
	}
	if count == 0 {
		return "", invalid
	}
	return fingerprint, nil
}

func clientIdentityHandler(w wingman, upstreamFingerprint string, write bool) http.HandlerFunc {
	return func(rw http.ResponseWriter, r *http.Request) {
		expected := "/mtls/identity"
		if write {
			expected = "/mtls/write"
		}
		if r.URL.Path != expected {
			http.NotFound(rw, r)
			return
		}
		fingerprint, err := forwardedFingerprint(r)
		if err != nil || write && fingerprint == "" {
			http.Error(rw, "forbidden", http.StatusForbidden)
			return
		}
		challenge := r.URL.Query().Get("challenge")
		if !challengeValue.MatchString(challenge) || len(r.URL.Query()["challenge"]) != 1 {
			http.Error(rw, "invalid challenge", http.StatusBadRequest)
			return
		}
		if w.ready(r.Context()) != nil {
			http.Error(rw, "not ready", http.StatusServiceUnavailable)
			return
		}
		rw.Header().Set("Content-Type", "application/json")
		rw.Header().Set("Cache-Control", "no-store")
		_ = json.NewEncoder(rw).Encode(struct {
			Challenge           string `json:"challenge"`
			Method              string `json:"method"`
			ClientFingerprint   string `json:"forwarded_client_certificate_sha256"`
			IdentitySource      string `json:"identity_source"`
			UpstreamFingerprint string `json:"origin_server_certificate_sha256"`
			Synthetic           bool   `json:"synthetic_acknowledgment"`
		}{challenge, r.Method, fingerprint, "edge-xfcc", upstreamFingerprint, write})
	}
}
