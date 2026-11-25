---
doc_id: "RN-AR-9.1.6"
doc_type: "release_note"
product: "Aurora AR-900"
version: "9.1.6"
version_family: "9.1"
---
# Aurora AR-900 release 9.1.6: release notes

## Overview
Aurora AR-900 9.1.6 is a maintenance release for the 9.1 train with targeted protocol and upgrade-state improvements. It adds more robust BGP route-refresh processing, prevents BFD transmit stalls when counters approach 64-bit wrap, and updates state migration logic used during software upgrade and rollback. These changes are intended to reduce control-plane disruption on long-lived peers and improve upgrade reliability without changing the established routing and policy model. The release remains focused on operational stability in environments using BGP, BFD, IPv6, QoS, control-plane protection, SNMP, NAT, and OSPF, with no new configuration model introduced beyond the existing 9.1.x command set.

## New features
### BGP route refresh handling
This release improves how the router processes inbound and outbound BGP route refresh requests when adjacent peers request a full table resend. The control plane now preserves session state more consistently during repeated refresh events and avoids unnecessary transient churn in adj-rib processing. No configuration changes are required, but operators should expect refresh-driven reconvergence to be more predictable on long-lived sessions.

### BFD counter wrap handling
BFD transmit and receive accounting now handles 64-bit counter wrap correctly on long-lived sessions. This prevents the transmit path from stalling when counters roll over on peers that have been established for extended periods. Existing BFD configuration, including interval and multiplier settings, is unchanged.

### Upgrade state migration
The upgrade process now migrates stored system state more reliably when moving from 9.1.4 to 9.1.6. This reduces the risk of inconsistent control-plane or management state after reboot, especially where routing and monitoring services are active during the upgrade window. No new commands are introduced, but operators should continue to perform a controlled maintenance-window upgrade and verify service state after first boot.

## Resolved issues
- KB-2102: Aurora AR-900 9.1.4 BFD sessions stop transmitting after 64-bit counter wrap on long-lived peers (ERR-BFD-2201)

## Known issues
- KB-2101: Aurora AR-900 9.1.4 and 9.1.6 BGP IPv4 next-hop stays unresolved after underlay route withdrawal. Workaround: Clear the BGP process for the affected address family, or remove and re-add the underlay static/connected route so recursion is recomputed. If the path is critical, prefer a static discard route with a lower distance than the learned underlay during the maintenance window.
- KB-2111: Aurora AR-900 9.1.x upgrade to 9.2.0 fails when BGP add-path is enabled. Workaround: Disable BGP add-path before starting the upgrade, then re-enable it after the router is running 9.2.0. If the box is already stuck in rollback, complete the boot on the previous release, remove add-path configuration, and retry the upgrade.

## Compatibility
Aurora AR-900 9.1.6 is supported as an in-train upgrade from 9.1.4 on AR-900 hardware. Configuration compatibility is preserved for existing 9.1.x features and CLI structure, including routing, BFD, SNMP, NAT, QoS, OSPF, and control-plane protection. Interoperability with external peers follows the same protocol behavior as 9.1.4, except for the protocol handling changes noted above; operators should still validate BGP and BFD adjacencies after upgrade, especially in environments that rely on route refresh or long-lived BFD sessions. This release does not introduce a new configuration syntax, but stored upgrade state is migrated automatically during first boot.

## Upgrade notes
Supported direct upgrade path from 9.1.4. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and save a copy of the current boot image and device inventory before starting.
2. Verify the target image checksum and confirm that sufficient flash space is available for the new release.
3. Schedule a maintenance window and notify stakeholders, because the router will reboot during the upgrade and adjacencies will reset.
4. Copy the 9.1.6 image to the device, set it as the boot image, and reload the router.
5. After the system returns to service, confirm basic health with 'show system status', then check routing and transport services with 'show bgp summary' and 'show bfd neighbors detail'.
6. Review logs for unexpected errors and verify that interface, NAT, and management services have returned to their expected state.
