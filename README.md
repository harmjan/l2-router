This directory contains an SDN router implementation that routes packets based on ethernet addresses. The router consists of 3 ryu applications:

 - setup.py maintains the permanent flows on each switch.
 - broadcast.py builds and maintains a broadcast tree. To broadcast a packet it should be send to a broadcast group table entry
 - router.py monitors packets and tries to learn on what switch/port a mac address is connected. If it learns a mac address it adds flows to all switches to efficiently route packets there.
 - port-security.py also learns switch/port locations of mac addresses and shuts off a port when there are more than 8 mac addresses learned from the same port to try to prevent a possible dos attack on the controller.

