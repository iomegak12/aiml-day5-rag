---
doc_id: "RN-NF-5.2.2"
doc_type: "release_note"
product: "Nimbus NF-300"
version: "5.2.2"
version_family: "5.2"
---
# Nimbus NF-300 release 5.2.2: release notes

## Overview
Nimbus NF-300 release 5.2.2 focuses on session-processing stability, high-availability recovery behavior, and TLS inspection cache handling. This release adds session-table rebalance tuning to improve distribution under asymmetric routing, refines HA recovery sequencing after a failover or split-brain event, and introduces controls for TLS inspection cache behavior. The primary quality objective is to reduce uneven session placement and improve recovery consistency in environments with concentrated traffic, large-prefix routing, and active HA pairs. Existing VPN, session-table, and SSL inspection deployments continue to be supported, but the known TLS cache eviction issue and the brief IPsec blackhole condition with matching DPD and rekey timers remain present.

## New features
### Session-table rebalance tuning
This release adds tuning for session-table rebalance behavior so the firewall can redistribute sessions more evenly when asymmetric routing is present. The change is intended for deployments that see concentrated traffic patterns or large-prefix flows that can skew session ownership on a single node. No new configuration mode is required, but administrators should review session-table counters after enabling asymmetric routing or changing route advertisement behavior.

### HA recovery sequencing
5.2.2 refines the order in which the active and standby units recover state after failover, split-brain resolution, and sync restoration. The updated sequencing reduces the risk of stale or prematurely reinstalled session state during HA recovery. Existing HA configuration syntax is unchanged, but operators should verify peer state with show ha status after maintenance or an unplanned transition.

### TLS inspection cache controls
This release introduces controls for TLS inspection cache behavior so administrators can better manage cache retention and eviction under certificate churn. The new controls are intended to reduce unexpected inspection behavior in environments with frequent certificate updates or high connection turnover. Configuration is committed from config mode and should be validated with inspection and session counters after deployment.

## Resolved issues
- KB-3103: Nimbus NF-300 5.0.9: standby drops replicated sessions after split-brain recovery (%HA-4-RSYNC_STALE_SEQ)
- KB-3109: Nimbus NF-300 5.2.0 uneven session-table distribution with asymmetric routing on concentrated /24 traffic (%SESSION-4-HASH_SKEW)
- KB-3110: Nimbus NF-300 5.2.0 session-table imbalance after enabling asymmetric routing on large-prefix traffic (%SESSION-4-HASH_SKEW)

## Known issues
- KB-3106: Nimbus NF-300 5.2.0 and 5.2.2: outbound TLS sessions intermittently bypass inspection after certificate cache eviction. Workaround: Increase the certificate cache size so eviction stays below 1,000 entries per hour, or disable outbound inspection for the affected server group until a fix is applied. Restarting SSL inspection clears the stale pointers temporarily.
- KB-3112: Nimbus NF-300 5.2.2: route-based IPsec tunnels may briefly blackhole traffic when dpd and rekey timers are both 10 seconds. Workaround: Stagger the timers so DPD is at least 3 seconds shorter or longer than the rekey interval, for example `crypto ikev2 dpd 10 3` with a 300-second rekey. Avoid setting both timers to the same 10-second value on route-based tunnels.

## Compatibility
Release 5.2.2 is supported as an upgrade from Nimbus NF-300 5.2.0, and the 5.0 and 5.1 family releases listed for this train are also compatible upgrade sources when following the standard staged path. Hardware support remains unchanged for the NF-300 platform family, and existing IPsec/IKEv2, HA, session-table, SSL inspection, firmware update, and threat-prevention configurations are retained. Interoperability behavior is unchanged except where noted by the session rebalance, HA recovery, and TLS cache updates; no required configuration syntax changes are introduced, although post-upgrade validation is recommended for asymmetric-routing, HA, and TLS inspection deployments. Known issues related to TLS cache eviction and the DPD/rekey timing interaction remain present in this release.

## Upgrade notes
Supported direct upgrade path from 5.2.0. Back up the configuration before upgrading and review the known issues above.

1. Back up the current configuration and export any security policy, certificate, and VPN material required for recovery.
2. Verify the 5.2.2 image checksum and signature on the management station before copying it to the firewall.
3. Schedule a maintenance window and confirm current HA and tunnel state with show ha status and show crypto ikev2 sa.
4. Upgrade the standby unit first in a high-availability pair, allow it to boot fully, and confirm synchronization before promoting or failing over to it.
5. Upgrade the active unit after the standby is healthy, then commit any required configuration changes from config mode if you are enabling the new session, HA, or TLS cache controls.
6. After both units are upgraded, validate forwarding and inspection with show session table summary, show ha status, and representative VPN and SSL inspection checks.
