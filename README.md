This directory contains an SDN router implementation that routes packets based on ethernet addresses. The router consists of 4 ryu applications:

# Modules

 - init.py maintains the permanent flows on each switch.
 - broadcast.py builds and maintains a broadcast tree. To broadcast a packet it should be send to the broadcast group table entry
 - router.py monitors packets and tries to learn on what switch/port a mac address is connected. If it learns a mac address it adds flows to all switches to efficiently route packets there.
 - port-security.py also learns switch/port locations of mac addresses and shuts off a port when there are more than 8 mac addresses learned from the same port to try to prevent a possible dos attack on the controller.

# Flow tables
Entry flow table, this flow table decides what port a packet should be send out of. If the switch doesn't know an output port broadcast is using group table 0.

Priority | Amount | Module | Name | Match | Instructions
---------|--------|--------|------|-------|-------------
20 | 1 per learned local mac | router.py | Locally learned mac forwarding rules | eth.dst == learned mac | goto-table(1) AND write-action(output port)
10 | 1 per learned foreign mac | router.py | Foreign learned mac forwarding rules | eth.dst == learned mac | goto-table(1) AND write-action(output port)
0  | 1 | init.py | Table miss entry | everything | goto-table(1) AND write-action(group 0)

Second flow table, this flow table looks up if the source ethernet address is known so the packet isn't forwarded to the controller without containing new information. This ensures the controller only receives packets of which it doesn't know the ethernet address. A switch also shouldn't forward packets to the controller it received from other switches since the source port would be wrong.

Priority | Amount | Module | Name | Match | Instructions
---------|--------|--------|------|-------|-------------
20 | 1 per learned mac | router.py | Learned mac rules | eth.src == learned mac | No actions
10 | 1 per connected switch | broadcast.py | Broadcasted forwarding rule | in port == other switch | No action
0  | 1 | init.py | Table miss entry | everything | apply-action(output controller)

Group table, this table only has 1 entry with the ports to forward on for broadcasting packets.

Identifier | Module | Name | Type | Buckets
-----------|--------|------|------|--------
0 | broadcast.py | Broadcast group | all | {Output port1, Output port2, ...}
