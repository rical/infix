#!/bin/sh
#                      vlan1
#                ______/____
#               [____br0____]
#               /  /   \    \
#     eth0  eth1 eth2 eth3  lag0
#                           /  \
#                        eth4  eth5
#
# - Bridge with five bridge ports, one of which is a lag, and VLAN interface
# - Move a port from lag to bridge
# - Remove VLAN interface from bridge and remove bridge
#

TEST_DIR=$(dirname "$0")
. "$TEST_DIR/lib.sh"

################################################
say "Verify bringup of bridge with three ports and an upper VLAN interface"

create_iface eth0 10.0.0.1/24
create_iface eth1
create_iface eth2
create_iface eth3
create_iface eth4
create_iface eth5

create_lag lag0 "" eth4 eth5

create_bridge br0 "vlan_filtering 1" eth1 eth2 eth3 lag0
bridge_init br0 br0 1 2 3

create_vlan_iface vlan1 br0 1 192.168.1.1/24
netdo

#ip -d -j link show eth4 |jq -r '.[].master'
#ip -d link show
#bridge -d link show
#bridge -d vlan show

assert_bridge_ports br0 true eth1 eth2 eth3 lag0
assert_iface br0
assert_iface vlan1 192.168.1.1/24
assert_lag_ports lag0 true eth4 eth5

################################################
sep
say "Verify moving a port from lag0 to br0"

del_lagport lag0 eth4
init_next_gen eth0 eth1 eth2 eth3 eth4 eth5 lag0 br0 vlan1
init_deps br0 eth1 eth2 eth3 lag0
init_deps lag0 eth5
add_brport br0 eth4

netdo

assert_lag_ports lag0 true eth5
assert_lag_ports lag0 false eth4

assert_bridge_ports br0 true eth1 eth2 eth3 eth4 lag0
assert_iface br0

################################################
sep
say "Verify removing VLAN interface (vlan1) and bridge (br0)"
remove_iface vlan1
remove_iface br0
init_next_gen eth0 eth1 eth2 eth3 eth4 eth5 lag0

netdo

for iface in eth0 eth1 eth2 eth3 eth4 lag0 eth5; do
    assert_iface $iface
done
