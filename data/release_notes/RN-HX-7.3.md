---
doc_id: "RN-HX-7.3"
doc_type: "release_note"
product: "Helix HX-5000"
version: "7.3"
version_family: "7.3"
---
# Helix HX-5000 release 7.3: release notes

## Overview
Helix HX-5000 release 7.3 focuses on operational stability in the core switching fabric. This release adds stack election optimization, improves transceiver polling behavior to reduce false optics alarms, and expands visibility into LACP neighbors for faster fault isolation during link aggregation events. Quality work in this release also addresses a 7.2 issue that could cause SFP28 link drops accompanied by DOM bias current spikes and remote loss-of-signal alarms. Administrators should expect the same configuration model as 7.2, with no required changes to existing switch, stacking, or port-channel definitions.

## New features
### stack election optimization
The stack election process has been refined to reduce unnecessary master changes during boot and link transitions. This change improves stability in stacks that experience brief control-plane interruptions or member restart events. Existing stack configuration is retained and no new commands are required.

### transceiver polling stabilization
Transceiver DOM polling has been stabilized to avoid transient threshold excursions that could trigger misleading optical alarms. This improves the accuracy of interface health reporting under load and reduces false-positive remote LOS conditions. The feature is transparent to configuration and applies to supported optics when using standard interface monitoring commands.

### LACP neighbor visibility
The release adds enhanced visibility into directly connected LACP neighbors so operators can confirm partner identity and aggregation state more quickly. This is useful during port-channel troubleshooting, especially when multiple members flap or negotiate unexpectedly. No protocol settings are changed; the enhancement is exposed through existing operational show output.

## Resolved issues
- KB-6101: HX-5000 7.2 SFP28 link drops with DOM bias current spike and remote LOS alarms (%TRANSCEIVER-4-LOS)

## Known issues
- KB-6103: HX-5000 stack master election oscillates in 7.3 when stack cables negotiate at mixed speed. Workaround: Use matched-length stack cables between all members and keep control-plane load below 60 percent until the software is upgraded. If possible, pin the desired master with a higher priority value and avoid adding or removing members during the unstable period.

## Compatibility
Release 7.3 is supported as an upgrade from HX-5000 release 7.2 on the same hardware platforms in the 7.x family. Configuration is forward-compatible with 7.2, and no syntax changes are required for existing stacking, spanning tree, LACP, or interface optics settings. Interoperability behavior remains aligned with standard Ethernet, LACP, and transceiver monitoring expectations; however, operators should review stack behavior in environments with mixed-speed stack links, as a known issue can still affect master election in that condition. No planned configuration migration steps are required beyond the normal software upgrade process.

## Upgrade notes
Supported direct upgrade path from 7.2. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export any local logs or diagnostics before starting the upgrade.
2. Verify the 7.3 image checksum and confirm the image is present in the boot repository.
3. Schedule a maintenance window and notify stakeholders, especially if the switch is participating in a stack or port-channel critical path.
4. Upgrade the switch to 7.3 using the standard image activation procedure, then reload during the approved window.
5. After the system returns to service, verify stack state, interface health, transceiver status, and LACP neighbor information with operational show commands.
6. Monitor the device for link flaps, stack election changes, and optical alarms for an initial stabilization period after cutover.
