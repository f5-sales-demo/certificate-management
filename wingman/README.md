# Wingman runtime scaffold

Deployment and qualification are tracked in [Certificate Management #51](https://github.com/f5-sales-demo/certificate-management/issues/51). This scaffold is separate from the
25 existing certificate examples. `contract.json` owns naming and resource ownership; bootstrap
and runtime have independent private Terraform states. The existing named-certificate owner
alone owns the opt-in pool and route.

The local implementation is awaiting provider release, immutable image publication, and live
qualification. The provider baseline pins must advance to the new qualified release before deployment.
Application tests use protocol fixtures; they do not substitute for a real Wingman sidecar.

Run `go test -race ./...` and `go vet ./...` from `app/`. Governed CI uses the Go image digest in
`app/build-image.txt` and publishes Linux amd64/arm64 images with source provenance. Receipt-only
updates do not trigger a new image. Runtime rejects floating image tags.
