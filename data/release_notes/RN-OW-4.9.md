---
doc_id: "RN-OW-4.9"
doc_type: "release_note"
product: "Orion OW-20"
version: "4.9"
version_family: "4.9"
---
# Orion OW-20 release 4.9: release notes

## Overview
Orion OW-20 release 4.9 adds targeted improvements for roaming continuity, guest access resilience, and DFS observability. The 802.11r fast transition path has been refined to reduce roam disruption under common controller and AP timing conditions, while guest portal session handling is improved for stations that move between APs during an active web-authenticated session. This release also adds clearer DFS event logging to help isolate radar detections, channel moves, and CAC-related transitions. In addition to these feature updates, 4.9 includes stability fixes for AP join processing and active-standby synchronization when the configuration database is large.

## New features
### 802.11r FT enhancements
This release improves fast transition handling for 802.11r-capable SSIDs by tightening controller-side state processing during roam authentication. The update is intended to reduce roam interruptions caused by timing-sensitive FT exchanges, especially in environments with aggressive roaming thresholds and mixed AP load.

### guest portal session continuity
Guest portal sessions now retain authentication state more consistently during client movement across APs in the same controller domain. This reduces the chance of an otherwise valid portal session being dropped during roam events, with no change to the standard guest policy or portal authentication workflow.

### DFS event logging
The controller now records additional DFS events to support troubleshooting of radar detection and channel evacuation behavior. New log entries make it easier to correlate channel moves, CAC completion, and DFS-triggered AP actions without changing DFS enforcement behavior.

## Resolved issues
- KB-4103: Orion OW-20 4.8 AP join stalls when the second capability exchange is delayed (ERR-APJ-4417)
- KB-4104: Orion OW-20 4.8 active-standby sync stalls when the configuration database exceeds 32,768 rows (%REDUNDANCY-4-SYNC_STALL)

## Known issues
- KB-4105: Orion OW-20 4.9 can delay 802.11r key installation during fast transition roaming. Workaround: Lower the client accounting interval to 60 seconds to reduce queue pressure, and keep controller CPU below 70% during roaming tests. For latency-sensitive SSIDs, disable 802.11r until the maintenance window.
- KB-4107: Orion OW-20 4.9 drops Vendor-Specific attribute 26 on Access-Challenge replies with more than 12 attributes. Workaround: Trim the RADIUS challenge to 12 or fewer attributes, or move the Vendor-Specific attribute earlier in the server response order. If possible, use a dedicated policy server that sends the tunneled attributes first.
- KB-4108: Orion OW-20 4.9 may omit Vendor-Specific attribute 26 from Access-Challenge processing when the reply contains 13 attributes. Workaround: Reduce the RADIUS challenge to 12 or fewer attributes, or reorder the server response so that the Vendor-Specific attribute appears earlier. If available, direct the request to a policy server that places the tunneled attributes first.
- KB-4109: Orion OW-20 guest portal sessions fail after standby failover when the portal cookie is pinned to the active node UUID. Workaround: Keep guest portal traffic pinned to the active node by disabling failover during guest registration windows, or clear the cookie and reauthenticate after each switchover. For planned maintenance, expire guest sessions before invoking redundancy failover.

## Compatibility
Release 4.9 is supported as an upgrade from Orion OW-20 4.8 on the same hardware platform and follows the standard controller-wide image upgrade process. Configuration from 4.8 is retained, and no manual conversion is required for existing WLANs, AP groups, redundancy settings, or RADIUS profiles. Interoperability with APs, 802.1X authentication servers, and guest portal clients is preserved, but operators should review any roaming-sensitive SSIDs that use 802.11r and confirm portal behavior after standby failover in environments that pin session cookies to controller identity. The release includes bug fixes for AP join and redundancy synchronization, but it does not change supported hardware models or require a new configuration schema.

## Upgrade notes
Supported direct upgrade path from 4.8. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export any local certificates, portal assets, and authentication profiles required for recovery.
2. Verify the 4.9 image checksum on the controller and confirm sufficient flash space before copying the image to the standby or maintenance node.
3. Schedule a maintenance window and place the controller pair or cluster into the planned upgrade state to avoid client disruption during image activation.
4. Upgrade the standby controller first, confirm it returns to in-sync state, and then fail traffic over before upgrading the former active node.
5. After both nodes are on 4.9, verify AP join status, client authentication, guest portal access, DFS log generation, and redundancy synchronization with show ap summary, show client detail <mac>, and the redundancy status commands used in your deployment.
