---
doc_id: "RN-NF-5.0.8"
doc_type: "release_note"
product: "Nimbus NF-300"
version: "5.0.8"
version_family: "5.0"
---
# Nimbus NF-300 release 5.0.8: release notes

## Overview
Nimbus NF-300 5.0.8 is the first release covered for this platform and establishes the baseline firewall feature set, initial IKEv2/IPsec and high-availability capabilities, and HTTPS-based image staging for future maintenance operations. The release is focused on bringing the platform into service with the core control-plane and data-plane functions required for enterprise deployments. Operationally, administrators should validate VPN and HA behaviour in their environment, with particular attention to IKEv2 rekeying and staged software updates. This release also serves as the starting point for the 5.0 maintenance train, so configuration and upgrade planning should assume later point releases may introduce fixes and behavioural changes.

## New features
### Baseline NF-300 firewall services
This release introduces the core firewall service set for the Nimbus NF-300, including stateful packet inspection, policy-based access control, session tracking, and common logging primitives. Configuration is performed in config mode and committed explicitly, so baseline policy, zone, address, and service objects should be validated after initial deployment.

### Initial IKEv2 and HA implementation
Initial support is provided for IKEv2 site-to-site VPNs and high availability operation on the NF-300. Administrators can validate tunnel establishment with 'show crypto ikev2 sa' and HA health with 'show ha status'; the initial implementation supports standard deployment patterns, but rekey and failover behaviour should be tested in maintenance windows before production cutover.

### HTTPS image staging
This release adds HTTPS-based image staging so software can be downloaded to the appliance over TLS before an upgrade window. The staged image is stored locally for later activation, which reduces exposure to transfer interruptions during maintenance; administrators should verify image integrity after download and before scheduling the reboot step.

## Resolved issues
- None

## Known issues
- KB-3101: Nimbus NF-300 5.0.8 and 5.0.9: ikev2 child-sa renegotiation fails after pfs group change when rekey traffic is active. Workaround: Keep the PFS group unchanged on both peers, or disable child SA rekey and force a manual tunnel restart during a maintenance window. If you must change the group, apply the same group on both sides and clear the SA after the change.
- KB-3104: Nimbus NF-300 5.0.8: boot loader rejects a valid 5.0.9 image after HTTPS stage download. Workaround: Use SCP or USB staging so the image is written without HTTPS padding, or upgrade first through an intermediate loader that understands the 4 KB-aligned payload. Verify the image hash before scheduling the reboot.

## Compatibility
Nimbus NF-300 5.0.8 is the first release in the covered train and should be treated as the baseline for forward upgrades within the 5.0 family. Supported upgrade sources for this release are not applicable because no earlier NF-300 release is covered here; later maintenance releases in the 5.0, 5.1, and 5.2 families are expected to follow the normal in-family upgrade path and preserve existing configuration objects unless explicitly changed by a later release. The platform interoperates with standard IKEv2/IPsec peers and HA designs that use common routing and failover behaviour, but administrators should test VPN rekeying, session sync, and staged-image workflows in their environment. Existing configurations created on this release should be exported and retained before upgrade planning, because future releases may introduce new defaults or validation rules.

## Upgrade notes
Initial release in this train. Back up the configuration before upgrading and review the known issues above.

1. Back up the running configuration and export any relevant certificates, VPN credentials, and HA state information to a secure location.
2. Verify the target image checksum after HTTPS staging and confirm the file is present on the appliance before scheduling the upgrade.
3. Plan a maintenance window and ensure both HA peers, if deployed, are in a known-good state before beginning the upgrade.
4. Stage the 5.0.8 image over HTTPS, then review the staging status and confirm there are no transfer or storage errors.
5. Commit any required configuration changes, reboot into the staged image, and allow the appliance to complete initial service startup.
6. After the upgrade, run 'show ha status', 'show crypto ikev2 sa', and 'show session table summary' to confirm cluster health, VPN establishment, and expected session capacity.
