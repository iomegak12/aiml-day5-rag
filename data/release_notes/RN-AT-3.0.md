---
doc_id: "RN-AT-3.0"
doc_type: "release_note"
product: "Atlas SD-WAN"
version: "3.0"
version_family: "3.0"
---
# Atlas SD-WAN release 3.0: release notes

## Overview
Atlas SD-WAN release 3.0 focuses on control-plane scalability, certificate handling, and transport stability. The policy compiler has been reworked to reduce compilation time and improve the consistency of generated forwarding policy across orchestrator pushes. Trust-store processing has also been tightened so certificate-chain validation behaves more predictably during controller and edge onboarding. In addition, SLA probe traffic now uses a separate queue from bulk data-plane traffic, which improves probe accuracy under load and reduces tunnel instability in congested sites.

## New features
### Policy compiler overhaul
The policy compiler has been redesigned to improve scalability when compiling larger routing and application-aware policies. This change reduces the time required for orchestrator policy push and makes generated policy behavior more consistent across edges. Existing policy objects are supported, but customers should review any automation that parses compiler status or timing output.

### Improved trust-store handling
Trust-store processing now validates certificate chains with clearer precedence for local trust anchors, intermediate certificates, and revocation state. This improves reliability during orchestrator-to-edge enrollment and during certificate rotation on deployed systems. Administrators should verify that imported CA bundles and edge certificates remain aligned with their existing trust model before upgrade.

### SLA probe queue separation
SLA probe traffic now uses a queue separate from the bulk data-plane forwarding queue. This isolates latency and loss measurements from burst traffic, improving probe fidelity and reducing false brownout indications on busy links. No new configuration is required, but operators should expect slightly different probe-loss characteristics under heavy congestion.

## Resolved issues
- KB-5105: Atlas SD-WAN 2.9: overlay tunnel flaps when SLA probes share the data-plane queue with burst traffic (%SDWAN-4-SLA-DOWN)

## Known issues
- KB-5103: Atlas SD-WAN 3.0: policy push hangs when a route-map contains more than 256 entries. Workaround: Split large route-maps into two smaller maps of 256 entries or fewer and reference them from separate policy objects. If the existing tenant already has a larger map, remove 10 to 20 entries, push the change, and then re-add the remainder in a second commit.

## Compatibility
Atlas SD-WAN 3.0 supports in-place upgrades from 2.9 on supported orchestrator and edge platforms. Hardware support remains unchanged for the 2.9 train, and existing overlay tunnels, application-aware routing, SLA classes, LTE transports, and reporting policies are retained. Interoperability with 2.9 edges and orchestrators is preserved during staged rollout, but new policy compilation behavior and trust-store validation should be verified in mixed-version deployments. Any external automation that depends on policy compiler output, certificate-import workflows, or SLA probe counters should be validated before broad deployment.

## Upgrade notes
Supported direct upgrade path from 2.9. Back up the configuration before upgrading and review the known issues above.

1. Back up the orchestrator configuration, edge inventory, certificates, and any exported policy packages before starting the upgrade.
2. Verify the 3.0 images on the orchestrator and edge repositories, and confirm checksums match the published software bundle.
3. Schedule a maintenance window large enough to complete orchestrator upgrade, policy resynchronization, and edge image rollout with minimal traffic impact.
4. Upgrade the orchestrator first, then upgrade a staged set of representative edges and confirm policy push, tunnel state, and certificate status before expanding the rollout.
5. After each stage, run post-upgrade checks such as show sdwan tunnels, show app-route sla-class, and certificate status verification to confirm policy propagation and transport health.
6. Once all sites are upgraded, monitor tunnel stability, SLA probe behavior, and policy push completion for at least one full business cycle before closing the change.
