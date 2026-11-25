---
doc_id: "RN-OW-5.0"
doc_type: "release_note"
product: "Orion OW-20"
version: "5.0"
version_family: "5.0"
---
# Orion OW-20 release 5.0: release notes

## Overview
Orion OW-20 release 5.0 adds improvements to RADIUS challenge handling, roaming scheduler behaviour, and pre-upgrade validation. The update focuses on reducing authentication edge cases during Access-Challenge processing, improving the ordering of fast roaming work under load, and catching upgrade conditions earlier before the controller applies an incompatible configuration. This release also includes defect corrections for 4.9 issues affecting 802.11r key installation, Vendor-Specific attribute handling, and guest portal failover behaviour. Administrators planning an upgrade should review existing guest portal objects and validate upgrade sources before changing the active controller image.

## New features
### RADIUS challenge repacking
The controller now repacks Access-Challenge replies before forwarding them to the client authentication flow. This preserves Vendor-Specific attribute 26 when a reply contains a larger attribute set and reduces the chance of partial attribute loss during RADIUS processing. No configuration change is required, but TAC recommends verifying any custom RADIUS policy that depends on attribute ordering or attribute count limits.

### fast roaming queue priority
The roaming scheduler gives higher priority to 802.11r fast transition key work when the controller is processing concurrent roaming events. This lowers the chance that FT key installation is delayed behind less time-sensitive tasks during busy mobility periods. The feature is automatic; existing FT profiles continue to use the same enablement and timer settings.

### upgrade migration checks
The upgrade workflow now performs additional migration validation before committing the new image. The controller checks for configuration objects known to block upgrade, including legacy guest portal ACL content, and reports the condition before the upgrade proceeds. Administrators should review any reported conflicts and clean up unsupported objects prior to starting the upgrade.

## Resolved issues
- KB-4105: Orion OW-20 4.9 can delay 802.11r key installation during fast transition roaming (%ROAM-5-FT_KEYTIMEOUT)
- KB-4107: Orion OW-20 4.9 drops Vendor-Specific attribute 26 on Access-Challenge replies with more than 12 attributes (%RADIUS-4-ATTR_DROP)
- KB-4108: Orion OW-20 4.9 may omit Vendor-Specific attribute 26 from Access-Challenge processing when the reply contains 13 attributes (%RADIUS-4-ATTR_DROP)
- KB-4109: Orion OW-20 guest portal sessions fail after standby failover when the portal cookie is pinned to the active node UUID (%PORTAL-5-COOKIE_MISMATCH)

## Known issues
- KB-4106: Orion OW-20 5.0 may miss FT key pushes during heavy 802.11r roaming. Workaround: Stagger roaming tests or reduce the client cleanup batch size so the FT flush completes within 150 ms. If the SSID is voice-critical, cap roam bursts below 30 clients per 10 seconds until the release is updated.
- KB-4111: Orion OW-20 upgrade from 4.6 to 5.0 can fail if the configuration database contains legacy guest portal ACL objects. Workaround: Delete unused legacy guest portal ACL objects before starting the upgrade, and export the configuration for review so the database contains only normalized entries. If the upgrade already failed, boot the old image and rerun the migration after pruning the stale ACL objects.

## Compatibility
Orion OW-20 5.0 supports direct upgrade from 4.9 and retains compatibility with the existing OW-20 hardware platform and controller-wide CLI model. Configuration syntax remains unchanged for wireless, roaming, RADIUS, guest portal, redundancy, and RF features, but the pre-upgrade migration checks can block upgrades from older configurations that contain unsupported legacy guest portal ACL objects. Interoperability with 802.1X, 802.11r/k/v, and standard RADIUS servers is preserved; however, environments using custom Access-Challenge policies should verify that Vendor-Specific attribute 26 is handled as expected after upgrade. Existing standby and redundancy designs remain supported, including n-plus-1 operation.

## Upgrade notes
Supported direct upgrade path from 4.9. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export any local certificates, guest portal content, and RADIUS-related policy objects before the maintenance window.
2. Verify the target 5.0 image checksum and confirm sufficient flash space on the controller before copying the image.
3. Review the configuration for legacy guest portal ACL objects and remove or replace unsupported entries if the pre-upgrade migration checks report them.
4. Schedule a maintenance window, place the controller into an upgrade-ready state, and stage the 5.0 image on the active node.
5. Apply the upgrade on the active controller, monitor the migration checks and boot messages, and confirm that the standby node resumes synchronization after failover.
6. After reboot, run post-checks including show ap summary, show client detail <mac>, and redundancy status verification, then test 802.1X authentication, guest portal login, and a sample fast-roaming event.
