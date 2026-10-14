# Current Certificate Management qualification

Tracking: [Certificate Management #39](https://github.com/f5-sales-demo/certificate-management/issues/39)
Governed delivery: [docs-control #2496](https://github.com/f5-sales-demo/docs-control/issues/2496)

- [x] Resolve current publications and verify both platform artifacts, digests and source commits.
- [x] Remove exact provider pins and initialize with upgrade before new plans.
- [x] Validate all 25 configurations on Ubuntu and macOS; confirm 25 installed certificate nodes across 14 resource types.
- [x] Replay 16 supported encrypted lifecycles per platform, including metadata stability, renewal and inline list changes.
- [x] Replay personalized Terraform and xcsh reader commands on both platforms with trusted served TLS before and after renewal.
- [x] Verify named/inline HTTPS and named-origin mTLS serving separately from generic API acceptance.
- [x] Back up and lock retained owner state, confirm tenant/resource identities, and require two independent zero-change plans with unchanged material and ownership.
- [x] Reassess nine reference paths. Connector readback drops TLS settings; BIG-IP reads return 501; NFV inputs remain unavailable within scope. Three stateful attempts return 500 and remain failures, including an HTTP-only control.
- [x] Confirm typed disposable absence twice. Raw attempts, state, plans and credentials remain private.
- [x] Validate current builder customization, clipboard behavior, downloads and public endpoints.
- [ ] Deliver linked content and governance PRs through CI and merge.
- [ ] Verify the current managed manifest and every downstream caller blob.
- [ ] Verify published pages, copied commands, downloads, receipts and fresh publication resolution.

Current evidence is under `docs/assets/current-*.json`. Historical receipts remain unchanged.
Automatic checks qualify schema, builder customization, downloads and endpoint health without tenant credentials. They do not claim fresh live encryption qualification.
