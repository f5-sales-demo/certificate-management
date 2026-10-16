package main

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/pem"
	"math/big"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestApplicationActuallyServesSharedTLS(t *testing.T) {
	cert, key := fixture(t)
	sidecar := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/status" {
			_, _ = w.Write([]byte("READY"))
			return
		}
		_, _ = w.Write([]byte(base64.StdEncoding.EncodeToString(key)))
	}))
	defer sidecar.Close()
	w := wingman{sidecar.URL, sidecar.Client()}
	pair, fingerprint, err := w.certificate(context.Background(), cert, "string:///encrypted", "tls.example.com")
	if err != nil {
		t.Fatal(err)
	}
	server := httptest.NewUnstartedServer(handler(w, fingerprint))
	server.TLS = &tls.Config{MinVersion: tls.VersionTLS12, Certificates: []tls.Certificate{pair}}
	server.StartTLS()
	defer server.Close()
	roots := x509.NewCertPool()
	roots.AppendCertsFromPEM(cert)
	client := &http.Client{Transport: &http.Transport{TLSClientConfig: &tls.Config{RootCAs: roots, ServerName: "tls.example.com", MinVersion: tls.VersionTLS12}}}
	response, err := client.Get(server.URL + "/wingman/get")
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	if response.StatusCode != 200 || !response.TLS.PeerCertificates[0].Equal(pair.Leaf) {
		t.Fatal("HTTPS did not serve the unsealed shared certificate")
	}
}

func TestPlatformIdentityTrustChains(t *testing.T) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	root := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "Synthetic identity CA"}, NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour), IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign}
	rootDER, err := x509.CreateCertificate(rand.Reader, root, root, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	rootPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: rootDER})
	leaf := &x509.Certificate{SerialNumber: big.NewInt(2), Subject: pkix.Name{CommonName: "Synthetic pod identity"}, NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour), KeyUsage: x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth, x509.ExtKeyUsageServerAuth}}
	leafDER, err := x509.CreateCertificate(rand.Reader, leaf, root, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	leafPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: leafDER})
	trusted := true
	sidecar := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/creds/pki/client/cert", "/creds/pki/server/cert":
			_, _ = w.Write(leafPEM)
		case "/trust/pki/client_ca", "/trust/pki/server_ca":
			if trusted {
				_, _ = w.Write(rootPEM)
			} else {
				_, _ = w.Write([]byte("invalid trust"))
			}
		default:
			t.Error("unexpected identity request")
		}
	}))
	defer sidecar.Close()
	w := wingman{sidecar.URL, sidecar.Client()}
	ids, err := w.identities(context.Background())
	if err != nil || len(ids) != 2 {
		t.Fatal("trusted identity rejected", err)
	}
	trusted = false
	if _, err := w.identities(context.Background()); err == nil {
		t.Fatal("untrusted identity accepted")
	}
}
