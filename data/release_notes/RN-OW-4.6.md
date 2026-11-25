---
doc_id: "RN-OW-4.6"
doc_type: "release_note"
product: "Orion OW-20"
version: "4.6"
version_family: "4.6"
---
# Orion OW-20 release 4.6: release notes

## Overview
Orion OW-20 release 4.6 is the initial GA software for the OW-20 controller platform. It establishes the baseline control-plane behavior for AP onboarding, guest access, and configuration persistence, with emphasis on deterministic controller operation during joins and configuration updates. This release is intended for first deployment on supported OW-20 hardware and for lab or production environments that need the 4.6 feature set. Operational focus areas include CAPWAP AP join processing, the new guest portal object model, and the configuration database commit queue. Administrators should validate AP join behavior, guest portal workflows, and commit activity after upgrade, especially in environments with large configuration bursts or strict RF profile handling.

## New features
### CAPWAP join baseline
This release introduces the initial CAPWAP join processing baseline for Orion OW-20. AP join handling now uses a consistent controller-wide state machine for discovery, image negotiation, configuration download, and registration, which simplifies troubleshooting with show ap summary and per-AP detail output. The baseline also defines the controller behavior for common join timing and retransmission events.

### guest portal object model
Release 4.6 adds the first guest portal object model on the OW-20 controller. Portal settings, authentication policy, and guest session attributes are stored as discrete controller objects rather than as a single monolithic profile, which improves configuration clarity and prepares the platform for later workflow expansion. Existing deployments should review portal dependencies before migration because object references are now validated at commit time.

### configuration database commit queue
This release adds a commit queue to serialize configuration database writes across controller subsystems. The queue reduces contention during bursts of edits and avoids partial application of related changes, especially when multiple WLAN, RF, or portal objects are modified together. Administrators may observe brief commit latency during large configuration updates, but the resulting configuration state is applied atomically per commit.

## Resolved issues
- None

## Known issues
- KB-4101: Orion OW-20 4.6 rejects AP joins when the join request includes a zero-length RF profile TLV. Workaround: Remove the RF profile override from the AP group so the controller stops emitting the empty TLV, or migrate the APs to a group with no custom RF settings. If the fleet is mixed, disable the affected APs' per-radio override until the upgrade is complete.

## Compatibility
Release 4.6 is the first software train supported on Orion OW-20 hardware and does not support direct upgrade from earlier OW-20 releases because none exist in this train. AP interoperability is limited to CAPWAP-based Orion AP models approved for OW-20 4.6; validate AP image compatibility before bringing access points back into service. Configuration imported from other Orion controller families may require manual normalization, particularly for guest portal objects and any workflow that depends on commit ordering. Existing WLAN, RF, and security settings are retained during upgrade where the source configuration is compatible, but administrators should review portal references, AP group membership, and any custom RF profile definitions before enabling production traffic.

## Upgrade notes
Initial release in this train. Back up the configuration before upgrading and review the known issues above.

1. Back up the current controller configuration and export any portal, WLAN, RF, and security objects needed for recovery.
2. Verify the 4.6 image checksum and signature, then stage the image on the OW-20 controller.
3. Schedule a maintenance window and ensure APs can tolerate a temporary join interruption while the controller reboots.
4. Upgrade the controller to Orion OW-20 4.6, then allow the configuration database to complete the initial commit queue flush before restoring client service.
5. After the upgrade, run show ap summary, show client detail <mac>, and show running-config to confirm AP registration, client authentication, and configuration persistence.
6. If guest portal service is used, test a full guest login workflow and confirm portal object references resolve correctly.
