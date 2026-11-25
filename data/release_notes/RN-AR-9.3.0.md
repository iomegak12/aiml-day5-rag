---
doc_id: "RN-AR-9.3.0"
doc_type: "release_note"
product: "Aurora AR-900"
version: "9.3.0"
version_family: "9.3"
---
# Aurora AR-900 release 9.3.0: release notes

## Overview
Aurora AR-900 9.3.0 adds three operational changes focused on address translation, control-plane visibility, and BGP convergence. NAT allocator aging now reclaims unused allocator state sooner, reducing stale allocation pressure after session churn. IPv6 control-plane protection accounting is improved so ND-related punts and drops are reflected more accurately during burst traffic, and BGP recursion re-notification causes next-hop resolution events to be re-evaluated when recursive static routes change. This release also includes fixes for control-plane policer accounting under burst IPv6 ND load and for BGP next-hop resolution after recursive static route updates. One known issue remains in dynamic NAT port-exhaustion reporting after session teardown.

## New features
### NAT allocator aging
The NAT allocator now ages unused translation allocator state after session teardown instead of retaining it until the next broader cleanup cycle. This reduces allocator growth in environments with short-lived sessions and frequent port reuse. No new configuration is required; existing NAT policies use the new aging behavior automatically.

### IPv6 control-plane protection accounting
Control-plane protection counters now account for IPv6 Neighbor Discovery punts and drops more accurately during burst traffic. This improves visibility when validating policer behavior with commands such as show control-plane protection statistics and related debug output. Existing control-plane protection configuration is unchanged, but counter deltas may differ from prior releases under high ND load.

### BGP recursion re-notification
BGP now re-evaluates and re-notifies affected paths when recursive static routes used for next-hop resolution change state. This improves convergence after static route add, remove, or metric changes that alter recursion results. No configuration syntax changes are introduced, but operators should expect additional next-hop resolution notifications during route recomputation.

## Resolved issues
- KB-2106: Aurora AR-900 9.2.3 control-plane policer can undercount IPv6 ND punts during burst traffic (ERR-CPP-4412)
- KB-2107: Aurora AR-900 9.2.3 BGP next-hop remains unresolved after recursive static route changes (%BGP-4-NH-RESOLVE)
- KB-2112: Aurora AR-900 9.2.3 control-plane protection may miss IPv6 ND drops during traffic bursts (ERR-CPP-4412)

## Known issues
- KB-2108: Aurora AR-900 9.3.0 dynamic NAT port exhaustion is reported incorrectly after session teardown. Workaround: Increase the NAT pool size or add at least one additional public address so the active allocator has headroom above the deferred-free window. If the traffic pattern is predictable, reduce the session churn by increasing application keepalive intervals to 60 seconds or more.

## Compatibility
Aurora AR-900 9.3.0 is supported for upgrade from any prior AR-900 release in the 9.1.x and 9.2.x families, including 9.2.3. Hardware compatibility is unchanged for supported AR-900 platforms, and existing BGP, BFD, OSPF, IPv6, QoS, SNMP, NAT, and control-plane protection configurations remain valid. Interoperability with adjacent routers is unchanged; however, BGP next-hop resolution events may be re-notified when recursive static routes change, which can alter operational logging without affecting protocol standards compliance. Review automation or monitoring that parses NAT port-exhaustion messages or control-plane counters, as the accounting behavior has changed in this release.

## Upgrade notes
Supported direct upgrade path from 9.2.3. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration, license files, and any local operational data before starting the upgrade.
2. Verify the 9.3.0 image checksum and confirm the image is present on the device storage.
3. Schedule a maintenance window and reduce routing impact if needed by confirming BGP/BFD/OSPF convergence state before upgrade.
4. Copy the 9.3.0 image to the standby storage location if required by your deployment method, then initiate the staged upgrade using the approved AR-900 procedure.
5. After reload, verify system health with show version, show bgp summary, show bfd neighbors detail, and show nat statistics.
6. Confirm control-plane and IPv6 behavior by checking control-plane protection counters and validating expected route resolution after any recursive static route changes.
