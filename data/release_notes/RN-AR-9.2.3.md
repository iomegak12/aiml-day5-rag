---
doc_id: "RN-AR-9.2.3"
doc_type: "release_note"
product: "Aurora AR-900"
version: "9.2.3"
version_family: "9.2"
---
# Aurora AR-900 release 9.2.3: release notes

## Overview
Aurora AR-900 release 9.2.3 is a maintenance update for the 9.2 train that adds control-plane visibility and routing diagnostics while addressing queue-scheduling and routing-process stability issues seen in 9.2.1. The release introduces control-plane punt accounting for improved tracking of packets delivered to the CPU, adds BGP recursive route notification to improve operator awareness of recursive resolution changes, and includes scheduler fairness fixes to reduce starvation of best-effort traffic under bursty load. This release is intended for deployments that require better observability of punted traffic and improved operational stability during routing churn and microburst conditions.

## New features
### Control-plane punt accounting
This release adds accounting for packets punted to the control plane so operators can correlate CPU-bound traffic with forwarding events. The counters are exposed through operational show commands and increment on punt paths used by routing, neighbor discovery, and control-plane policing functions. No configuration is required to enable the counters, but existing monitoring systems may need updated pollers to consume the new fields.

### BGP recursive route notification
The BGP process now generates a notification when a recursive path changes state, including cases where the next hop depends on a static or IGP-learned route. This improves troubleshooting for route resolution changes that can affect best-path selection and forwarding. The feature is informational and does not alter BGP policy or routing decisions.

### Scheduler fairness fixes
This release corrects scheduler behavior that could allow strict-priority queues to dominate transmission during short microbursts. The fix improves service fairness for best-effort traffic without changing the queueing model or requiring configuration changes. Existing QoS policies remain valid, but traffic behavior under congestion should be revalidated after upgrade.

## Resolved issues
- KB-2105: Aurora AR-900 9.2.1 strict-priority queue can starve best-effort traffic during microbursts (%QOS-5-SCHED-DEFICIT)
- KB-2110: Aurora AR-900 9.2.1 routing process can spike to 95% CPU during repeated BGP soft clears (ERR-CPU-7781)

## Known issues
- KB-2106: Aurora AR-900 9.2.3 control-plane policer can undercount IPv6 ND punts during burst traffic. Workaround: Lower the IPv6 ND rate at the edge by enabling RA guard or storm control on the access VLAN, and reduce the control-plane policer to a conservative value such as 2,000 pps until the traffic source is identified. If necessary, shut the offending access port for 30 seconds to let neighbor state recover.
- KB-2107: Aurora AR-900 9.2.3 BGP next-hop remains unresolved after recursive static route changes. Workaround: Issue a soft clear of the affected BGP address family after changing recursive static routes. If you must avoid a clear, withdraw the old static route for at least 5 seconds before installing the replacement so the recursion engine rebuilds the dependency graph.
- KB-2112: Aurora AR-900 9.2.3 control-plane protection may miss IPv6 ND drops during traffic bursts. Workaround: Reduce IPv6 ND load at the edge by enabling RA guard or storm control on the access VLAN, and temporarily lower the control-plane policer to a conservative value such as 2,000 pps until the source is isolated. If needed, shut the offending access port for 30 seconds to allow neighbor state to recover.

## Compatibility
Aurora AR-900 9.2.3 is supported as an in-place upgrade from earlier 9.2 releases, including 9.2.1, and can be used on the same AR-900 hardware platforms supported by the 9.2 train. Configuration is forward-compatible within the 9.2 family; existing BGP, BFD, OSPF, IPv6, QoS, control-plane protection, SNMP, NAT, and system settings should be retained across the upgrade. The new punt accounting and BGP notification functions do not require new configuration statements, but external monitoring, log parsing, and performance baselines may need adjustment to account for additional counters and event messages. When upgrading from 9.1.x, validate the configuration after boot because feature defaults and operational counters may differ between major.minor families.

## Upgrade notes
Supported direct upgrade path from 9.2.1. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and save a copy of the current 9.2.1 image, including any boot variables and license files.
2. Verify the 9.2.3 image checksum and confirm adequate flash storage before copying the image to the device.
3. Schedule a maintenance window and reduce routing impact by draining nonessential traffic and confirming neighbor stability with commands such as 'show bgp summary' and 'show bfd neighbors detail'.
4. Upgrade the standby or inactive boot image first if the deployment uses redundant boot partitions, then set the next boot image to 9.2.3.
5. Reload the device and confirm that the system returns to service, then review 'show version', 'show interface counters', 'show bgp summary', and relevant control-plane logs for abnormal CPU, queue, or adjacency behavior.
6. After validation, update any external monitoring thresholds or scripts that rely on punt counters or BGP event messages.
