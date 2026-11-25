---
doc_id: "RN-OW-4.8"
doc_type: "release_note"
product: "Orion OW-20"
version: "4.8"
version_family: "4.8"
---
# Orion OW-20 release 4.8: release notes

## Overview
Orion OW-20 release 4.8 introduces changes in AP onboarding, configuration replication, and roaming visibility. The AP join state machine has been reworked to improve retry handling during capability negotiation, incremental configuration sync reduces replication overhead on active-standby systems, and roaming telemetry adds more detailed reporting for 802.11r/k/v analysis. This release also includes a fix for AP join retry loss seen in 4.7. The primary quality focus remains controller stability under AP join load, redundancy synchronization, and operational observability.

## New features
### AP join state-machine rework
The AP join sequence has been reworked to handle radio capability revalidation and retry transitions more deterministically. This reduces the chance of losing join progress during capability exchange and improves recovery when an AP restarts the join process. No configuration changes are required, but TAC may request additional join-state logs when troubleshooting onboarding issues.

### incremental config sync
Configuration replication between active and standby controllers now propagates changed rows instead of forcing full database refreshes on each sync cycle. This reduces sync traffic and shortens convergence time after routine configuration changes, particularly in environments with frequent WLAN or policy updates. The feature is internal to the controller and does not change the CLI model, but large configuration databases should still be monitored during redundancy testing.

### roaming telemetry
The controller now records additional telemetry for client roaming events, including transition timing and steering outcomes relevant to 802.11r/k/v behavior. This improves root-cause analysis for sticky-client and handoff complaints and helps correlate roam latency with RF and policy changes. Operators can use the expanded client detail output and controller logs to validate roaming performance after feature or RF adjustments.

## Resolved issues
- KB-4102: Orion OW-20 4.7 may drop AP join retries after radio capability revalidation (ERR-APJ-4417)

## Known issues
- KB-4103: Orion OW-20 4.8 AP join stalls when the second capability exchange is delayed. Workaround: Temporarily increase the join timeout to 180 seconds and keep AP uplink loss under 0.5% during join. If the branch link is unstable, stage the APs locally and move them after the initial registration completes.
- KB-4104: Orion OW-20 4.8 active-standby sync stalls when the configuration database exceeds 32,768 rows. Workaround: Reduce the configuration database below 30,000 rows by deleting unused AP groups, WLAN profiles, and stale guest accounts before enabling redundancy. If immediate failover is required, force a full config resync during a maintenance window.

## Compatibility
Release 4.8 is supported as an upgrade from Orion OW-20 4.7; direct upgrade paths from older major.minor families are not specified in this release note and should be validated against local upgrade policy before use. The release applies to Orion OW-20 controller hardware and retains CLI compatibility with existing flat, controller-wide commands and configuration objects. Existing APs and wireless clients remain interoperable, including deployments using 802.11r/k/v, RADIUS/802.1X, guest portal, and redundancy features. The incremental sync change does not require manual migration, but administrators should review redundancy settings and confirm that the configuration database size remains within operational limits before and after upgrade.

## Upgrade notes
Supported direct upgrade path from 4.7. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export the configuration database before starting the upgrade.
2. Verify the 4.8 image checksum and confirm that the image is present on both controller nodes if operating in a redundant pair.
3. Schedule a maintenance window and inform AP and client stakeholders, especially if the controller is handling roaming-sensitive WLANs or 802.1X authentication.
4. Upgrade the standby controller first, allow it to return to service, and confirm redundancy health before upgrading the active controller.
5. After both nodes are upgraded, verify AP membership and controller state with `show ap summary` and confirm roaming and authentication behavior with representative clients.
6. Review logs and operational counters for AP join retries, sync status, and roaming events, and retain the backup until the post-upgrade validation window is complete.
