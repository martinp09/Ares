SHELL := /usr/bin/env bash

.PHONY: help dev smoke api ui worker

help:
	@printf '%s\n' 'Targets:'
	@printf '%s\n' '  make dev    - print the local bootstrap commands for Ares, Mission Control, Trigger, and Hermes env'
	@printf '%s\n' '  make smoke  - run the lead machine smoke harness'
	@printf '%s\n' '  make api    - run the Ares FastAPI server on 127.0.0.1:8000'
	@printf '%s\n' '  make ui     - run the Mission Control Vite app'
	@printf '%s\n' '  make worker - run the Trigger worker'

dev:
	@./scripts/dev/boot-local.sh

smoke:
	@./scripts/dev/smoke.sh

api:
	@uv run --with uvicorn uvicorn app.main:app --host 127.0.0.1 --port 8000

ui:
	@npm --prefix apps/mission-control run dev

worker:
	@npm --prefix trigger run dev
