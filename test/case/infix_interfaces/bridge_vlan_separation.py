#!/usr/bin/env python3
#    ,-------------------------------------,       ,-------------------------------------,       
#    |                          dut1:data2 |       | dut2:data2                          | 
#    |                      br0  ----------|-------|---------  br0                       |  
#    |                     /   \           |       |          /   \                      | 
#    |dut1:mgmt  dut1:data0     dut1:data1 |       | dut2:data0    dut2:data1  dut2:mgmt | 
#    '-------------------------------------'       '-------------------------------------'
#        |                |     |                            |     |                 | 
#        |                |     |                            |     |                 |
# ,-----------------------------------------------------------------------------------------,
# |  host:mgmt0  host:data0     host:data1          host:data2     host:data3   host:mgmt1  |
# |              [10.0.0.1]     [10.0.0.2]          [10.0.0.3]     [10.0.0.4]               |
# |                (ns10)         (ns11)              (ns20)         (ns21)                 |
# |                                                                                         |
# |                                        [ HOST ]                                         |
# '-----------------------------------------------------------------------------------------'          

import infamy

with infamy.Test() as test:
    with test.step("Initialize"):
        env = infamy.Env(infamy.std_topology("2x4"))
        dut1 = env.attach("dut1", "mgmt")
        dut2 = env.attach("dut2", "mgmt")

    with test.step("Configure a bridge with triple physical port"):
        _, tport10 = env.ltop.xlate("dut1", "data0")
        _, tport11 = env.ltop.xlate("dut1", "data1")
        _, tport12 = env.ltop.xlate("dut1", "data2")
        _, tport20 = env.ltop.xlate("dut2", "data0")
        _, tport21 = env.ltop.xlate("dut2", "data1")
        _, tport22 = env.ltop.xlate("dut2", "data2")

        dut1.put_config_dict("ietf-interfaces", {
            "interfaces": {
                "interface": [
                    {
                        "name": "br0",
                        "type": "infix-if-type:bridge",
                        "enabled": True,
                        "bridge": {
                            "vlans": {
                                "vlan": [
                                    {
                                        "vid": 10,
                                        "untagged": [ tport10 ],
                                        "tagged":   [ "br0", tport12 ]
                                    },
                                    {
                                        "vid": 20,
                                        "untagged": [ tport11 ],
                                        "tagged":   [ "br0", tport12 ]
                                    }
                                ]
                            }
                        }
                    },
                    {
                        "name": tport10,
                        "type": "infix-if-type:ethernet",
                        "enabled": True,
                        "infix-interfaces:bridge-port": {
                            "pvid": 10,
                            "bridge": "br0"
                        }
                    },
                    {
                        "name": tport11,
                        "type": "infix-if-type:ethernet",
                        "enabled": True,
                        "infix-interfaces:bridge-port": {
                            "pvid": 20,
                            "bridge": "br0"
                        }
                    },
                    {
                        "name": tport12,
                        "type": "infix-if-type:ethernet",
                        "enabled": True,
                        "infix-interfaces:bridge-port": {
                            "bridge": "br0",
                        }
                    }
                ]
            }
        })

        dut2.put_config_dict("ietf-interfaces", {
            "interfaces": {
                "interface": [
                    {
                        "name": "br0",
                        "type": "infix-if-type:bridge",
                        "enabled": True,
                        "bridge": {
                            "vlans": {
                                "vlan": [
                                    {
                                        "vid": 10,
                                        "untagged": [ tport20 ],
                                        "tagged":   [ "br0", tport22 ]
                                    },
                                    {
                                        "vid": 20,
                                        "untagged": [ tport21 ],
                                        "tagged":   [ "br0", tport22 ]
                                    }
                                ]
                            }
                        }
                    },
                    {
                        "name": tport20,
                        "type": "infix-if-type:ethernet",
                        "enabled": True,
                        "infix-interfaces:bridge-port": {
                            "pvid": 10,
                            "bridge": "br0"
                        }
                    },
                    {
                        "name": tport21,
                        "type": "infix-if-type:ethernet",
                        "enabled": True,
                        "infix-interfaces:bridge-port": {
                            "pvid": 20,
                            "bridge": "br0"
                        }
                    },
                    {
                        "name": tport22,
                        "type": "infix-if-type:ethernet",
                        "enabled": True,
                        "infix-interfaces:bridge-port": {
                            "bridge": "br0",
                        }
                    }
                ]
            }
        })

    with test.step("Ping host:data20 [10.0.0.3] from host:data10 [10.0.0.1] through <bridge-vlan-10>" \
                   " and host:data21 [10.0.0.4] from host:data11 [10.0.0.2] through <bridge-vlan-20>"):
        
        _, hport10 = env.ltop.xlate("host", "data10")
        _, hport11 = env.ltop.xlate("host", "data11")
        _, hport20 = env.ltop.xlate("host", "data20")
        _, hport21 = env.ltop.xlate("host", "data21")

        with infamy.IsolatedMacVlan(hport10) as ns10, \
             infamy.IsolatedMacVlan(hport11) as ns11, \
             infamy.IsolatedMacVlan(hport20) as ns20, \
             infamy.IsolatedMacVlan(hport21) as ns21:

            ns10.addip("10.0.0.1")
            ns11.addip("10.0.0.2")
            ns20.addip("10.0.0.3")
            ns21.addip("10.0.0.4")

            ns10.must_reach("10.0.0.3")
            ns11.must_reach("10.0.0.4")

            ns10.must_not_reach("10.0.0.4")
            ns11.must_not_reach("10.0.0.3")
            ns10.must_not_reach("10.0.0.2")
            ns11.must_not_reach("10.0.0.1")
                    
    test.succeed()
