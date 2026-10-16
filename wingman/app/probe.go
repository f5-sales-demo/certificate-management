package main

import (
	"context"
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"errors"
	"net/http"
	"os"
	"strings"
	"time"
)

func certificateChain(data []byte) ([]*x509.Certificate, error) {
	certificates := []*x509.Certificate{}
	for len(strings.TrimSpace(string(data))) > 0 {
		block, rest := pem.Decode(data)
		if block == nil || block.Type != "CERTIFICATE" {
			return nil, errors.New("invalid identity certificate chain")
		}
		certificate, err := x509.ParseCertificate(block.Bytes)
		if err != nil {
			return nil, errors.New("invalid identity certificate")
		}
		certificates = append(certificates, certificate)
		data = rest
	}
	if len(certificates) == 0 {
		return nil, errors.New("empty identity certificate chain")
	}
	return certificates, nil
}
func (w wingman) identities(ctx context.Context) (map[string]string, error) {
	result := map[string]string{}
	for _, role := range []struct {
		name, ca string
		usage    x509.ExtKeyUsage
	}{{"client", "client_ca", x509.ExtKeyUsageClientAuth}, {"server", "server_ca", x509.ExtKeyUsageServerAuth}} {
		data, err := w.request(ctx, "GET", "/creds/pki/"+role.name+"/cert", nil)
		if err != nil {
			return nil, err
		}
		certificates, err := certificateChain(data)
		if err != nil {
			return nil, err
		}
		rootsPEM, err := w.request(ctx, "GET", "/trust/pki/"+role.ca, nil)
		if err != nil {
			return nil, err
		}
		roots := x509.NewCertPool()
		if !roots.AppendCertsFromPEM(rootsPEM) {
			return nil, errors.New("invalid identity trust bundle")
		}
		intermediates := x509.NewCertPool()
		for _, c := range certificates[1:] {
			intermediates.AddCert(c)
		}
		if _, err := certificates[0].Verify(x509.VerifyOptions{Roots: roots, Intermediates: intermediates, KeyUsages: []x509.ExtKeyUsage{role.usage}}); err != nil {
			return nil, errors.New("untrusted pod identity chain")
		}
		fingerprint := sha256.Sum256(certificates[0].Raw)
		result[role.name+"_identity_sha256"] = hex.EncodeToString(fingerprint[:])
	}
	return result, nil
}

// Probe modes emit only public fingerprints and a denial status. No key is printed.
func probe(ctx context.Context, mode string) error {
	if mode != "probe-authorized" && mode != "probe-denied" {
		return errors.New("unknown probe mode")
	}
	ctx, cancel := context.WithTimeout(ctx, 2*time.Minute)
	defer cancel()
	w := wingman{"http://127.0.0.1:8070", &http.Client{Timeout: 30 * time.Second, Transport: &http.Transport{Proxy: nil}, CheckRedirect: func(*http.Request, []*http.Request) error { return errors.New("Wingman redirect rejected") }}}
	for w.ready(ctx) != nil {
		select {
		case <-ctx.Done():
			return errors.New("Wingman readiness deadline exceeded")
		case <-time.After(time.Second):
		}
	}
	identities, err := w.identities(ctx)
	if err != nil {
		return err
	}
	cert, err := readMaterial("/material/certificate.pem")
	if err != nil {
		return err
	}
	locationPath := os.Getenv("PROBE_LOCATION_FILE")
	if locationPath == "" {
		locationPath = "/material/encrypted-location"
	}
	if locationPath != "/material/encrypted-location" && locationPath != "/material/encrypted-location-xcsh" {
		return errors.New("invalid probe material path")
	}
	location, err := readMaterial(locationPath)
	if err != nil {
		return err
	}
	_, fingerprint, err := w.certificate(ctx, cert, strings.TrimSpace(string(location)), os.Getenv("TLS_HOSTNAME"))
	if mode == "probe-denied" {
		var status wingmanStatusError
		if !errors.As(err, &status) || int(status) != http.StatusForbidden {
			return errors.New("unselected probe did not receive HTTP 403")
		}
		return json.NewEncoder(os.Stdout).Encode(struct {
			Denied     bool              `json:"denied"`
			Status     int               `json:"http_status"`
			Identities map[string]string `json:"identities"`
		}{true, 403, identities})
	}
	if err != nil {
		return err
	}
	for _, id := range identities {
		if id == fingerprint {
			return errors.New("pod identity reused application TLS certificate")
		}
	}
	return json.NewEncoder(os.Stdout).Encode(struct {
		Fingerprint string            `json:"certificate_sha256"`
		Identities  map[string]string `json:"identities"`
	}{fingerprint, identities})
}
