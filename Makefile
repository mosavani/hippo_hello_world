##
## hippo_hello_world — Build, test, and deploy targets
##
## Helm chart lives in hippo_k8s-service. This repo owns the app image
## and its service-settings values files consumed by ArgoCD.

APP_NAME   := hippo-hello-world
IMAGE_REPO ?= ghcr.io/mosavani/hippo-hello-world
IMAGE_TAG  ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")
IMAGE      := $(IMAGE_REPO):$(IMAGE_TAG)
PORT       ?= 8080
NAMESPACE  ?= default
RELEASE    ?= hippo-hello-world

# ── Phony targets ──────────────────────────────────────────────────────────
.PHONY: help build push run stop test clean

# ── Help ───────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  hippo_hello_world — available targets"
	@echo ""
	@echo "  Testing"
	@echo "    test            Run Python unit tests (pytest)"
	@echo ""
	@echo "  Docker"
	@echo "    build           Build the container image"
	@echo "    push            Push image to registry (set IMAGE_REPO)"
	@echo "    run             Run the container locally on port $(PORT)"
	@echo "    stop            Stop the local container"
	@echo ""
	@echo "  Vars: IMAGE_REPO=$(IMAGE_REPO)  IMAGE_TAG=$(IMAGE_TAG)"
	@echo "        NAMESPACE=$(NAMESPACE)    RELEASE=$(RELEASE)"
	@echo ""

# ── Testing ────────────────────────────────────────────────────────────────
test:
	pip install -q pytest && \
	python -m pytest tests/unit/ -v

# ── Docker ─────────────────────────────────────────────────────────────────
build:
	docker build \
	  --build-arg BUILD_DATE="$(shell date -u +%Y-%m-%dT%H:%M:%SZ)" \
	  --build-arg GIT_SHA="$(IMAGE_TAG)" \
	  -t $(IMAGE) \
	  -t $(IMAGE_REPO):latest \
	  .

push: build
	docker push $(IMAGE)
	docker push $(IMAGE_REPO):latest

run:
	docker run --rm -d \
	  --name $(APP_NAME) \
	  -p $(PORT):8080 \
	  -e APP_ENV=development \
	  $(IMAGE_REPO):latest
	@echo "App running → http://localhost:$(PORT)"
	@echo "  curl http://localhost:$(PORT)/"
	@echo "  curl http://localhost:$(PORT)/health"
	@echo "  curl http://localhost:$(PORT)/ready"
	@echo "  curl http://localhost:$(PORT)/metrics"

stop:
	docker stop $(APP_NAME) 2>/dev/null || true

# ── Cleanup ────────────────────────────────────────────────────────────────
clean:
	docker rmi $(IMAGE) $(IMAGE_REPO):latest 2>/dev/null || true
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
