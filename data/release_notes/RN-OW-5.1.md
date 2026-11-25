---
doc_id: "RN-OW-5.1"
doc_type: "release_note"
product: "Orion OW-20"
version: "5.1"
version_family: "5.1"
---
# Orion OW-20 release 5.1: release notes

## Overview
Orion OW-20 release 5.1 adds targeted RF, guest access, and configuration safety improvements while continuing to focus on controller stability. The RF channel worker has been tuned to reduce scheduling delay under dense radio events, and guest ACL data is now migrated in a way that preserves legacy portal access policy objects during upgrade. In addition, configuration backup validation is introduced to detect incomplete or inconsistent backups before they are used for restore operations. This release also includes fixes for FT key push reliability during heavy 802.11r roaming and for upgrades from 4.6 environments that contain legacy guest portal ACL objects.

## New features
### RF channel worker tuning
The RF channel worker has been retuned to reduce update latency when the controller is processing frequent channel changes, including DFS-driven events. This improves the responsiveness of channel selection and AP radio reconfiguration during busy RF conditions. No new configuration commands are introduced; existing RF settings continue to apply.

### guest ACL migration
The upgrade process now migrates legacy guest portal ACL objects into the current configuration format. This preserves guest access policy behavior across version changes and reduces the risk of upgrade interruption on systems that still contain pre-5.0 ACL objects. Administrators should still review guest portal policies after upgrade to confirm that the intended permit and deny rules are present.

### configuration backup validation
The controller now validates configuration backups before they are accepted for restore or used in upgrade workflows. Validation checks for completeness, internal consistency, and expected object references in the backup set. If validation fails, the controller reports the backup as unusable and records the failure in the system log.

## Resolved issues
- KB-4106: Orion OW-20 5.0 may miss FT key pushes during heavy 802.11r roaming (%ROAM-5-FT_KEYTIMEOUT)
- KB-4111: Orion OW-20 upgrade from 4.6 to 5.0 can fail if the configuration database contains legacy guest portal ACL objects (ERR-UPG-2204)

## Known issues
- KB-4110: Orion OW-20 5.1 RF manager may stop channel updates after repeated DFS events on 5 GHz radios. Workaround: Disable DFS on the affected radio group and pin the radios to a non-DFS channel set with at least 20 MHz separation from neighboring cells. If DFS must remain enabled, limit the environment to fewer than 3 radar events per 10 minutes during peak usage.

## Compatibility
Release 5.1 supports upgrade from OW-20 5.0 and remains aligned with the 4.6 through 5.0 configuration families that are present in the current train. Controllers running 4.6 with legacy guest portal ACL objects may now upgrade through the normal path without the failure seen in earlier images, provided the configuration database is intact. Hardware support is unchanged for the OW-20 platform, and existing AP, RADIUS/802.1X, guest portal, roaming, and redundancy configurations are retained. Interoperability with access points and clients is unchanged, although administrators should verify RF behavior after upgrade in environments that rely on DFS events or aggressive 802.11r roaming. Backup files created on 5.1 should be validated before restore, and older backups should be checked for completeness before use.

## Upgrade notes
Supported direct upgrade path from 5.0. Back up the configuration before upgrading and review the known issues above.

1. Save the current configuration and export a backup from the running 5.0 controller.
2. Verify the 5.1 image checksum and confirm that sufficient storage is available for the image and rollback copy.
3. Schedule a maintenance window and, if the controller is in a redundancy pair, place the standby node out of service before starting the upgrade.
4. Upload the 5.1 image, start the upgrade, and allow the controller to complete the image installation and reboot without interruption.
5. After the controller returns to service, confirm image version, AP join state, client authentication, and redundancy status with show commands such as show ap summary and show client detail <mac>.
6. Validate that the saved configuration backup can be opened or restored, and review RF and guest portal operation for expected behavior.
