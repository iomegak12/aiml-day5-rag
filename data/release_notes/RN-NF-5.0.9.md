---
doc_id: "RN-NF-5.0.9"
doc_type: "release_note"
product: "Nimbus NF-300"
version: "5.0.9"
version_family: "5.0"
---
# Nimbus NF-300 release 5.0.9: release notes

## Overview
Nimbus NF-300 release 5.0.9 is a maintenance release for the 5.0 train with targeted improvements to boot image validation, IPsec child SA rekey handling, and high-availability replay logging. The release focuses on upgrade reliability and operational visibility in environments that use IKEv2 VPNs and active HA pairs. It also addresses an issue where the boot loader could reject a valid 5.0.9 image after HTTPS stage download. Customers should note the remaining known issues affecting child SA renegotiation during PFS group changes with active rekey traffic, and standby session loss after split-brain recovery.

## New features
### Boot loader verification update
The boot loader validation path has been updated to accept the 5.0.9 image format after HTTPS stage download. This reduces the risk of upgrade interruption during staged image transfer and subsequent reboot. No configuration changes are required.

### Child SA rekey stability improvements
IPsec child SA rekey processing has been hardened to reduce renegotiation failures under load. The change improves handling of rekey timing and state transitions in environments with active VPN traffic, but the known issue involving PFS group changes during rekey remains present in this release.

### HA replay logging
High-availability replay events are now logged with additional detail to help identify session replication and replay-order issues during failover analysis. These messages are intended to improve TAC troubleshooting of HA synchronization and recovery behaviour. No new configuration knobs are introduced.

## Resolved issues
- KB-3104: Nimbus NF-300 5.0.8: boot loader rejects a valid 5.0.9 image after HTTPS stage download (%UPGRADE-3-IMAGE_VERIFY_FAIL)

## Known issues
- KB-3101: Nimbus NF-300 5.0.8 and 5.0.9: ikev2 child-sa renegotiation fails after pfs group change when rekey traffic is active. Workaround: Keep the PFS group unchanged on both peers, or disable child SA rekey and force a manual tunnel restart during a maintenance window. If you must change the group, apply the same group on both sides and clear the SA after the change.
- KB-3103: Nimbus NF-300 5.0.9: standby drops replicated sessions after split-brain recovery. Workaround: Manually force a full HA resync after recovery instead of relying on the incremental replay. Keep failover links stable for at least 120 seconds after node return so the replay queue can drain.

## Compatibility
Release 5.0.9 is supported as an upgrade from Nimbus NF-300 5.0.8 within the 5.0 family. It is intended for existing NF-300 hardware and does not introduce new platform dependencies. Interoperability with existing IKEv2 peers, HA pairs, SSL inspection policies, and threat-prevention profiles is preserved, although the known IPsec child SA renegotiation issue during PFS group changes and the standby session-drop issue after split-brain recovery remain present. Configuration format is unchanged; no migration steps are required beyond a normal commit-based upgrade workflow.

## Upgrade notes
Supported direct upgrade path from 5.0.8. Back up the configuration before upgrading and review the known issues above.

1. Back up the current configuration and export any locally stored certificates, VPN credentials, and diagnostic logs before starting the upgrade.
2. Verify the 5.0.9 image checksum and confirm the image has been transferred successfully to the device staging area.
3. Schedule a maintenance window and ensure HA peers, VPN tunnels, and session-sensitive services can tolerate a brief restart.
4. Install the 5.0.9 image on the active unit, then reboot or trigger the staged activation according to your standard procedure.
5. After the device returns to service, verify the software version, confirm HA state with `show ha status`, and check VPN and session health with `show crypto ikev2 sa` and `show session table summary`.
6. Review system logs for boot, HA, and VPN warnings, then repeat the upgrade on the peer unit if operating in an HA pair.
