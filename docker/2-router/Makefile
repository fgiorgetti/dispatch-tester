DISPATCHBRANCH?=master
PROTONBRANCH?=master

all: images install-venv test
	@echo Preparing all steps

stop-containers:
	@echo Stopping and removing containers
	docker stop `docker ps -a` 2> /dev/null || true
	docker rm `docker ps -qa` 2> /dev/null || true
	docker rmi dispatch-tester/router1:1 || true
	docker rmi dispatch-tester/router2:1 || true

images: stop-containers
	@echo Building QPID Dispatch Images
	@echo QPID Dispatch branch: $(DISPATCHBRANCH)
	@echo QPID Proton branch: $(PROTONBRANCH)
	./set-up.sh -d $(DISPATCHBRANCH) -p $(PROTONBRANCH)

install-venv:
	@echo Setting up python environment
	virtualenv venv
	. venv/bin/activate && pip install -r requirements.txt

test:
	@echo Running tests
	mkdir results || rm results/*
	. venv/bin/activate && pytest -s -v --junit-xml=results/2-router.junit.xml tests/test_smoke_01.py

.PHONY: test install-venv images stop-containers all

