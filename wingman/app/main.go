// Wingman authorizes the TLS key; the application never writes plaintext to disk.
package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

const maxMaterial = 1 << 20

type wingmanStatusError int

func (s wingmanStatusError) Error() string { return fmt.Sprintf("Wingman returned HTTP %d", s) }

type wingman struct {
	base   string
	client *http.Client
}

func (w wingman) request(ctx context.Context, method, path string, body []byte) ([]byte, error) {
	req, err := http.NewRequestWithContext(ctx, method, w.base+path, bytes.NewReader(body))
	if err != nil {
		return nil, errors.New("invalid Wingman request")
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := w.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("Wingman %s unavailable", path)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, wingmanStatusError(resp.StatusCode)
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, maxMaterial+1))
	if err != nil {
		return nil, fmt.Errorf("Wingman %s response read failed", path)
	}
	if len(data) > maxMaterial {
		return nil, fmt.Errorf("Wingman %s response exceeds material limit", path)
	}
	return data, nil
}

func (w wingman) ready(ctx context.Context) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	data, err := w.request(ctx, http.MethodGet, "/status", nil)
	if err != nil {
		return err
	}
	if strings.TrimSpace(string(data)) != "READY" {
		return errors.New("Wingman is not READY")
	}
	return nil
}

func (w wingman) certificate(ctx context.Context, certPEM []byte, location string, hostname string) (tls.Certificate, string, error) {
	if !strings.HasPrefix(location, "string:///") {
		return tls.Certificate{}, "", errors.New("expected encrypted string location")
	}
	if err := w.ready(ctx); err != nil {
		return tls.Certificate{}, "", err
	}
	body, _ := json.Marshal(struct {
		Type     string `json:"type"`
		Location string `json:"location"`
	}{"blindfold", location})
	data, err := w.request(ctx, http.MethodPost, "/secret/unseal", body)
	if err != nil {
		return tls.Certificate{}, "", err
	}
	defer clear(data)
	key, err := base64.StdEncoding.DecodeString(strings.TrimSpace(string(data)))
	if err != nil {
		clear(key)
		return tls.Certificate{}, "", errors.New("invalid unseal encoding")
	}
	defer clear(key)
	pair, err := tls.X509KeyPair(certPEM, key)
	if err != nil {
		return tls.Certificate{}, "", errors.New("unsealed key does not match public certificate")
	}
	leaf, err := x509.ParseCertificate(pair.Certificate[0])
	if err != nil {
		return tls.Certificate{}, "", errors.New("invalid public certificate")
	}
	if err := leaf.VerifyHostname(hostname); err != nil {
		return tls.Certificate{}, "", errors.New("application certificate hostname mismatch")
	}
	now := time.Now()
	if now.Before(leaf.NotBefore) || !now.Before(leaf.NotAfter) {
		return tls.Certificate{}, "", errors.New("application certificate is outside its validity period")
	}
	pair.Leaf = leaf
	sum := sha256.Sum256(leaf.Raw)
	return pair, hex.EncodeToString(sum[:]), nil
}

func handler(w wingman, fingerprint string) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /readyz", func(rw http.ResponseWriter, r *http.Request) {
		if w.ready(r.Context()) != nil {
			http.Error(rw, "not ready", http.StatusServiceUnavailable)
			return
		}
		rw.Header().Set("Content-Type", "text/plain")
		_, _ = rw.Write([]byte("READY\n"))
	})
	mux.HandleFunc("GET /wingman/get", func(rw http.ResponseWriter, r *http.Request) {
		if w.ready(r.Context()) != nil {
			http.Error(rw, "not ready", http.StatusServiceUnavailable)
			return
		}
		rw.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(rw).Encode(struct {
			Example     string `json:"example"`
			Fingerprint string `json:"certificate_sha256"`
		}{"wingman-certificate", fingerprint})
	})
	return mux
}

func readMaterial(path string) ([]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, errors.New("material file unavailable")
	}
	defer f.Close()
	data, err := io.ReadAll(io.LimitReader(f, maxMaterial+1))
	if err != nil || len(data) > maxMaterial {
		return nil, errors.New("invalid material size")
	}
	return data, nil
}

func run(ctx context.Context) error {
	cert, err := readMaterial("/material/certificate.pem")
	if err != nil {
		return err
	}
	location, err := readMaterial("/material/encrypted-location")
	if err != nil {
		return err
	}
	hostname := os.Getenv("TLS_HOSTNAME")
	if hostname == "" {
		return errors.New("TLS_HOSTNAME is required")
	}
	w := wingman{"http://127.0.0.1:8070", &http.Client{
		Timeout:       30 * time.Second,
		Transport:     &http.Transport{Proxy: nil},
		CheckRedirect: func(*http.Request, []*http.Request) error { return errors.New("Wingman redirect rejected") },
	}}
	startup, cancel := context.WithTimeout(ctx, 2*time.Minute)
	defer cancel()
	for w.ready(startup) != nil {
		select {
		case <-startup.Done():
			return errors.New("Wingman readiness deadline exceeded")
		case <-time.After(time.Second):
		}
	}
	pair, fingerprint, err := w.certificate(startup, cert, strings.TrimSpace(string(location)), hostname)
	if err != nil {
		return err
	}
	server := &http.Server{
		Addr: ":8443", Handler: handler(w, fingerprint),
		TLSConfig:         &tls.Config{MinVersion: tls.VersionTLS12, Certificates: []tls.Certificate{pair}},
		ReadHeaderTimeout: 30 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second, IdleTimeout: 30 * time.Second,
	}
	go func() {
		<-ctx.Done()
		shutdown, stop := context.WithTimeout(context.Background(), 10*time.Second)
		defer stop()
		_ = server.Shutdown(shutdown)
	}()
	err = server.ListenAndServeTLS("", "")
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	var err error
	if len(os.Args) == 1 {
		err = run(ctx)
	} else {
		err = probe(ctx, os.Args[1])
	}
	if err != nil {
		log.Print(err)
		os.Exit(1)
	}
}
