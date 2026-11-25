---
doc_id: "RN-AR-9.2.0"
doc_type: "release_note"
product: "Aurora AR-900"
version: "9.2.0"
version_family: "9.2"
---
# Aurora AR-900 release 9.2.0: release notes

## Overview
Aurora AR-900 9.2.0 introduces three operational features focused on routing protocol resilience and IPv6 host-state visibility. OSPF now negotiates the database description MTU during adjacency formation, which reduces false adjacency failures caused by interface MTU differences. The IPv6 stack adds SLAAC lifetime tracking so operators can inspect preferred and valid lifetimes per learned prefix. Static routes that depend on recursive resolution now generate a notification when the resolving path changes, improving troubleshooting for underlay-dependent forwarding. This release also includes a defect fix for BGP next-hop resolution after underlay withdrawal, and it continues to address stability in routing and control-plane behaviour.

## New features
### OSPF DBD MTU negotiation
OSPF now compares the database description MTU during adjacency formation and uses the negotiated value rather than relying only on the local interface MTU. This reduces adjacency resets and stuck negotiations when peers have different, but operationally valid, MTU settings. No configuration is required, but operators should review any static MTU overrides on OSPF interfaces after upgrade.

### IPv6 SLAAC lifetime tracking
The IPv6 control plane now tracks the preferred and valid lifetimes learned through SLAAC and exposes them in operational output. This helps operators correlate address expiry with router advertisement timers and identify stale host addressing states. The feature is enabled by default and does not change the behavior of existing SLAAC clients.

### Recursive static-route notification
The system now generates a notification when a recursive static route changes resolution state, such as when the next-hop path is withdrawn or replaced. This improves visibility into underlay dependency changes and makes it easier to distinguish forwarding loss from protocol adjacency issues. Existing static route configuration is unchanged, but operators should expect additional log and event output when recursion flips.

## Resolved issues
- KB-2101: Aurora AR-900 9.1.4 and 9.1.6 BGP IPv4 next-hop stays unresolved after underlay route withdrawal (%BGP-4-NH-RESOLVE)

## Known issues
- KB-2103: Aurora AR-900 9.2.0 OSPF adjacency repeatedly resets on multiaccess networks with MTU mismatch. Workaround: Set a matching MTU on both sides or configure the neighbor on the interface as point-to-point if the topology permits. If changing MTU is not possible, use `ip ospf mtu-ignore` on both peers during the maintenance window.

## Compatibility
Aurora AR-900 9.2.0 is supported as an upgrade from 9.1.6 on the AR-900 hardware family. The release preserves existing BGP, BFD, OSPF, IPv6, QoS, control-plane protection, SNMP, NAT, and management configurations, although the new OSPF DBD MTU negotiation may alter adjacency establishment on links where peers advertise mismatched MTUs. Interoperability with adjacent routers should remain unchanged for standard RFC-compliant BGP, OSPFv2, and IPv6 SLAAC deployments, but operators should validate any environments that depend on non-default interface MTU values or recursive static routes tied to dynamic underlay paths. No configuration migration is required, and existing configuration files are retained during upgrade.

## Upgrade notes
Supported direct upgrade path from 9.1.6. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and capture current operational state, including 'show bgp summary', 'show bfd neighbors detail', 'show ospf neighbor', and 'show ipv6 interface'.
2. Verify the 9.2.0 image checksum and confirm sufficient flash and boot partition space before scheduling the change.
3. Plan a maintenance window and notify stakeholders, especially for sites using OSPF over links with known MTU variation or static routes that depend on recursive next-hop resolution.
4. Stage the image to the device, set the next-boot image, and perform the upgrade during the approved maintenance window.
5. After the device returns to service, confirm routing and forwarding stability with 'show bgp summary', 'show ospf neighbor', 'show ipv6 route', and 'show logging' for any new recursion or adjacency events.
6. If the environment uses redundant peers, verify convergence on the standby path before returning traffic to normal operation.
