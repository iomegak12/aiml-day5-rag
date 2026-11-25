---
doc_id: "RN-HX-8.0"
doc_type: "release_note"
product: "Helix HX-5000"
version: "8.0"
version_family: "8.0"
---
# Helix HX-5000 release 8.0: release notes

## Overview
Helix HX-5000 release 8.0 focuses on control-plane stability and operational recovery in stacked and EVPN deployments. The release adds improvements to EVPN type-5 route refresh handling, faster and more deterministic stack failure detection, and cleanup of routing-process memory management under repeated control-plane churn. In the 7.6 train, these changes address transient stack separation during heartbeat jitter, loss of type-5 advertisement after anycast gateway MAC movement, and memory growth following repeated EVPN route-refresh activity. Operators should expect no intended data-plane feature changes, but should validate stack behavior, EVPN route propagation, and baseline resource utilization after upgrade.

## New features
### EVPN type-5 refresh fixes
This release corrects EVPN type-5 route refresh handling so advertised prefixes remain present after control-plane events such as anycast gateway MAC movement. The change reduces the risk of stale refresh state suppressing type-5 advertisements in VXLAN/EVPN fabrics. No new configuration is required, but TAC recommends verifying route advertisement with show commands after any gateway MAC change.

### stack failure detection
Stack failure detection has been tightened so transient heartbeat jitter on long interconnect runs is less likely to trigger a brief member separation event. The switch now distinguishes between short transport disruption and true member loss more reliably. Existing stack configurations remain valid, but operators should review cabling quality and monitor show stack output after upgrade.

### memory management cleanup
This release includes memory management cleanup in the routing process to reduce growth observed after repeated EVPN route-refresh events. The update improves reclaim behavior under sustained control-plane churn and helps preserve headroom for routing and adjacency processing. No configuration changes are required, but operators should establish a pre- and post-upgrade baseline for memory utilization.

## Resolved issues
- KB-6104: HX-5000 7.6 stack members briefly separate after dual-path heartbeat jitter on long cable runs (%STACK-3-SPLIT-BRAIN)
- KB-6108: HX-5000 7.6 EVPN type-5 routes stop advertising after anycast gateway MAC move (%EVPN-4-RT5-STALL)
- KB-6112: HX-5000 7.6 routing process leaks memory after repeated EVPN route-refresh events (%MEM-4-LEAK)

## Known issues
- KB-6110: HX-5000 8.0 multicast replication can starve uplink buffers during short bursts. Workaround: Limit multicast fanout on the busiest leafs, or move replication-heavy workloads onto a separate uplink group so the shared buffer pool is not exhausted. If the burst is predictable, schedule the traffic outside congestion-sensitive windows.

## Compatibility
Release 8.0 is supported as an upgrade from HX-5000 release 7.6 and is intended for existing 7.6 hardware and configurations. Interoperability with adjacent routing, stacking, LACP, spanning tree, and VXLAN/EVPN peers is preserved, although environments that depend on aggressive route-refresh behavior should be validated after upgrade. No configuration syntax changes are required, and existing hierarchical configuration entered with configure terminal remains compatible. Any temporary operational variance is expected to be limited to post-upgrade state convergence and should be verified with show stack, show interfaces transceiver detail, and EVPN routing status commands.

## Upgrade notes
Supported direct upgrade path from 7.6. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export any operational state you need for rollback comparison, including show stack and show interfaces transceiver detail output.
2. Verify the 8.0 image checksum and confirm sufficient flash and bootloader space before scheduling the change.
3. Plan a maintenance window long enough for image installation, reload, and post-upgrade convergence of stacking and EVPN control-plane state.
4. Upgrade one stack member or a staged subset first if your deployment model allows it, then complete the remaining members after the first unit returns to service.
5. After reload, confirm stack membership, EVPN type-5 advertisement, and routing process health with show stack and related route verification commands.
6. Monitor logs, memory utilization, and interface counters for at least one convergence interval and confirm there are no unexpected member separations or route-refresh stalls.
