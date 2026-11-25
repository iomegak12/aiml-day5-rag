---
doc_id: "RN-AT-2.9"
doc_type: "release_note"
product: "Atlas SD-WAN"
version: "2.9"
version_family: "2.9"
---
# Atlas SD-WAN release 2.9: release notes

## Overview
Atlas SD-WAN 2.9 adds three operational improvements focused on routing stability, transport flexibility, and safer policy rollout. The release introduces configurable hold-down behaviour for SLA classes, support for LTE transport profiles on edges, and a preflight validation step before policy push so common deployment errors are caught earlier. This release also includes fixes for SLA class state handling during brief probe loss, and for certificate renewal and edge re-registration when trust material is updated. Operators should review certificate chain and CRL hygiene before upgrade, since policy push protections in this train are sensitive to stale revocation data.

## New features
### SLA class hold-down tuning
This release adds hold-down parameters for SLA classes so brief probe-loss spikes do not immediately force application-aware routing to declare a path down. The tuning applies to class state transitions and lets operators align failover behaviour with their probe interval and jitter tolerance. Existing SLA class definitions continue to work, but administrators should review any automation that assumes immediate down transitions.

### LTE transport profile support
Atlas SD-WAN 2.9 introduces LTE transport profiles for edges that use cellular uplinks. The profile allows transport-specific settings such as MTU, preferred APN parameters, and link handling to be applied consistently from the orchestrator or the edge CLI. Existing Ethernet and broadband transports are unchanged, but LTE-connected sites should be validated after upgrade to confirm tunnel behaviour and carrier-specific settings.

### Policy push preflight validation
Before a policy push is committed, the orchestrator now performs preflight validation of referenced objects, certificate state, and deployability conditions. This reduces failed pushes caused by missing dependencies or incomplete trust updates and provides earlier feedback to operators. Preflight validation does not change policy intent, but it can block a push until the underlying configuration issue is corrected.

## Resolved issues
- KB-5101: Atlas SD-WAN 2.8: application-aware routing marks SLA class down after a 1-second probe loss spike (%SDWAN-4-SLA-DOWN)
- KB-5102: Atlas SD-WAN 2.8: orchestrator rejects edge certificate renewal when the intermediate CA is not reimported (%PKI-3-CHAIN-UNTRUSTED)
- KB-5108: Atlas SD-WAN 2.8: edge re-registration fails after certificate renewal if the orchestrator trust bundle is not updated (%PKI-3-CHAIN-UNTRUSTED)

## Known issues
- KB-5105: Atlas SD-WAN 2.9: overlay tunnel flaps when SLA probes share the data-plane queue with burst traffic. Workaround: Place SLA probes into a high-priority queue or reserve at least 10 percent bandwidth for control traffic on busy links. If shaping is already enabled, lower the bulk-traffic class to 60 to 70 percent so probes are not delayed behind large data bursts.
- KB-5111: Atlas SD-WAN 2.9: orchestrator blocks policy push when the CRL update is older than 24 hours. Workaround: Refresh the CRL on the orchestrator before the 24-hour mark, or align the CA publication interval to 12 to 18 hours so the push window never overlaps the hard-expiry check. Confirm the updated CRL timestamp before retrying the policy push.

## Compatibility
Atlas SD-WAN 2.9 supports in-service upgrade from 2.8 on supported orchestrator and edge hardware. The release is interoperable with 2.8 peers during a rolling upgrade, but the new SLA hold-down, LTE transport profile, and preflight validation behaviours only take effect after both orchestrator and edge software are on 2.9. Configuration exported from 2.8 remains valid, although sites using LTE should review transport profiles and any certificate workflows that depend on intermediate CA import or trust bundle updates. Because policy push validation depends on current revocation data, ensure CRL distribution is functioning before upgrading clustered orchestrators.

## Upgrade notes
Supported direct upgrade path from 2.8. Back up the configuration before upgrading and review the known issues above.

1. Back up the orchestrator configuration, edge inventory, certificate bundles, and current policy set before starting the upgrade.
2. Verify the 2.9 software image checksum on the orchestrator and confirm that the image has been staged to all target edges.
3. Schedule a maintenance window and upgrade the orchestrator first, then upgrade edges in batches so overlay tunnels remain controlled during the transition.
4. After each batch, confirm tunnel health and routing state with show sdwan tunnels and show app-route sla-class, and verify LTE uplinks if they are in use.
5. Check certificate status, trust bundle contents, and CRL freshness before pushing policy, then run a staged policy push to validate preflight behaviour.
6. Perform final post-checks for application-aware routing, tunnel stability, and edge re-registration where certificate renewal is part of the rollout.
