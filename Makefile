RYU_PATH=../ryu

.PHONY: run
run:
	PYTHONPATH=${RYU_PATH} ${RYU_PATH}/bin/ryu-manager --verbose --observe-links broadcast.py router.py port-security.py
