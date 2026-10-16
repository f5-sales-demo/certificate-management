# Wingman runtime scaffold

Deployment and qualification are tracked in [Certificate Management #58](https://github.com/f5-sales-demo/certificate-management/issues/58). This scaffold is separate from the
25 existing certificate examples. `contract.json` owns naming and resource ownership; bootstrap
and runtime have independent private Terraform states. The existing named-certificate owner
alone owns the opt-in pool and route.

The published provider 15.9.0 and existing certificate lifecycles are qualified on Ubuntu and macOS.
The immutable application passed fresh sidecar injection, both authorized ciphertext sources, HTTP 403
denial, trusted identities, backend and public TLS, and restart checks. All three owner states have
empty follow-up plans; probes were absent twice and the scoped credential was revoked.
[The qualification record](../docs/assets/wingman-acceptance.json) records the selected artifacts and
preserves first-run failures alongside the passing runs.
Application tests use protocol fixtures; they do not substitute for a real Wingman sidecar.

Run `go test -race ./...` and `go vet ./...` from `app/`. Governed CI uses the Go image digest in
`app/build-image.txt` and publishes Linux amd64/arm64 images with source provenance. Receipt-only
updates do not trigger a new image. Runtime rejects floating image tags.
