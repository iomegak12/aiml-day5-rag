---
doc_id: "RN-NF-5.1.5"
doc_type: "release_note"
product: "Nimbus NF-300"
version: "5.1.5"
version_family: "5.1"
---
# Nimbus NF-300 release 5.1.5: release notes

## Overview
Nimbus NF-300 release 5.1.5 extends the 5.1 train with changes in threat prevention, SSL inspection, and high-availability telemetry. The update focuses on operational scaling and visibility in deployments that carry larger policy sets, more active inspection sessions, and tighter HA observability requirements. This release should be evaluated carefully in environments with IKEv2 and large threat signature updates, because the known issues listed for 5.1.5 remain present. Customers upgrading from 5.1.3 receive the full 5.1.5 feature set and should use the standard backup and staged upgrade procedure to reduce interruption risk.

## New features
### Threat prevention signature cache changes
The threat prevention engine now uses a revised signature cache layout to reduce lookup contention under higher rule counts and larger signature sets. This change improves cache locality during inspection, but it does not remove the operational limit associated with very large update bundles. Administrators do not need to change policy syntax, although they should monitor update size and dataplane health after applying new signature content.

### SSL inspection policy scaling
SSL inspection policy handling has been tuned to support larger policy tables and higher session turnover without requiring manual policy partitioning. The control plane now allocates policy resources more efficiently during commit and session establishment, which reduces pressure on systems that run many exception rules or multiple inspection profiles. Existing policy objects remain valid, and no syntax changes are required.

### HA resync telemetry
High-availability resync operations now expose additional telemetry for state synchronization progress, backlog depth, and completion status. These counters improve troubleshooting when peers take longer to converge after a failover or configuration commit. The new telemetry is read-only and does not change HA behavior, but operators should update runbooks to include the new status output when validating sync health.

## Resolved issues
- None

## Known issues
- KB-3102: Nimbus NF-300 5.1.3 and 5.1.5: IKEv2 phase 2 resets when responder selects a different DH group than the initiator. Workaround: Pin a single DH group for the tunnel, preferably group 14, on both peers and avoid mixed transform sets. If the peer cannot be changed, shorten the lifetime to 1800 seconds so rekeys occur at predictable intervals and can be monitored.
- KB-3105: Nimbus NF-300 5.1.5: threat database update can stall packet processing when signature bundle exceeds 128 MB. Workaround: Schedule threat database updates during a maintenance window and, if possible, reduce the feed set so the bundle stays below 128 MB. If an update is already in progress, avoid initiating SSL inspection policy changes until activation is complete.
- KB-3111: Nimbus NF-300 5.1.3 and 5.1.5: upgrade from 5.0.x may reset configuration objects if checkpoint replay exceeds 4,096 entries. Workaround: Break the configuration into smaller chunks before upgrading, or export and re-import the policy objects after the first boot. For large deployments, keep each checkpoint file under 4,000 entries and verify the running configuration immediately after reboot.

## Compatibility
Nimbus NF-300 5.1.5 supports upgrade from 5.1.3 on all hardware platforms that run the 5.1 train. Direct upgrade from 5.0.x is not recommended for production without a validated checkpoint export and recovery plan, because configuration replay may reset objects when more than 4,096 entries are processed during migration. Interoperability for IPsec/IKEv2, HA peer operation, and SSL inspection remains aligned with 5.1.3, but environments using large IKEv2 phase 2 option sets should verify peer proposals before upgrading because a responder-selected DH group different from the initiator can still reset phase 2. No configuration syntax changes are required for the new features, though operators should review threat update sizing and HA monitoring procedures after upgrade.

## Upgrade notes
Supported direct upgrade path from 5.1.3. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export a checkpoint before starting the upgrade. Confirm that the backup is readable and that you can restore it on the target hardware if rollback is required.
2. Verify the 5.1.5 image checksum and signature, then copy the image to the appliance storage used for staged upgrades. Check available flash capacity and remove unused images if necessary.
3. Schedule a maintenance window and notify stakeholders of a brief service interruption if the device is running in an active firewall or HA pair role. Disable nonessential change automation during the upgrade.
4. Install the 5.1.5 image on the standby unit first in an HA pair, or on a nonproduction system first for single-device validation. Reboot only after the image verification step completes successfully.
5. After the device returns to service, confirm health with `show ha status`, `show session table summary`, and `show crypto ikev2 sa`. Verify that session counts, HA sync state, and VPN tunnels are normal.
6. Monitor post-upgrade logs and threat update behavior for at least one update cycle. If the environment uses large signature bundles, confirm that packet processing remains stable and that no update stall conditions appear during the first synchronization window.
