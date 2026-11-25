---
doc_id: "RN-HX-7.2"
doc_type: "release_note"
product: "Helix HX-5000"
version: "7.2"
version_family: "7.2"
---
# Helix HX-5000 release 7.2: release notes

## Overview
Helix HX-5000 release 7.2 introduces initial platform support for 25G optical DOM telemetry, enhanced queue counters, and basic rapid-pvst operation. The release is focused on visibility and baseline Layer 2 functionality for core-switch deployments, with particular attention to optics, queue behaviour, and spanning-tree convergence. Because this is the first release in the 7.x train, configuration and operational workflows are intentionally conservative, and administrators should validate transceiver telemetry collection, queue monitoring, and spanning-tree mode selection before broad rollout. Known issues remain in 7.2 around certain SFP28 link conditions, oversubscribed 100G egress bursts, and one upgrade path to 7.4.

## New features
### 25G optical DOM telemetry
The switch now reports digital optical monitoring values for supported 25G transceivers, including temperature, transmit and receive power, bias current, and module voltage. Use this data to trend optics health and identify marginal links before they affect traffic, especially on uplinks and stacked interconnects. The feature is read-only and does not change transceiver calibration or link negotiation.

### enhanced queue counters
Queue statistics now include higher-resolution transmit and drop counters for congestion analysis on ingress and egress scheduling points. This improves visibility into burst absorption and persistent oversubscription on high-speed ports, and the counters can be correlated with interface and buffer statistics during troubleshooting. No configuration is required, but existing monitoring systems may need to be updated to poll the expanded counter set.

### basic rapid-pvst support
Release 7.2 adds basic rapid-pvst operation for deployments that require faster spanning-tree convergence than classic PVST behavior. The feature is enabled through spanning-tree configuration and is intended for access and core edge designs that use VLAN-based spanning tree. Validate interoperability carefully in mixed environments, as only baseline rapid-pvst behaviour is included in this release.

## Resolved issues
- None

## Known issues
- KB-6101: HX-5000 7.2 SFP28 link drops with DOM bias current spike and remote LOS alarms. Workaround: Reduce DOM polling activity on the affected ports and keep the optics below 50 C case temperature if possible. If the port is flapping under load, move the optic to a port running a later release or replace it with a module that has a stable bias current profile.
- KB-6109: HX-5000 7.2 oversubscribed 100G egress queues drop bursts above 85 percent utilization. Workaround: Reduce burstiness with traffic shaping upstream, or spread the workload across additional uplinks so no single egress port remains above 85 percent sustained utilization. For critical low-latency flows, reserve a dedicated queue on the affected interface.
- KB-6111: Upgrade from 7.2 to 7.4 can fail when saved transceiver calibration data exceeds 32 KB. Workaround: Back up the configuration, clear nonessential DOM history, and retry the upgrade from a maintenance window with fewer populated optics. If the system has many optics, remove and reseat the most recently installed modules before retrying so the calibration cache is rebuilt smaller.

## Compatibility
Release 7.2 is the first release in the Helix HX-5000 7.x train, so upgrade sources from earlier HX-5000 software are not applicable. The release is intended for supported HX-5000 hardware and is compatible with standard Layer 2 and Layer 3 deployments, including optics, stacking, and link aggregation features already present on the platform. Interoperability with third-party devices should be verified for rapid-pvst and transceiver telemetry workflows, since both depend on peer behaviour and management-system support. Existing configurations are generally retained, but administrators enabling rapid-pvst should review spanning-tree mode and VLAN topology before upgrade, and monitoring systems may need to accommodate the new queue counter fields and DOM telemetry output.

## Upgrade notes
Initial release in this train. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export any stored transceiver or operational data before beginning the upgrade.
2. Verify the 7.2 image checksum and confirm the package is present and readable on the target system.
3. Schedule a maintenance window, because the upgrade requires a reload and may briefly interrupt forwarding.
4. Stage the image on the HX-5000, then perform the upgrade during the maintenance window and allow the system to reboot fully.
5. After boot, confirm the software version, validate interface status, check transceiver DOM output, and review queue and spanning-tree counters for expected values.
