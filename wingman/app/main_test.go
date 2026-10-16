package main

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"math/big"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func fixture(t *testing.T) ([]byte, []byte) {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	cert := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "tls.example.com"}, DNSNames: []string{"tls.example.com"}, NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour), KeyUsage: x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
	der, err := x509.CreateCertificate(rand.Reader, cert, cert, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	return pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
}

func TestCertificateAndPublicResponse(t *testing.T) {
	cert, key := fixture(t)
	unseals := 0
	sidecar := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/status" {
			_, _ = w.Write([]byte("READY\n"))
			return
		}
		if r.URL.Path != "/secret/unseal" || r.Method != "POST" || r.Header.Get("Content-Type") != "application/json" {
			t.Error("unexpected request")
			http.Error(w, "bad", 400)
			return
		}
		var body map[string]string
		if json.NewDecoder(r.Body).Decode(&body) != nil || body["type"] != "blindfold" || body["location"] != "string:///encrypted" {
			t.Error("incorrect unseal contract")
		}
		unseals++
		_, _ = w.Write([]byte(base64.StdEncoding.EncodeToString(key)))
	}))
	defer sidecar.Close()
	w := wingman{sidecar.URL, sidecar.Client()}
	pair, fingerprint, err := w.certificate(context.Background(), cert, "string:///encrypted", "tls.example.com")
	if err != nil || len(pair.Certificate) != 1 || len(fingerprint) != 64 || unseals != 1 {
		t.Fatalf("TLS setup failed: %v", err)
	}
	response := httptest.NewRecorder()
	handler(w, fingerprint).ServeHTTP(response, httptest.NewRequest("GET", "/wingman/get", nil))
	if response.Code != 200 || strings.Contains(response.Body.String(), string(key)) || !strings.Contains(response.Body.String(), fingerprint) {
		t.Fatal("unsafe or incomplete public response")
	}
	for _, path := range []string{"/secret/unseal", "/creds/pki/server/key", "/status"} {
		response := httptest.NewRecorder()
		handler(w, fingerprint).ServeHTTP(response, httptest.NewRequest("GET", path, nil))
		if response.Code != 404 {
			t.Fatal("sidecar API exposed")
		}
	}
}

func TestNotReadyDoesNotUnseal(t *testing.T) {
	cert, _ := fixture(t)
	for _, status := range []string{"INITIALIZING", "DEGRADED", "HALTED", "READY extra", ""} {
		t.Run(status, func(t *testing.T) {
			sidecar := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path != "/status" {
					t.Error("unseal attempted before READY")
				}
				_, _ = w.Write([]byte(status))
			}))
			defer sidecar.Close()
			w := wingman{sidecar.URL, sidecar.Client()}
			if _, _, err := w.certificate(context.Background(), cert, "string:///encrypted", "tls.example.com"); err == nil {
				t.Fatal("accepted non-READY status")
			}
			response := httptest.NewRecorder()
			handler(w, "public-fingerprint").ServeHTTP(response, httptest.NewRequest("GET", "/readyz", nil))
			if response.Code != 503 {
				t.Fatal("reported readiness without READY")
			}
		})
	}
}

func TestUnsealFailures(t *testing.T) {
	cert, key := fixture(t)
	_, wrongKey := fixture(t)
	for _, tc := range []struct {
		name       string
		code       int
		body, host string
	}{
		{"denied", 403, "PRIVATE ERROR MUST NOT ESCAPE", "tls.example.com"},
		{"invalid-base64", 200, "!!", "tls.example.com"},
		{"mismatched-key", 200, base64.StdEncoding.EncodeToString(wrongKey), "tls.example.com"},
		{"wrong-host", 200, base64.StdEncoding.EncodeToString(key), "wrong.example.com"},
		{"oversized", 200, strings.Repeat("x", maxMaterial+1), "tls.example.com"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			calls := 0
			sidecar := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path == "/status" {
					_, _ = w.Write([]byte("READY"))
					return
				}
				calls++
				w.WriteHeader(tc.code)
				_, _ = w.Write([]byte(tc.body))
			}))
			defer sidecar.Close()
			w := wingman{sidecar.URL, sidecar.Client()}
			if _, _, err := w.certificate(context.Background(), cert, "string:///encrypted", tc.host); err == nil || strings.Contains(err.Error(), tc.body) {
				t.Fatal("unsafe or missing failure")
			}
			if calls != 1 {
				t.Fatal("unseal retried")
			}
		})
	}
}

func TestResponseReadFailureDoesNotExposeBody(t *testing.T) {
	sidecar := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Length", "100")
		_, _ = w.Write([]byte("PRIVATE RESPONSE"))
		w.(http.Flusher).Flush()
		<-r.Context().Done()
	}))
	defer sidecar.Close()
	client := sidecar.Client()
	client.Timeout = 50 * time.Millisecond
	w := wingman{sidecar.URL, client}
	_, err := w.request(context.Background(), "GET", "/trust/pki/client_ca", nil)
	if err == nil || err.Error() != "Wingman /trust/pki/client_ca response read failed" {
		t.Fatalf("read failure was not distinguished safely: %v", err)
	}
}

func TestResponseMaterialLimitIsDistinct(t *testing.T) {
	sidecar := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(strings.Repeat("x", maxMaterial+1)))
	}))
	defer sidecar.Close()
	w := wingman{sidecar.URL, sidecar.Client()}
	_, err := w.request(context.Background(), "POST", "/secret/unseal", nil)
	if err == nil || err.Error() != "Wingman /secret/unseal response exceeds material limit" {
		t.Fatalf("material limit was not distinguished safely: %v", err)
	}
}
