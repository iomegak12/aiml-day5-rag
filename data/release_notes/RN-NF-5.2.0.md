---
doc_id: "RN-NF-5.2.0"
doc_type: "release_note"
product: "Nimbus NF-300"
version: "5.2.0"
version_family: "5.2"
---
# Nimbus NF-300 release 5.2.0: release notes

## Overview
Nimbus NF-300 5.2.0 introduces asymmetric session hashing, chunked signature activation, and improved VPN policy parsing. The release focuses on session-table scaling, faster and safer threat-database activation, and more predictable IPsec/IKEv2 policy handling during configuration changes. It also includes targeted fixes for phase 2 negotiation resets, large signature bundle updates, and configuration replay during upgrade from 5.0.x. Operators should review HA and inspection behavior after upgrade, as 5.2.0 still includes known issues affecting outbound TLS inspection and session-table distribution under asymmetric routing.

## New features
### Asymmetric session hashing
This release adds asymmetric session hashing to improve session placement when return traffic does not follow the forward path. The feature is intended for environments with asymmetric routing and concentrated prefix traffic, where a single chassis or node can otherwise carry a disproportionate share of sessions. Enable it only after confirming your routing design and session-table capacity, then validate distribution with show session table summary.

### Chunked signature activation
Threat signature activation now occurs in smaller chunks rather than as a single large update transaction. This reduces the chance of packet-processing stalls during activation of large threat database bundles and improves update resilience on busy systems. No configuration syntax changes are required, but operators should still schedule signature updates during a maintenance window when possible.

### Improved VPN policy parsing
VPN policy parsing has been tightened to handle more complex IPsec/IKEv2 policy definitions consistently during commit and replay. This reduces the likelihood of phase 2 negotiation failures caused by mismatched proposal selection and improves recovery when policies are edited or restored from configuration backups. Review existing crypto ikev2 and policy objects after upgrade if you use multiple DH groups, proposal sets, or imported templates.

## Resolved issues
- KB-3102: Nimbus NF-300 5.1.3 and 5.1.5: IKEv2 phase 2 resets when responder selects a different DH group than the initiator (%IKEV2-3-PROPOSAL_MISMATCH)
- KB-3105: Nimbus NF-300 5.1.5: threat database update can stall packet processing when signature bundle exceeds 128 MB (%TP-4-SIGNATURE_STALL)
- KB-3111: Nimbus NF-300 5.1.3 and 5.1.5: upgrade from 5.0.x may reset configuration objects if checkpoint replay exceeds 4,096 entries (%UPGRADE-4-REPLAY_CURSOR)

## Known issues
- KB-3106: Nimbus NF-300 5.2.0 and 5.2.2: outbound TLS sessions intermittently bypass inspection after certificate cache eviction. Workaround: Increase the certificate cache size so eviction stays below 1,000 entries per hour, or disable outbound inspection for the affected server group until a fix is applied. Restarting SSL inspection clears the stale pointers temporarily.
- KB-3109: Nimbus NF-300 5.2.0 uneven session-table distribution with asymmetric routing on concentrated /24 traffic. Workaround: Disable asymmetric routing handling for the affected policy set, or split the large prefix into smaller policy groups so sessions are distributed more evenly. Continue monitoring the busiest shard and keep occupancy below 75 percent until a software fix is available.
config
session-table asymmetric-routing disable
commit
- KB-3110: Nimbus NF-300 5.2.0 session-table imbalance after enabling asymmetric routing on large-prefix traffic. Workaround: Disable asymmetric routing handling for the affected policy set, or break the large prefix into smaller policy groups so the sessions distribute more evenly. Monitor the hottest shard and keep occupancy below 75 percent until a software fix is available.

## Compatibility
Nimbus NF-300 5.2.0 supports upgrade from the 5.1.x train, including 5.1.3 and 5.1.5, and from 5.0.x when the upgrade path is handled through the supported staged procedure. Hardware support remains limited to the NF-300 platform family; no new platform requirements are introduced in this release. Existing IPsec/IKEv2, HA, SSL inspection, and threat-prevention configurations are retained, but operators should expect changed runtime behavior from asymmetric session hashing and improved VPN policy parsing. After upgrade, verify interoperability with peer devices that enforce strict IKEv2 proposal matching or that rely on symmetric session stickiness, and confirm that inspection policies still behave as intended for TLS traffic.

## Upgrade notes
Supported direct upgrade path from 5.1.5. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export any VPN, HA, and threat-prevention artifacts before starting the upgrade.
2. Verify the 5.2.0 image checksum and confirm adequate flash capacity for the staged installation.
3. Schedule a maintenance window and, if the deployment is in HA, place the peer in standby before upgrading the active node.
4. Install the 5.2.0 image, reboot, and allow configuration replay and signature database initialization to complete.
5. After the system returns to service, run show ha status, show crypto ikev2 sa, and show session table summary to confirm expected operation.
6. Validate representative VPN tunnels, SSL inspection policy behavior, and threat signature updates before returning the device to production traffic.
