---
doc_id: "RN-AR-9.1.4"
doc_type: "release_note"
product: "Aurora AR-900"
version: "9.1.4"
version_family: "9.1"
---
# Aurora AR-900 release 9.1.4: release notes

## Overview
Aurora AR-900 release 9.1.4 introduces three routing-plane enhancements focused on BGP and BFD behavior. The release adds a BGP next-hop recursion cache to reduce repeated resolution work during route churn, a BFD transmit scheduler to improve timer handling under load, and BGP add-path session state to preserve session context across control-plane events. This first release in the 9.1 train is intended for early adopters validating routing and failover behavior in edge deployments. Operators should review the known issues before deployment, particularly the remaining BGP next-hop and BFD counter-wrap limitations and the upgrade constraint to later 9.2 software when add-path is enabled.

## New features
### BGP next-hop recursion cache
Aurora AR-900 9.1.4 adds a cache for BGP next-hop recursion results so repeated lookups do not re-evaluate the same underlay resolution path on every update. This reduces control-plane churn during route instability and can lower CPU usage in dense tables. No configuration changes are required to enable the cache.

### BFD transmit scheduler
This release introduces a transmit scheduler for BFD sessions to improve packet pacing when the system carries many concurrent sessions. The scheduler centralizes transmit timing and reduces jitter caused by competing control-plane tasks. Existing BFD configuration remains valid, but TAC recommends validating session timers after upgrade in deployments with aggressive detection intervals.

### BGP add-path session state
Aurora AR-900 9.1.4 now retains BGP add-path session state in the control plane so path-selection context is preserved across transient events. This improves session continuity for peers using add-path and reduces the likelihood of unnecessary path re-advertisement after a restart of routing processes. No additional configuration is required, but operators should confirm add-path behavior during maintenance windows.

## Resolved issues
- None

## Known issues
- KB-2101: Aurora AR-900 9.1.4 and 9.1.6 BGP IPv4 next-hop stays unresolved after underlay route withdrawal. Workaround: Clear the BGP process for the affected address family, or remove and re-add the underlay static/connected route so recursion is recomputed. If the path is critical, prefer a static discard route with a lower distance than the learned underlay during the maintenance window.
- KB-2102: Aurora AR-900 9.1.4 BFD sessions stop transmitting after 64-bit counter wrap on long-lived peers. Workaround: Restart the BFD process or reload during a maintenance window before the platform uptime reaches 49 days. As a temporary containment measure, increase the detection multiplier to 5 and the transmit interval to 200 ms on noncritical peers.
- KB-2111: Aurora AR-900 9.1.x upgrade to 9.2.0 fails when BGP add-path is enabled. Workaround: Disable BGP add-path before starting the upgrade, then re-enable it after the router is running 9.2.0. If the box is already stuck in rollback, complete the boot on the previous release, remove add-path configuration, and retry the upgrade.

## Compatibility
Aurora AR-900 9.1.4 is the first release covered in the 9.1 train and is intended for AR-900 hardware only. Supported upgrade sources for this release are not defined because no earlier Aurora AR-900 release is included in this train. The release interoperates with standard BGP, BFD, OSPF, IPv6, QoS, SNMP, NAT, and control-plane protection configurations already present on the platform, but deployments using BGP add-path should note the documented upgrade limitation to 9.2.0. Configuration syntax is preserved for existing features; however, operators should review route-policy, BFD timer, and BGP add-path settings before and after upgrade to confirm expected behavior.

## Upgrade notes
Initial release in this train. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and capture current operational state, including 'show bgp summary', 'show bfd neighbors detail', and any platform health output used for baseline comparison.
2. Verify the 9.1.4 image checksum and signature against the published image file before transferring it to the AR-900.
3. Schedule a maintenance window and confirm that routing convergence impact is acceptable for the site, especially where BGP add-path or tight BFD timers are in use.
4. Stage the image on the device, then perform the upgrade using the standard AR-900 software installation procedure and allow the system to reload completely.
5. After the reload, confirm software version, validate BGP and BFD session status, and check that routing adjacencies and next-hop resolution are restored as expected.
6. Monitor logs and counters for a short validation period and compare post-upgrade behavior with the baseline, paying particular attention to BGP add-path peers and BFD transmit continuity.
