---
doc_id: "RN-AT-2.8"
doc_type: "release_note"
product: "Atlas SD-WAN"
version: "2.8"
version_family: "2.8"
---
# Atlas SD-WAN release 2.8: release notes

## Overview
Atlas SD-WAN 2.8 is the first generally available release for the Atlas SD-WAN orchestrator and edge platform. It introduces initial overlay tunnel formation, basic application-aware routing, and certificate-based edge registration. This release establishes the core control-plane and data-plane workflow for site onboarding and policy delivery, with emphasis on deterministic tunnel bring-up, simple SLA-driven path selection, and certificate validation during edge enrollment. As the first release in the train, 2.8 is intended for new deployments and controlled pilot rollouts, with known limitations around short probe-loss events and certificate renewal workflows that should be considered during operations planning.

## New features
### Initial overlay tunnel formation
Atlas SD-WAN 2.8 establishes the first overlay tunnels between registered edges and the orchestrator-managed fabric. Tunnel creation uses the configured transport underlay and negotiates tunnel parameters automatically during edge bring-up. Administrators can verify tunnel state from the edge CLI with commands such as `show sdwan tunnels`.

### Basic application-aware routing
This release adds policy-driven application-aware routing based on SLA classes. Edges can classify traffic and select an overlay path using latency, loss, and jitter thresholds defined in the orchestrator policy. The initial implementation supports basic class matching and path preference, and operators can review class state with `show app-route sla-class`.

### Certificate-based edge registration
Atlas SD-WAN 2.8 introduces certificate-based edge registration for orchestrator-managed onboarding. The orchestrator validates the edge certificate chain before accepting a device into the fabric, and the edge uses its certificate identity for subsequent control-plane authentication. Administrators should ensure the full trust chain is available before attempting registration or renewal.

## Resolved issues
- None

## Known issues
- KB-5101: Atlas SD-WAN 2.8: application-aware routing marks SLA class down after a 1-second probe loss spike. Workaround: Increase the SLA probe window to at least five samples and extend the hold-down so one missed probe does not clear the class. If the link is already marginal, raise the packet-loss threshold by 1 to 2 percent to prevent unnecessary path switching.
- KB-5102: Atlas SD-WAN 2.8: orchestrator rejects edge certificate renewal when the intermediate CA is not reimported. Workaround: Reimport the full certificate chain, including the active intermediate CA, on the orchestrator before renewing the edge certificate. For large deployments, stage the new chain at least 24 hours before the old intermediate expires.
- KB-5108: Atlas SD-WAN 2.8: edge re-registration fails after certificate renewal if the orchestrator trust bundle is not updated. Workaround: Import the complete certificate chain, including the current intermediate CA, into the orchestrator before renewing the edge certificate. In large deployments, load the new chain at least 24 hours before the previous intermediate expires.

## Compatibility
Atlas SD-WAN 2.8 is the initial release in the 2.x train and does not support direct upgrade from earlier Atlas SD-WAN releases because none are defined for this train. Hardware compatibility is limited to the edge platforms and orchestrator software images validated for 2.8; mixed-version deployments are not supported beyond the staged upgrade window. Interoperability is limited to Atlas SD-WAN components running the same 2.8 feature set, and configuration created in 2.8 may require revalidation after later upgrades because certificate enrollment, tunnel policy, and application-routing behaviour are foundational in this release. Before upgrading, confirm that the orchestrator trust bundle includes the active intermediate CA used by all edges.

## Upgrade notes
Initial release in this train. Back up the configuration before upgrading and review the known issues above.

1. Back up the orchestrator configuration, edge configuration exports, and certificate trust material, including the active root and intermediate CA chain.
2. Verify the 2.8 images for the orchestrator and each edge, and confirm available storage and boot variables before starting the upgrade.
3. Schedule a maintenance window and stage the upgrade so that the orchestrator is upgraded first, followed by pilot edges and then the remaining sites.
4. After the orchestrator upgrade, import or reimport the required certificate chain and confirm that policy push and edge registration succeed.
5. Upgrade edges in batches, then validate tunnel formation and application-aware routing with `show sdwan tunnels` and `show app-route sla-class` on representative sites.
6. Complete post-upgrade checks by confirming registration status, policy synchronization, and application traffic forwarding across all planned transports.
