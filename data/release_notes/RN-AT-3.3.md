---
doc_id: "RN-AT-3.3"
doc_type: "release_note"
product: "Atlas SD-WAN"
version: "3.3"
version_family: "3.3"
---
# Atlas SD-WAN release 3.3: release notes

## Overview
Atlas SD-WAN 3.3 expands operational visibility and tightens control-plane validation. The release adds richer flow-history reporting, improved LTE handoff telemetry for field troubleshooting, and stricter certificate validation on orchestrator and edge control connections. In addition to these feature updates, 3.3 corrects IPSec proposal negotiation for peers that require AES-GCM with SHA-384 on the same proposal and preserves per-interface LTE tunnel MTU during migration when a nondefault APN is used. The release continues to focus on overlay tunnel stability, reporting accuracy, and predictable upgrades from the 3.2 train.

## New features
### Expanded flow-history reporting
Flow-history reporting now retains and exposes a broader set of per-flow attributes for post-event analysis, including tunnel selection, application classification, and SLA-class decisions. This improves troubleshooting of application-aware routing and overlay path changes after a transient outage. Existing report definitions continue to work, but operators may need to review retention and export settings because larger datasets can increase report generation time.

### LTE handoff telemetry
Atlas SD-WAN 3.3 adds detailed telemetry for LTE handoff events on the edge, including modem state transitions, carrier acquisition timing, and tunnel recovery markers. The new data is available in edge operational output and reporting so TAC can correlate handoff activity with tunnel loss or latency spikes. No configuration changes are required, but operators should ensure their monitoring systems are prepared to ingest the additional event fields.

### Certificate validation tightening
The orchestrator and edge now enforce stricter certificate checks during control-plane authentication. Validation includes closer matching of certificate identity, validity period, and chain requirements, which reduces acceptance of malformed or weakly trusted certificates. Before upgrade, verify that all device and orchestrator certificates are current and that any custom trust chain is complete, because previously tolerated certificate defects may now block enrollment or policy synchronization.

## Resolved issues
- KB-5106: Atlas SD-WAN 3.2: IPSec tunnel negotiation fails with peers that require AES-GCM and SHA-384 on the same proposal (%IKE-3-PROPOSAL-MISMATCH)
- KB-5110: Atlas SD-WAN 3.2: migration drops per-interface LTE tunnel MTU when the profile uses a nondefault APN (%UPG-5-MTU-MIGRATE)

## Known issues
- KB-5107: Atlas SD-WAN 3.3: reporting jobs consume excessive CPU when flow history exceeds 7 days. Workaround: Reduce the flow-history retention window to 3 to 5 days or split reporting into narrower 24-hour jobs. If the dataset must stay large, run reports during a low-change maintenance window so policy updates are not contending with the same CPU cores.
- KB-5112: Atlas SD-WAN 3.3: edge CPU spikes during LTE handoff when both modems are enabled. Workaround: Stagger the modem failover by disabling the standby modem during maintenance windows, or raise the LTE handoff debounce to 5 seconds so the state machines do not oscillate on transient signal loss. If possible, avoid pushing policy changes during a carrier switchover.

## Compatibility
Atlas SD-WAN 3.3 supports upgrade from 3.2 in-place for the orchestrator and edges, including platforms that use LTE transport and application-aware routing policies. Existing overlay tunnels, SLA classes, and policy constructs are retained, but certificate-based control connections may require remediation if certificates are expired, missing intermediates, or use mismatched identities. The release remains interoperable with 3.2 peers during a staged upgrade, although mixed-version reporting may show different levels of flow detail until all components are upgraded. The LTE migration fix preserves per-interface tunnel MTU values for profiles that use a nondefault APN; no manual configuration change is required unless a site previously worked around the issue. Hardware support follows the existing 3.2 platform matrix.

## Upgrade notes
Supported direct upgrade path from 3.2. Back up the configuration before upgrading and review the known issues above.

1. Back up the orchestrator configuration, edge templates, certificates, and any local edge exports before starting the upgrade.
2. Verify the 3.3 images on the orchestrator and edge repositories, and confirm the checksums match the published package values.
3. Schedule a maintenance window large enough to upgrade the orchestrator first, then the edges in staged groups so policy push and reporting can be validated incrementally.
4. Upgrade the orchestrator to 3.3, confirm policy compilation succeeds, and verify that certificate validation passes for all managed edges.
5. Upgrade a small edge batch, then confirm tunnel state, application-aware routing, LTE transport, and report generation with commands such as 'show sdwan tunnels' and 'show app-route sla-class'.
6. After all sites are upgraded, review logs and counters for certificate failures, tunnel re-establishment, and LTE handoff events, and document any residual reporting CPU impact if flow-history retention is set above 7 days.
