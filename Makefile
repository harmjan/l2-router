RYU_PATH=../ryu
MODULES=init.py broadcast.py router.py
FLAGS=--observe-links

.PHONY: run
run:
	PYTHONPATH=${RYU_PATH} ${RYU_PATH}/bin/ryu-manager ${FLAGS} ${MODULES}

.PHONY: deploy
deploy:
	ssh nas@controller 'rm l2-router -rf'
	ssh nas@controller 'mkdir l2-router'
	scp *.py nas@controller:~/l2-router
	scp Makefile nas@controller:~/l2-router
	ssh nas@controller
