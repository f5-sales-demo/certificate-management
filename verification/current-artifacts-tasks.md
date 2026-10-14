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
- [x] Deliver source and governance changes through Certificate Management PRs #40 and #46 and docs-control PRs #2497, #2500, and #2503.
- [x] Verify the current manifest across 43 active repositories: zero mismatched changed managed files, source commit `555fca8baccf3bdb742b983709d699eac3655113`.
- [x] Verify published guides: 60 desktop/mobile clipboard comparisons, 76 source/download matches, trusted retained endpoints, and current publication resolution.

Current evidence is under `docs/assets/current-*.json`. Historical receipts remain unchanged.
Automatic checks qualify schema, builder customization, downloads and endpoint health without tenant credentials. They do not claim fresh live encryption qualification.

## Current publication follow-up

[Issue #49](https://github.com/f5-sales-demo/certificate-management/issues/49) tracks the final version advance to
provider 15.8.3 and xcsh 23.4.2 with Terraform 1.16.6 and docs-builder 1.10.1. Installed schemas match byte-for-byte on
Ubuntu and macOS. All 25 configurations and 16 terminal supported lifecycles per host passed; both native-input and
published-reader suites passed. Two initial CDN failures remain recorded alongside successful fresh diagnostic replays
after typed cleanup. The connector API drops TLS settings and the provider fails unresolved readback; three stateful
paths remain HTTP 500 failures. All 77 disposable objects were absent twice, and 201 saved plans passed
secret-containment checks. The retained owner upgrade returned two empty plans with unchanged material and identities.

The prior current receipt set is preserved byte-for-byte at its immutable source commit. `docs/assets/qualification-history/provider-v15.8.2-xcsh-v23.4.1.json` records each receipt URL and digest. Final follow-up CI, publication, and worktree cleanup evidence is recorded in issue #49.
