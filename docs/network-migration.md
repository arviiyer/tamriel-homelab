# The first network migration

[Home](../README.md) · [Networking](../networking/README.md)

My first segmentation attempt in March 2026 combined two changes: adding client
VLANs and moving nine infrastructure hosts into new subnets. It was rolled back.

The immediate failure was assigning the proposed management VLAN interface the
same subnet as the existing untagged LAN interface. OPNsense could not use both
interfaces for that network, and administration access was lost.

For the next attempt, I left the infrastructure LAN in place and added the
trusted, work, IoT, and guest networks separately. OPNsense handled their routing
and DHCP; UniFi carried the VLANs and assigned the wireless networks. The media
VM later received its own segment.

One follow-up was Pi-hole's listening mode. DNS worked from its own network but
needed an explicit change to accept routed client queries, with the firewall
limiting which networks could reach it.

The useful lesson was to separate Layer 2 transport, DHCP/DNS, firewall policy,
and host address changes. Check a client on the new network at each stage before
moving an existing service. The management/server split is still future work;
the [current network notes](network-and-identity.md) describe what is in place.
