#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

WORKSPACE="${1:-${WORKSPACE:-dev}}"
AWS_WORKLOAD_PROFILE="${AWS_WORKLOAD_PROFILE:-${WORKSPACE}-prepvilla}"
TFVARS_FILE="${INFRA_DIR}/terraform/envs/${WORKSPACE}.tfvars"
AWS_REGION="${AWS_REGION:-eu-west-1}"
ECS_CLUSTER_NAME="${ECS_CLUSTER_NAME:-}"
ADMIN_TASK_DEFINITION="${ADMIN_TASK_DEFINITION:-}"
ADMIN_TASK_CONTAINER_NAME="${ADMIN_TASK_CONTAINER_NAME:-migration}"
PUBLIC_SUBNET_IDS="${PUBLIC_SUBNET_IDS:-}"
APP_SECURITY_GROUP_ID="${APP_SECURITY_GROUP_ID:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@prepvilla.info}"
ADMIN_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-${ADMIN_PASSWORD:-}}"

export AWS_PAGER=""

AWS_PROFILE_ARGS=()

set_aws_auth_mode() {
  if [ "${AWS_USE_PROFILE:-1}" = "0" ] ||
    [ -n "${AWS_ACCESS_KEY_ID:-}" ] ||
    [ -n "${AWS_WEB_IDENTITY_TOKEN_FILE:-}" ] ||
    [ -n "${AWS_CONTAINER_CREDENTIALS_RELATIVE_URI:-}" ] ||
    [ -n "${AWS_CONTAINER_CREDENTIALS_FULL_URI:-}" ]; then
    AWS_PROFILE_ARGS=()
    return
  fi

  AWS_PROFILE_ARGS=(--profile "${AWS_WORKLOAD_PROFILE}")
}

aws_with_auth() {
  aws "${AWS_PROFILE_ARGS[@]}" "$@"
}

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

read_tfvars_string() {
  local key="$1"
  local value

  value="$(sed -nE "s/^${key}[[:space:]]*=[[:space:]]*\"([^\"]+)\"[[:space:]]*$/\\1/p" "${TFVARS_FILE}" | head -n 1)"
  [ -n "${value}" ] || fail "Could not read ${key} from ${TFVARS_FILE}"
  printf '%s\n' "${value}"
}

build_overrides_json() {
  ADMIN_EMAIL="${ADMIN_EMAIL}" \
  ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  ADMIN_TASK_CONTAINER_NAME="${ADMIN_TASK_CONTAINER_NAME}" \
  python3 - <<'PY'
import json
import os

command = (
    "cd /app && python manage.py ensure_superuser "
    '--email "$ADMIN_EMAIL" '
    '--password "$ADMIN_PASSWORD" '
    '--display-name "Admin" '
    '--full-name "Admin" '
    '--timezone "UTC"'
)

payload = {
    "containerOverrides": [
        {
            "name": os.environ["ADMIN_TASK_CONTAINER_NAME"],
            "command": ["sh", "-lc", command],
            "environment": [
                {"name": "ADMIN_EMAIL", "value": os.environ["ADMIN_EMAIL"]},
                {"name": "ADMIN_PASSWORD", "value": os.environ["ADMIN_PASSWORD"]},
            ],
        }
    ]
}

print(json.dumps(payload))
PY
}

require_cmd aws
require_cmd python3
require_cmd sed
require_cmd tr
set_aws_auth_mode

[ -n "${ADMIN_PASSWORD}" ] || fail "ADMIN_PASSWORD is required"

if [ -f "${TFVARS_FILE}" ]; then
  PROJECT_NAME="${PROJECT_NAME:-$(read_tfvars_string project_name)}"
  ENVIRONMENT="${ENVIRONMENT:-$(read_tfvars_string environment)}"
  REGION="${AWS_REGION:-$(read_tfvars_string region)}"
else
  PROJECT_NAME="${PROJECT_NAME:-prepvilla}"
  ENVIRONMENT="${ENVIRONMENT:-${WORKSPACE}}"
  REGION="${AWS_REGION:-eu-west-1}"
fi
NAME_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"
CLUSTER_NAME="${ECS_CLUSTER_NAME:-${NAME_PREFIX}-cluster}"
TASK_DEFINITION="${ADMIN_TASK_DEFINITION:-${NAME_PREFIX}-migration}"
API_SERVICE_NAME="${NAME_PREFIX}-api"

resolve_service_network_value() {
  local query="$1"

  aws_with_auth ecs describe-services \
    --region "${REGION}" \
    --cluster "${CLUSTER_NAME}" \
    --services "${API_SERVICE_NAME}" \
    --query "${query}" \
    --output text 2>/dev/null || true
}

