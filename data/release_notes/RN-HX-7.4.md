---
doc_id: "RN-HX-7.4"
doc_type: "release_note"
product: "Helix HX-5000"
version: "7.4"
version_family: "7.4"
---
# Helix HX-5000 release 7.4: release notes

## Overview
Helix HX-5000 release 7.4 adds buffer management and upgrade-safety improvements for core-switch deployments. The release focuses on traffic handling under sustained load, stricter validation of device operating-mode thresholds, and additional checks during software migration to reduce upgrade risk. It also includes fixes for stack stability during master election and for burst loss on oversubscribed 100G egress paths. Administrators should review existing LACP designs before deployment, because interoperability issues remain when a peer advertises slow LACP timers. Overall, this release is intended for customers seeking improved forwarding resilience and a more predictable upgrade process on HX-5000 systems running the 7.x train.

## New features
### expanded buffer scheduling
This release expands buffer scheduling on HX-5000 egress paths to better distribute queued traffic during microbursts and sustained congestion. The change improves forwarding consistency under high-utilization conditions and reduces the likelihood of transient drops on oversubscribed interfaces. No new configuration is required, but operators should revalidate queueing behavior in environments that rely on tight latency thresholds.

### dom threshold validation
Release 7.4 adds validation for domain-of-operation threshold values before they are committed to running configuration. Invalid or out-of-range threshold settings are now rejected at configuration time rather than applied and corrected later by the system. This reduces ambiguity during change windows and helps prevent misconfiguration in automation workflows that push threshold-based policies.

### upgrade migration checks
The upgrade process now performs additional migration checks before activating the new image. These checks validate configuration objects and operational dependencies that affect post-upgrade startup, so incompatible state is identified earlier in the workflow. Administrators may see the upgrade paused or rejected if preconditions are not met, and should clear those conditions before retrying.

## Resolved issues
- KB-6103: HX-5000 stack master election oscillates in 7.3 when stack cables negotiate at mixed speed (%STACK-3-SPLIT-BRAIN)
- KB-6109: HX-5000 7.2 oversubscribed 100G egress queues drop bursts above 85 percent utilization (%BUF-3-OVERFLOW)

## Known issues
- KB-6106: HX-5000 7.4 EtherChannel mis-bundles member ports when partner uses slow LACP timers. Workaround: Configure the peer and local bundle for fast LACP timers if the design permits it, or manually clear the affected EtherChannel after link restoration. If the bundle must stay on slow timers, avoid flapping individual member links during maintenance.
- KB-6107: HX-5000 7.4 LACP bundle can suspend member links when the peer advertises slow timers. Workaround: If the design allows it, configure both ends of the bundle for fast LACP timers. If fast timers are not an option, manually clear the affected EtherChannel after the link comes back. When the bundle must remain on slow timers, do not flap individual member links during maintenance.

## Compatibility
Helix HX-5000 release 7.4 supports in-train upgrades from 7.3 and remains compatible with existing HX-5000 hardware platforms that are supported on the 7.x train. Interoperability with adjacent network devices is unchanged for standard Ethernet, stacking, spanning tree, and VXLAN/EVPN deployments, but known LACP issues remain when peers use slow timers, so mixed-timer EtherChannel designs should be reviewed before upgrading. Configuration is broadly preserved, although the new threshold validation may cause previously accepted values to fail commit during startup or when re-entered through configure terminal. Back up the running configuration and confirm that any automation accounts for stricter validation behavior before proceeding.

## Upgrade notes
Supported direct upgrade path from 7.3. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and save a copy of the current startup configuration.
2. Verify the target image checksum and confirm sufficient flash and system resource headroom for the upgrade.
3. Schedule a maintenance window and notify stakeholders of the expected control-plane interruption during the reload.
4. Stage the 7.4 image on the device, then run the pre-upgrade migration check and resolve any reported validation errors.
5. Perform the upgrade from a privileged session, allow the system to reload, and confirm that the active image is 7.4 after boot.
6. Run post-upgrade checks including show stack, show interfaces transceiver detail, and show mac address-table flapping to confirm stable operation.
