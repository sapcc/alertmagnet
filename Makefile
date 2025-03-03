SHELL       := /bin/sh
IMAGE       := keppel.eu-de-1.cloud.sap/ccloud/alertmagnet
VERSION     := 0.1

### Executables
DOCKER := docker

### Docker Targets 

.PHONY: build
build: 
	$(DOCKER) build -t $(IMAGE):$(VERSION) --no-cache --rm .

.PHONY: push 
push: 
	$(DOCKER) push $(IMAGE):$(VERSION)
