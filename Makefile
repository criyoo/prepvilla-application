SHELL := /bin/bash

TF ?= terraform
WORKSPACE ?= dev
ENVIRONMENT ?= $(WORKSPACE)
WORKSPACE_VARS := -var-file=envs/$(ENVIRONMENT).tfvars
ENV_FILE := envs/secrets/.env.$(ENVIRONMENT)
ENCRYPTED_ENV_FILE := $(ENV_FILE).age
SOURCE := .
LOAD_ENV := set -a && $(SOURCE) $(ENV_FILE) && set +a

AWS_PROFILE ?= root
AWS_DEFAULT_PROFILE ?= $(AWS_PROFILE)
AWS_WORKLOAD_PROFILE ?= $(WORKSPACE)-prepvilla
AWS_SDK_LOAD_CONFIG ?= 1


.PHONY: api web migrate admin

export WORKSPACE
export ENVIRONMENT
export AWS_PROFILE
export AWS_DEFAULT_PROFILE
export AWS_WORKLOAD_PROFILE
export AWS_SDK_LOAD_CONFIG


api:
	@bash scripts/deploy/api.sh

web:
	@bash scripts/deploy/web.sh

migrate:
	@bash scripts/migrate.sh

admin:
	@bash scripts/create-admin-user.sh
