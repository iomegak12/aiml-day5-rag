---
doc_id: "RN-AR-9.2.1"
doc_type: "release_note"
product: "Aurora AR-900"
version: "9.2.1"
version_family: "9.2"
---
# Aurora AR-900 release 9.2.1: release notes

## Overview
Aurora AR-900 9.2.1 is a maintenance release for the 9.2 train that adds QoS scheduler credit handling, improves BGP soft-clear scaling, and expands OSPF adjacency interoperability. The release also addresses stability issues seen during OSPF adjacency formation on multiaccess networks with MTU mismatch and during upgrades from 9.1.x systems that have BGP add-path enabled. TAC recommends this release for sites that rely on dense route refresh activity, mixed-vendor OSPF peering, or tight QoS scheduling on edge-facing interfaces. The release does not change the general management model, but operators should validate queue behaviour and routing-process headroom after upgrade, especially where strict-priority traffic classes are used.

## New features
### QoS scheduler credits
Aurora AR-900 9.2.1 introduces scheduler credit accounting for QoS queues so transmit opportunities are tracked more consistently under variable line-rate load. This change is intended to improve fairness between service classes during sustained congestion and to reduce burst-induced scheduling drift. Existing class-map and policy-map configuration remains valid, but queue behaviour should be reviewed where strict-priority traffic is paired with best-effort classes.

### BGP soft-clear scaling
This release improves the handling of repeated BGP soft clears on routers with larger route tables and more frequent policy refresh activity. The routing process now reuses more soft-clear state and reduces avoidable churn during inbound or outbound route refresh operations. No configuration changes are required, but operators should continue to monitor control-plane CPU if soft clears are driven at high frequency by automation or test scripts.

### OSPF adjacency interop
Aurora AR-900 9.2.1 expands OSPF adjacency interoperability with peers that advertise differing interface MTU values on multiaccess segments. The adjacency state machine now tolerates common negotiation patterns seen in mixed environments and avoids unnecessary reset loops during initial exchange. Existing OSPF configuration is preserved, although TAC recommends verifying neighbor state and MTU consistency after upgrade on networks that include third-party or legacy peers.

## Resolved issues
- KB-2103: Aurora AR-900 9.2.0 OSPF adjacency repeatedly resets on multiaccess networks with MTU mismatch (%OSPF-4-ADJ-EXSTART)
- KB-2111: Aurora AR-900 9.1.x upgrade to 9.2.0 fails when BGP add-path is enabled (ERR-UPG-1307)

## Known issues
- KB-2105: Aurora AR-900 9.2.1 strict-priority queue can starve best-effort traffic during microbursts. Workaround: Cap the strict-priority class to 30% bandwidth or convert it to low-latency queueing with an explicit policer of 300 Mbps on 10 Gbps links. If possible, move bulk traffic to a separate egress interface to avoid shared scheduler contention.
- KB-2110: Aurora AR-900 9.2.1 routing process can spike to 95% CPU during repeated BGP soft clears. Workaround: Avoid repeated soft clears during peak update periods. If a refresh is required, prefer one hard clear during a maintenance window, or stage the clear after inbound route churn has settled for at least 60 seconds.

## Compatibility
Aurora AR-900 9.2.1 is supported as an in-train upgrade from 9.2.0 and as a direct upgrade target from 9.1.x releases, including systems using BGP add-path. Hardware support remains unchanged for the AR-900 platform family. Interoperability is unchanged for BGP, BFD, IPv6, NAT, SNMP, and control-plane protection features, except for the improved OSPF neighbour handling described above. Configuration syntax is preserved across the 9.2 train; however, operators should validate QoS policy behaviour after upgrade because the scheduler credit mechanism can change observed queue servicing under congestion without requiring any configuration migration.

## Upgrade notes
Supported direct upgrade path from 9.2.0. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and any relevant route-policy, QoS, and SNMP settings, and record current neighbor status with 'show bgp summary', 'show bfd neighbors detail', and 'show ospf neighbor'.
2. Verify the 9.2.1 image checksum and signature on your staging server, then copy the image to the device and confirm available storage before proceeding.
3. Schedule a maintenance window and ensure traffic engineering, failover, and monitoring systems are aware of the planned reboot and routing restart.
4. Upgrade a staged or non-production AR-900 first if available, then perform the production upgrade from 9.2.0 or 9.1.x using the normal software activation procedure.
5. After reboot, confirm system health and protocol convergence with 'show bgp summary', 'show ospf neighbor', 'show qos queue statistics', and 'show system resources'.
6. If the site uses strict-priority QoS or frequent BGP soft clears, monitor CPU and traffic behaviour for at least one convergence interval and adjust operational thresholds if required.
