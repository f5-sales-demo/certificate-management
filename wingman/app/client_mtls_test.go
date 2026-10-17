package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/pem"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
)

func TestForwardedIdentity(t *testing.T) {
	cert, _ := fixture(t)
	block, _ := pem.Decode(cert)
	sum := sha256.Sum256(block.Bytes)
	hash := hex.EncodeToString(sum[:])
	valid := `Hash=` + hash + `;Cert="` + url.PathEscape(string(cert)) + `";Chain="` + url.PathEscape(string(cert)) + `"`
	for _, tc := range []struct {
		name   string
		values []string
		want   string
		bad    bool
	}{
		{"absent", nil, "", false}, {"certificate", []string{valid}, hash, false},
		{"forged hash", []string{"Hash=" + hash}, "", true},
		{"duplicate headers", []string{valid, valid}, "", true},
		{"duplicate field", []string{valid + `;Hash=` + hash}, "", true},
		{"multiple hops", []string{valid + "," + valid}, "", true},
		{"wrong hash", []string{strings.Replace(valid, hash, strings.Repeat("0", 64), 1)}, "", true},
		{"malformed", []string{`Cert="%zz"`}, "", true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			r := httptest.NewRequest("GET", "/mtls/identity", nil)
			for _, v := range tc.values {
				r.Header.Add("X-Forwarded-Client-Cert", v)
			}
			got, err := forwardedFingerprint(r)
			if (err != nil) != tc.bad || got != tc.want {
				t.Fatalf("got %q, error %v", got, err)
			}
		})
	}
}

func TestClientRoutes(t *testing.T) {
	sidecar := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write([]byte("READY")) }))
	defer sidecar.Close()
	h := handler(wingman{sidecar.URL, sidecar.Client()}, "origin-fingerprint")
	cert, _ := fixture(t)
	block, _ := pem.Decode(cert)
	sum := sha256.Sum256(block.Bytes)
	hash := hex.EncodeToString(sum[:])
	xfcc := `Hash=` + hash + `;Cert="` + url.PathEscape(string(cert)) + `";Chain="` + url.PathEscape(string(cert)) + `"`
	for _, method := range []string{"GET", "POST", "PUT", "PATCH"} {
		path := "/mtls/write"
		if method == "GET" {
			path = "/mtls/identity"
		}
		for _, authenticated := range []bool{false, true} {
			r := httptest.NewRequest(method, path+"?challenge=fresh-123", strings.NewReader("must-not-be-echoed"))
			if authenticated {
				r.Header.Set("X-Forwarded-Client-Cert", xfcc)
			}
			w := httptest.NewRecorder()
			h.ServeHTTP(w, r)
			want := 200
			if method != "GET" && !authenticated {
				want = 403
			}
			if w.Code != want {
				t.Fatalf("%s authenticated=%v status=%d", method, authenticated, w.Code)
			}
			if want == 200 && (!strings.Contains(w.Body.String(), "fresh-123") || strings.Contains(w.Body.String(), "must-not-be-echoed") || strings.Contains(w.Body.String(), "BEGIN CERTIFICATE")) {
				t.Fatal("unsafe or incomplete response")
			}
			if authenticated && !strings.Contains(w.Body.String(), hash) {
				t.Fatal("forwarded fingerprint missing")
			}
		}
	}
	for _, path := range []string{"/mtls/write/extra", "/mtls/identity/extra"} {
		w := httptest.NewRecorder()
		h.ServeHTTP(w, httptest.NewRequest("POST", path, nil))
		if w.Code != 404 {
			t.Fatal("non-exact route matched")
		}
	}
}
