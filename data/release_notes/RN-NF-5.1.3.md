---
doc_id: "RN-NF-5.1.3"
doc_type: "release_note"
product: "Nimbus NF-300"
version: "5.1.3"
version_family: "5.1"
---
# Nimbus NF-300 release 5.1.3: release notes

## Overview
Nimbus NF-300 release 5.1.3 introduces broader IPsec transform support, configuration checkpoint migration improvements, and additional session-table instrumentation. The release also includes a fix for child SA renegotiation failures observed after a PFS group change when rekey traffic is active. This train update is focused on VPN stability, upgrade resilience, and operational visibility for session handling. Administrators should review existing VPN proposals and checkpoint usage before upgrade, particularly in environments that rely on large configuration histories or frequent IPsec rekey events.

## New features
### Expanded VPN transform support
This release expands the set of accepted IPsec/IKEv2 transform combinations for tunnel negotiation. The change is intended to improve interoperability with peers that require non-default encryption, integrity, or Diffie-Hellman selections, while preserving existing tunnel policy behavior. Review configured phase 1 and phase 2 proposals after upgrade to confirm that the selected transform sets match your peer requirements.

### Configuration checkpoint migration
Release 5.1.3 adds checkpoint migration logic for configurations created on earlier 5.0.x and 5.1.x software. The migration process preserves supported objects during upgrade and reduces manual re-entry for common firewall, VPN, and policy settings. Environments with large checkpoint histories should plan the upgrade window carefully and verify checkpoint replay results after the system comes back online.

### Session-table instrumentation
This release adds session-table instrumentation to improve operational visibility into active flows, aging behavior, and table pressure. The new counters and summary output help identify whether packet drops or session churn are associated with resource exhaustion, policy changes, or asymmetric forwarding. Use the updated session summary commands after upgrade to validate steady-state behavior under normal and peak load.

## Resolved issues
- KB-3101: Nimbus NF-300 5.0.8 and 5.0.9: ikev2 child-sa renegotiation fails after pfs group change when rekey traffic is active (%IKEV2-3-PROPOSAL_MISMATCH)

## Known issues
- KB-3102: Nimbus NF-300 5.1.3 and 5.1.5: IKEv2 phase 2 resets when responder selects a different DH group than the initiator. Workaround: Pin a single DH group for the tunnel, preferably group 14, on both peers and avoid mixed transform sets. If the peer cannot be changed, shorten the lifetime to 1800 seconds so rekeys occur at predictable intervals and can be monitored.
- KB-3111: Nimbus NF-300 5.1.3 and 5.1.5: upgrade from 5.0.x may reset configuration objects if checkpoint replay exceeds 4,096 entries. Workaround: Break the configuration into smaller chunks before upgrading, or export and re-import the policy objects after the first boot. For large deployments, keep each checkpoint file under 4,000 entries and verify the running configuration immediately after reboot.

## Compatibility
Nimbus NF-300 5.1.3 supports upgrade from the 5.0.x and 5.1.x trains listed for this product family, with 5.0.9 as the immediately previous release in the 5.0 train. Hardware compatibility is unchanged for supported NF-300 platforms, and existing high-availability, SSL inspection, and threat-prevention configurations remain supported. IPsec/IKEv2 interoperability is maintained, but peers that negotiate different Diffie-Hellman groups or custom transform sets should be validated after upgrade. Administrators should also note that configuration migration behavior changed in this release; checkpoints created on earlier versions are supported, but large replay sets may require additional validation in environments with many stored objects.

## Upgrade notes
Supported direct upgrade path from 5.0.9. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export any required VPN certificates, keys, and checkpoint archives before starting the upgrade.
2. Verify the 5.1.3 image checksum and confirm the image is present on both HA members if the deployment uses redundancy.
3. Schedule a maintenance window and, where applicable, place the standby HA node into a controlled state before upgrading the active node.
4. Upgrade the primary system to 5.1.3, allow the device to reboot, and then confirm that the image boots successfully before proceeding to the peer.
5. After the system returns to service, verify VPN and HA status with 'show crypto ikev2 sa' and 'show ha status', then confirm session stability with 'show session table summary'.
6. If the deployment uses checkpoint-based recovery, validate checkpoint replay and review logs for migration warnings before resuming normal traffic.
