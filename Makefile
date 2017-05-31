# Set RYU_PATH to a path to a ryu installation
RYU_PATH = ../ryu

# I needed to run this controller in parallel a few times, which
# is why there are 3 targets that startup this application. Target
# run1 runs the controller on the default openflow port and the other
# targets, run2 and run3, use port 6653 and 6654 respectively.

MODULES = init.py broadcast.py router.py
FLAGS1  = --observe-links --ofp-tcp-listen-port=6633
FLAGS2  = --observe-links --ofp-tcp-listen-port=6653
FLAGS3  = --observe-links --ofp-tcp-listen-port=6654

# The lines below enable the ryu topology visualizer, you can disable
# this application by removing the section below or make the if below
# evaluate to false.
ifeq (false, true)
MODULES := ${RYU_PATH}/ryu/app/gui_topology/gui_topology.py ${MODULES}
FLAGS1  += --wsapi-port=8080
FLAGS2  += --wsapi-port=8081
FLAGS3  += --wsapi-port=8082
endif

.PHONY: run1 run2 run3
run1:
	PYTHONPATH=${RYU_PATH} ${RYU_PATH}/bin/ryu-manager ${FLAGS1} ${MODULES}
run2:
	PYTHONPATH=${RYU_PATH} ${RYU_PATH}/bin/ryu-manager ${FLAGS2} ${MODULES}
run3:
	PYTHONPATH=${RYU_PATH} ${RYU_PATH}/bin/ryu-manager ${FLAGS3} ${MODULES}
