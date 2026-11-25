---
doc_id: "RN-HX-7.5"
doc_type: "release_note"
product: "Helix HX-5000"
version: "7.5"
version_family: "7.5"
---
# Helix HX-5000 release 7.5: release notes

## Overview
Helix HX-5000 release 7.5 focuses on link aggregation stability, optics event handling, and parser resilience. This release adds improved LACP marker processing to reduce bundle instability when peers negotiate slow timers, tunes transceiver debounce logic to reduce transient state changes, and hardens the configuration parser against malformed or oversized input during upgrade and reload operations. Quality work in this release also addresses previously observed EtherChannel mis-bundling and an upgrade failure path associated with saved transceiver calibration data. Administrators should review post-upgrade transceiver status on high-speed uplinks, especially where DOM thresholds are close to operating margins.

## New features
### LACP marker handling
This release improves handling of LACP marker responses during bundle negotiation and link recovery. The switch now processes marker-driven state transitions more deterministically when the peer advertises slow LACP timers, which reduces mis-bundling and unexpected member suspension in EtherChannel deployments.

### transceiver debounce tuning
The transceiver state machine has updated debounce thresholds for LOS, DOM, and module-insertion events. These changes reduce short-lived flaps caused by transient optics conditions, but they can also delay alarm assertion and clearance slightly compared with 7.4.

### configuration parser hardening
The configuration parser has been strengthened to reject malformed input earlier and to handle larger saved state blocks during boot and upgrade. This reduces the risk of upgrade interruption when existing configuration or transceiver calibration data is larger than expected, and it improves reload robustness for complex configurations.

## Resolved issues
- KB-6106: HX-5000 7.4 EtherChannel mis-bundles member ports when partner uses slow LACP timers (%LACP-4-MISBUNDLE)
- KB-6107: HX-5000 7.4 LACP bundle can suspend member links when the peer advertises slow timers (%LACP-4-MISBUNDLE)
- KB-6111: Upgrade from 7.2 to 7.4 can fail when saved transceiver calibration data exceeds 32 KB (ERR-UPG-2207)

## Known issues
- KB-6102: HX-5000 7.5 QSFP28 uplinks report intermittent LOS after DOM threshold recalculation. Workaround: Disable aggressive DOM alarm action on the affected interface and leave the port in service if the module readings stay inside the normal operating range. If the uplink is critical, move it to a release that contains the corrected debounce handling.

## Compatibility
Release 7.5 supports upgrade from Helix HX-5000 releases 7.2, 7.3, and 7.4 on supported hardware in the HX-5000 core switch family. Existing interface, stacking, spanning tree, LACP, and VXLAN/EVPN configurations remain supported, with no mandatory syntax changes; however, devices with extensive optics calibration records should be verified before upgrade, especially if they previously used 7.2 software. Interoperability behavior with LACP peers is unchanged at the protocol level, but bundle formation may appear more stable after upgrade because marker handling is stricter. Review transceiver thresholds and monitor QSFP28 uplinks after upgrade, as intermittent LOS reports can still occur when DOM threshold recalculation is in progress.

## Upgrade notes
Supported direct upgrade path from 7.4. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration, startup configuration, and any saved transceiver calibration data before scheduling the upgrade.
2. Verify the 7.5 image checksum and copy the image to the standby storage location used for boot selection.
3. Plan a maintenance window and confirm that all critical LACP bundles, stacking links, and uplinks are in a healthy state before starting.
4. Upgrade one chassis or stack member at a time where operationally possible, then reload the device to activate release 7.5.
5. After the device returns to service, verify software version, stack membership, LACP bundle state, and interface health with `show stack`, `show interfaces transceiver detail`, and `show mac address-table flapping`.
6. Monitor logs and counters for transceiver LOS events, bundle suspensions, and parser-related errors during the first post-upgrade operational interval.
