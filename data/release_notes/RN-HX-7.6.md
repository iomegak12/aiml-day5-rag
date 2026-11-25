---
doc_id: "RN-HX-7.6"
doc_type: "release_note"
product: "Helix HX-5000"
version: "7.6"
version_family: "7.6"
---
# Helix HX-5000 release 7.6: release notes

## Overview
Helix HX-5000 release 7.6 adds operational enhancements for EVPN control-plane maintenance, stack resilience, and multicast buffer visibility. The release also addresses a transceiver-related issue seen on 7.5 where QSFP28 uplinks could report intermittent loss of signal after DOM threshold recalculation. Overall quality focus in 7.6 is on improving stability in stacked deployments and reducing ambiguity in buffer-related troubleshooting, while maintaining configuration and forwarding behaviour compatible with the 7.5 train for typical core switching deployments.

## New features
### EVPN route-refresh support
This release adds EVPN route-refresh handling so the routing process can re-advertise EVPN state without requiring a full control-plane reset. The feature is intended for operational use during route-policy changes and troubleshooting, and it preserves existing VXLAN/EVPN configuration. In environments with repeated route-refresh activity, monitor process memory until the follow-on fix is available in a later release.

### stack heartbeat refinements
Stack heartbeat processing has been refined to reduce false separation events caused by transient jitter on the interconnect path. The change improves detection and recovery behaviour for stacked HX-5000 systems and adjusts internal timers used for dual-path heartbeat evaluation. No configuration changes are required, but TAC recommends verifying stack health after upgrade with 'show stack' in environments using long cable runs.

### multicast buffer accounting
This release improves multicast buffer accounting so counters better reflect actual queue consumption during periods of sustained replication. The updated accounting is intended to improve troubleshooting of buffer drops and multicast congestion without changing forwarding policy. Existing multicast and QoS configuration is retained, but operators may notice counter values differ from earlier releases because the accounting model has been corrected.

## Resolved issues
- KB-6102: HX-5000 7.5 QSFP28 uplinks report intermittent LOS after DOM threshold recalculation (%TRANSCEIVER-4-LOS)

## Known issues
- KB-6104: HX-5000 7.6 stack members briefly separate after dual-path heartbeat jitter on long cable runs. Workaround: Keep stack cabling under 1 m when possible and avoid chaining all members through a single long physical path. If the installation must use 2 m cables, place the stack on a release with the corrected heartbeat hold-down timer.
- KB-6108: HX-5000 7.6 EVPN type-5 routes stop advertising after anycast gateway MAC move. Workaround: Trigger a controlled EVPN route refresh after moving the anycast gateway, or avoid gateway MAC mobility during periods when the fabric is carrying active type-5 routes. If operationally possible, keep the gateway anchored on a single leaf pair until the software is upgraded.
- KB-6112: HX-5000 7.6 routing process leaks memory after repeated EVPN route-refresh events. Workaround: Reduce the frequency of route-refresh events by limiting unnecessary neighbor resets and schedule a reload before free memory drops below 15 percent. If the fabric is stable, keep EVPN adjacency changes out of peak traffic windows.

## Compatibility
Release 7.6 is supported for upgrade from HX-5000 7.5. Configuration is expected to be forward-compatible with 7.5 for switching, stacking, spanning tree, LACP, and VXLAN/EVPN deployments, with no mandatory configuration migration steps. Mixed-version operation is not recommended for extended periods in stacked or EVPN environments, and the known issues listed for this release should be considered when planning maintenance on systems with long stack cabling or heavy EVPN route-refresh usage. Optical hardware and transceiver support remain aligned with the 7.5 hardware matrix; verify optics with 'show interfaces transceiver detail' after upgrade if the environment previously showed DOM or LOS anomalies.

## Upgrade notes
Supported direct upgrade path from 7.5. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and capture a copy of the current software image, stack state, and relevant operational output such as 'show stack' and 'show interfaces transceiver detail'.
2. Verify the 7.6 image checksum and digital signature on the staging server or transfer source before copying it to the switch.
3. Schedule a maintenance window that accounts for control-plane restart time and, if applicable, the time needed to upgrade stack members in sequence.
4. Install the 7.6 image on the standby or non-active system first, then reload or fail over according to the site upgrade procedure; for stacked systems, upgrade one member at a time where operationally permitted.
5. After the upgrade, confirm platform health with 'show stack', check interface and transceiver status, and validate EVPN, spanning tree, and LACP adjacency state as appropriate for the deployment.
6. Review system logs for unexpected warnings or process restarts, then save the confirmed working configuration if no anomalies are observed.