if [ -z "${PUBLIC_SUBNET_IDS}" ]; then
  PUBLIC_SUBNET_IDS="$(aws_with_auth ec2 describe-subnets \
    --region "${REGION}" \
    --filters \
      "Name=tag:Project,Values=${PROJECT_NAME}" \
      "Name=tag:Environment,Values=${ENVIRONMENT}" \
      "Name=tag:Tier,Values=public" \
    --query 'Subnets[].SubnetId' \
    --output text)"

  if [ -z "${PUBLIC_SUBNET_IDS}" ] || [ "${PUBLIC_SUBNET_IDS}" = "None" ]; then
    PUBLIC_SUBNET_IDS="$(resolve_service_network_value 'services[0].networkConfiguration.awsvpcConfiguration.subnets')"
  fi
fi

[ -n "${PUBLIC_SUBNET_IDS}" ] && [ "${PUBLIC_SUBNET_IDS}" != "None" ] || fail "Could not resolve public subnets for ${NAME_PREFIX}"

if [ -z "${APP_SECURITY_GROUP_ID}" ]; then
  APP_SECURITY_GROUP_ID="$(aws_with_auth ec2 describe-security-groups \
    --region "${REGION}" \
    --filters "Name=group-name,Values=${NAME_PREFIX}-app" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)"

  if [ -z "${APP_SECURITY_GROUP_ID}" ] || [ "${APP_SECURITY_GROUP_ID}" = "None" ]; then
    APP_SECURITY_GROUP_ID="$(resolve_service_network_value 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]')"
  fi
fi

[ -n "${APP_SECURITY_GROUP_ID}" ] && [ "${APP_SECURITY_GROUP_ID}" != "None" ] || fail "Could not resolve app security group for ${NAME_PREFIX}"

TASK_DEFINITION_ARN="$(aws_with_auth ecs describe-task-definition \
  --region "${REGION}" \
  --task-definition "${TASK_DEFINITION}" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)"

[ -n "${TASK_DEFINITION_ARN}" ] && [ "${TASK_DEFINITION_ARN}" != "None" ] || fail "Could not resolve ECS task definition ${TASK_DEFINITION}"

IFS=$'\t \n,' read -r -a SUBNET_IDS <<< "${PUBLIC_SUBNET_IDS}"
[ "${#SUBNET_IDS[@]}" -gt 0 ] || fail "No public subnet IDs available for the admin task"

subnet_csv="$(IFS=,; echo "${SUBNET_IDS[*]}")"
network_configuration="awsvpcConfiguration={subnets=[${subnet_csv}],securityGroups=[${APP_SECURITY_GROUP_ID}],assignPublicIp=ENABLED}"
overrides_json="$(build_overrides_json)"

echo "Creating or updating ${ADMIN_EMAIL} with task definition ${TASK_DEFINITION_ARN}..."
TASK_ARN="$(aws_with_auth ecs run-task \
  --region "${REGION}" \
  --cluster "${CLUSTER_NAME}" \
  --launch-type FARGATE \
  --task-definition "${TASK_DEFINITION_ARN}" \
  --network-configuration "${network_configuration}" \
  --overrides "${overrides_json}" \
  --started-by "admin-user-noninteractive" \
  --query 'tasks[0].taskArn' \
  --output text)"

[ -n "${TASK_ARN}" ] && [ "${TASK_ARN}" != "None" ] || fail "Failed to start the admin creation task in cluster ${CLUSTER_NAME}"

echo "Task ARN: ${TASK_ARN}"

aws_with_auth ecs wait tasks-stopped \
  --region "${REGION}" \
  --cluster "${CLUSTER_NAME}" \
  --tasks "${TASK_ARN}"

TASK_EXIT_CODE="$(aws_with_auth ecs describe-tasks \
  --region "${REGION}" \
  --cluster "${CLUSTER_NAME}" \
  --tasks "${TASK_ARN}" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)"

TASK_STOPPED_REASON="$(aws_with_auth ecs describe-tasks \
  --region "${REGION}" \
  --cluster "${CLUSTER_NAME}" \
  --tasks "${TASK_ARN}" \
  --query 'tasks[0].stoppedReason' \
  --output text)"

TASK_CONTAINER_REASON="$(aws_with_auth ecs describe-tasks \
  --region "${REGION}" \
  --cluster "${CLUSTER_NAME}" \
  --tasks "${TASK_ARN}" \
  --query 'tasks[0].containers[0].reason' \
  --output text)"

if [ "${TASK_EXIT_CODE}" != "0" ]; then
  fail "Admin user task failed with exit code ${TASK_EXIT_CODE}. Stopped reason: ${TASK_STOPPED_REASON}. Container reason: ${TASK_CONTAINER_REASON}"
fi

echo "Admin user ready: ${ADMIN_EMAIL}"
