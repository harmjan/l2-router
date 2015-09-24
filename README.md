This directory contains an SDN router implementation that routes packets based on ethernet addresses. The router consists of 3 ryu applications:

# Modules

 - init.py maintains the permanent flows on each switch.
 - broadcast.py builds and maintains a broadcast tree. To broadcast a packet it should be send to a broadcast group table entry
 - router.py monitors packets and tries to learn on what switch/port a mac address is connected. If it learns a mac address it adds flows to all switches to efficiently route packets there.
 - port-security.py also learns switch/port locations of mac addresses and shuts off a port when there are more than 8 mac addresses learned from the same port to try to prevent a possible dos attack on the controller.

# Flow tables
Entry flow table, this flow table has to decide where a packet should be outputted.

Priority | Amount | Module | Name | Match | Instructions
---------|--------|--------|------|-------|-------------
40 | 1 per learned local mac | router.py | Locally learned mac forwarding rules | eth.dst == learned mac AND in port == learned in port | forward to second flow table AND forward to output port
30 | 1 per learned foreign mac | router.py | Foreign learned mac forwarding rules | eth.dst == learned mac AND in port == other switch | forward to output port
20 | 1 per connected switch | broadcast.py | Forwarding broadcast rule (maybe unnecesary) | in port == other switch | forward to broadcast group
10 | 1 | init.py | General broadcast rule (unnecesary) | eth.dst == broadcast address | forward to second flow table AND forward to broadcast group
0  | 1 | init.py | Table miss entry | ANY | forward to second flow table AND forward to broadcast group

Second flow table, this flow table looks up if the source ethernet address is known and if it isn't forward to the controller.

Priority | Amount | Module | Name | Match | Instructions
---------|--------|--------|------|-------|-------------
30 | 1 per learned mac | router.py | Learned mac rules | eth.src == learned mac | No actions
0  | 1 | init.py | Table miss entry | ANY | output to controller

Group table, this only has 1 entry with the ports to forward on for flooding.

Identifier | Module | Name | Type | Buckets
-----------|--------|------|------|--------
1 | broadcast.py | Broadcast group | all | {Output port1, Output port2, ...}
