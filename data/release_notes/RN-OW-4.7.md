---
doc_id: "RN-OW-4.7"
doc_type: "release_note"
product: "Orion OW-20"
version: "4.7"
version_family: "4.7"
---
# Orion OW-20 release 4.7: release notes

## Overview
Orion OW-20 release 4.7 focuses on controller stability in AP onboarding, redundancy state exchange, and AAA attribute handling. This release adds improved AP join retry handling for transient failures during controller admission, refines redundancy synchronization to reduce state mismatches after role changes, and normalizes RADIUS attributes before policy evaluation to improve interoperability with AAA servers and access policies. The release also includes a defect fix for AP joins that were rejected when the join request contained a zero-length RF profile TLV. Operators should note the remaining known issue affecting AP join retries after radio capability revalidation.

## New features
### AP join retry handling
The controller now retains and replays AP join retries more reliably when the initial join attempt fails due to transient control-plane or timing conditions. This reduces unnecessary AP disconnect/reconnect cycles during controller admission and recovery events. No configuration change is required, but operators should monitor join counters during staged rollouts if APs are in a marginal RF or management-network state.

### redundancy sync improvements
Redundancy synchronization between peers has been tightened to reduce stale or incomplete state after switchover and resynchronization events. The controller now converges configuration and operational data more consistently, which improves failover behavior in active/standby deployments. Existing redundancy settings remain valid, but TAC recommends validating peer health and sync status after upgrade.

### RADIUS attribute normalization
The controller now normalizes selected RADIUS attributes before they are matched against authorization and policy logic. This improves interoperability with servers that format equivalent attributes differently and reduces policy mismatches during 802.1X authentication. Administrators do not need to change existing server profiles, but custom authorization rules should be reviewed if they depend on exact attribute string formatting.

## Resolved issues
- KB-4101: Orion OW-20 4.6 rejects AP joins when the join request includes a zero-length RF profile TLV (%CAPWAP-3-JOIN_REJECT)

## Known issues
- KB-4102: Orion OW-20 4.7 may drop AP join retries after radio capability revalidation. Workaround: Reduce the AP join retry interval from 5 seconds to 2 seconds so the controller keeps the transaction active long enough for revalidation. If the APs are remote, also verify one-way latency is under 80 ms and packet loss is below 1%.

## Compatibility
Release 4.7 is supported as an upgrade from Orion OW-20 4.6 on supported OW-20 hardware. It is intended to remain interoperable with existing APs, RADIUS/802.1X infrastructure, guest portal deployments, and roaming features already used in 4.6. Configuration is preserved across upgrade, with no required syntax changes for controller-wide CLI objects; however, redundancy and AAA policies should be revalidated after the upgrade, especially in environments that depend on exact RADIUS attribute formatting or are sensitive to AP join timing.

## Upgrade notes
Supported direct upgrade path from 4.6. Back up the configuration before upgrading and review the known issues above.

1. Back up the controller configuration and export any operational records needed for rollback validation.
2. Verify the 4.7 image checksum and confirm sufficient flash space before scheduling the upgrade.
3. Schedule a maintenance window and place the controller in a controlled state to minimize AP join activity during the image switch.
4. Upload the 4.7 image to the controller, set it as the boot image, and perform the upgrade from the controller CLI.
5. After reboot, confirm controller status, redundancy state, AP join counts, and RADIUS authentication success with show ap summary, show client detail <mac>, and the relevant redundancy status command.
6. If the deployment uses a peer controller, verify synchronization completion before returning the controller to service.
