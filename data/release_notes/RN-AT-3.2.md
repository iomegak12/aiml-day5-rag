---
doc_id: "RN-AT-3.2"
doc_type: "release_note"
product: "Atlas SD-WAN"
version: "3.2"
version_family: "3.2"
---
# Atlas SD-WAN release 3.2: release notes

## Overview
Atlas SD-WAN 3.2 focuses on control-plane correctness and upgrade safety for orchestrator-managed overlays and edge devices. This release adds immediate route-withdrawal invalidation so application-aware routing stops using withdrawn next-hop information without waiting for cache expiry, preserves dual-SIM LTE tunnel settings during upgrade, and updates IPSec proposal negotiation handling to align with current peer policy behavior. Quality fixes in this release address two customer-impacting issues observed in 3.1: LTE tunnel MTU changes during upgrade on dual-SIM edges, and stale route selection in app-aware routing after a withdrawal event. Administrators should review IPSec and LTE transport configurations before upgrading, especially where nondefault APN profiles or stricter proposal policies are in use.

## New features
### Immediate route-withdrawal invalidation
When the orchestrator receives a route withdrawal, Atlas SD-WAN now invalidates the affected route immediately in the forwarding and application-routing caches. This prevents app-aware routing from continuing to select a withdrawn path until the normal cache aging timer expires. No configuration changes are required, but operators should expect faster failover and route-state convergence after withdrawal events.

### Dual-SIM LTE upgrade preservation
Upgrade workflows now preserve per-interface LTE tunnel settings on dual-SIM edges instead of rewriting the tunnel MTU during migration. This keeps the configured tunnel MTU intact across image changes and avoids post-upgrade traffic shifts caused by an unintended default value. Existing edge profiles do not require modification, but TAC recommends verifying LTE transport parameters after the upgrade if the edge uses dual-SIM operation.

### IPSec proposal negotiation updates
The IPSec negotiation engine has been updated to better follow proposal ordering and peer capability matching during tunnel setup. This improves interoperability with peers that present multiple transform combinations and reduces negotiation failures caused by mismatched local preference handling. Review any custom IPSec policy objects before upgrade to confirm that encryption and integrity proposals still reflect the intended peer requirements.

## Resolved issues
- KB-5104: Atlas SD-WAN 3.1: upgrade rewrites LTE tunnel MTU to 1500 on dual-SIM edges (%UPG-5-MTU-MIGRATE)
- KB-5109: Atlas SD-WAN 3.1: app-aware routing keeps using a withdrawn route until the cache ages out (%SDWAN-4-ROUTE-CACHE)

## Known issues
- KB-5106: Atlas SD-WAN 3.2: IPSec tunnel negotiation fails with peers that require AES-GCM and SHA-384 on the same proposal. Workaround: Configure the remote peer to accept an AES-GCM proposal without a separate integrity field, or use AES-CBC with SHA-384 if the peer allows alternate transforms. Verify the resulting SA proposal on both sides before restoring traffic.
- KB-5110: Atlas SD-WAN 3.2: migration drops per-interface LTE tunnel MTU when the profile uses a nondefault APN. Workaround: Reapply the tunnel MTU manually on every LTE interface that uses a custom APN after upgrading to 3.2. Validate the resulting encapsulation size with 1400-byte and 1472-byte probes before returning the circuit to production.

## Compatibility
Atlas SD-WAN 3.2 supports upgrade from 3.1 on the same orchestrator and edge hardware families supported by the 3.x train. Configuration is generally preserved across the upgrade, including overlay policy, SLA classes, certificate material, and routing policy; however, edges using dual-SIM LTE profiles should be checked after upgrade because per-interface LTE tunnel MTU values must remain as intended, especially when a nondefault APN is configured. Interoperability with IPSec peers is unchanged for standard proposal sets, but environments that depend on strict AES-GCM and SHA-384 combinations should be validated before broad rollout because proposal support remains subject to peer-specific negotiation behavior. No manual schema conversion is required, but operators should stage policy and tunnel changes through the orchestrator before upgrading all sites.

## Upgrade notes
Supported direct upgrade path from 3.1. Back up the configuration before upgrading and review the known issues above.

1. Back up the orchestrator configuration, certificate inventory, and current edge profiles, including any LTE and IPSec policy objects.
2. Verify the target 3.2 image checksum and signature on the orchestrator and on any edge software repository before scheduling the upgrade.
3. Choose a maintenance window that covers at least one full control-plane convergence cycle and, for remote sites, a backup WAN path if available.
4. Upgrade the orchestrator first, then stage the 3.2 image to a pilot group of edges; confirm the image activates cleanly before expanding the rollout.
5. After each pilot edge upgrade, run post-checks such as 'show sdwan tunnels', 'show app-route sla-class', and interface-specific LTE verification to confirm tunnel state, route selection, and MTU values.
6. Complete the remaining edge upgrades in waves, then review logs and counters for tunnel negotiation failures, route withdrawals, and policy push errors before closing the change.
