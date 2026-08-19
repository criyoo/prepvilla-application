#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

WORKSPACE="${WORKSPACE:-dev}"
AWS_WORKLOAD_PROFILE="${AWS_WORKLOAD_PROFILE:-${WORKSPACE}-prepvilla}"
TFVARS_FILE="${INFRA_DIR}/terraform/envs/${WORKSPACE}.tfvars"
PUBLIC_SUBNET_IDS="${PUBLIC_SUBNET_IDS:-}"
APP_SECURITY_GROUP_ID="${APP_SECURITY_GROUP_ID:-}"
ECS_CLUSTER_NAME="${ECS_CLUSTER_NAME:-}"
MIGRATION_TASK_DEFINITION="${MIGRATION_TASK_DEFINITION:-}"
MIGRATION_LOG_GROUP="${MIGRATION_LOG_GROUP:-}"

export AWS_PAGER=""
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_SECURITY_TOKEN AWS_SESSION_EXPIRATION AWS_ACCESS_KEY AWS_SECRET_KEY

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

  grep -qE "^${key}[[:space:]]*=[[:space:]]*\"[^\"]*\"[[:space:]]*$" "${TFVARS_FILE}" \
    || fail "Could not read ${key} from ${TFVARS_FILE}"
  value="$(sed -nE "s/^${key}[[:space:]]*=[[:space:]]*\"([^\"]*)\"[[:space:]]*$/\\1/p" "${TFVARS_FILE}" | head -n 1)"
  printf '%s\n' "${value}"
}

json_escape() {
  local value="$1"

  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"

  printf '%s' "${value}"
}

build_task_overrides() {
  local command="$1"

  printf '{"containerOverrides":[{"name":"migration","command":["sh","-lc","%s"]}]}' "$(json_escape "${command}")"
}

require_cmd aws
require_cmd grep
require_cmd sed
require_cmd tr

[ -f "${TFVARS_FILE}" ] || fail "Missing Terraform variables file: ${TFVARS_FILE}"

PROJECT_NAME="$(read_tfvars_string project_name)"
ENVIRONMENT="$(read_tfvars_string environment)"
REGION="${AWS_REGION:-$(read_tfvars_string region)}"
NAME_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"
CLUSTER_NAME="${ECS_CLUSTER_NAME:-${NAME_PREFIX}-cluster}"
TASK_DEFINITION="${MIGRATION_TASK_DEFINITION:-${NAME_PREFIX}-migration}"
MIGRATION_LOG_GROUP="${MIGRATION_LOG_GROUP:-/ecs/${NAME_PREFIX}/migration}"
API_SERVICE_NAME="${NAME_PREFIX}-api"

LAST_TASK_ARN=""
LAST_TASK_EXIT_CODE=""
LAST_TASK_STOPPED_REASON=""
LAST_TASK_CONTAINER_REASON=""

run_ecs_task() {
  local description="$1"
  local overrides="${2:-}"
  local -a run_task_args

  run_task_args=(
    aws ecs run-task
    --profile "${AWS_WORKLOAD_PROFILE}"
    --region "${REGION}"
    --cluster "${CLUSTER_NAME}"
    --launch-type FARGATE
    --task-definition "${TASK_DEFINITION_ARN}"
    --network-configuration "${network_configuration}"
    --query 'tasks[0].taskArn'
    --output text
  )

  if [ -n "${overrides}" ]; then
    run_task_args+=(--overrides "${overrides}")
  fi

  echo "${description} with task definition ${TASK_DEFINITION_ARN}..."
  LAST_TASK_ARN="$("${run_task_args[@]}")"

  [ -n "${LAST_TASK_ARN}" ] && [ "${LAST_TASK_ARN}" != "None" ] || fail "Failed to start the task in cluster ${CLUSTER_NAME}"

  echo "Task ARN: ${LAST_TASK_ARN}"

  aws ecs wait tasks-stopped \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --cluster "${CLUSTER_NAME}" \
    --tasks "${LAST_TASK_ARN}"

  LAST_TASK_EXIT_CODE="$(aws ecs describe-tasks \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --cluster "${CLUSTER_NAME}" \
    --tasks "${LAST_TASK_ARN}" \
    --query 'tasks[0].containers[0].exitCode' \
    --output text)"

  LAST_TASK_STOPPED_REASON="$(aws ecs describe-tasks \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --cluster "${CLUSTER_NAME}" \
    --tasks "${LAST_TASK_ARN}" \
    --query 'tasks[0].stoppedReason' \
    --output text)"

  LAST_TASK_CONTAINER_REASON="$(aws ecs describe-tasks \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --cluster "${CLUSTER_NAME}" \
    --tasks "${LAST_TASK_ARN}" \
    --query 'tasks[0].containers[0].reason' \
    --output text)"
}

has_pending_migrations() {
  local overrides
  local task_id

  overrides="$(build_task_overrides "set -eu; python manage.py showmigrations --plan --no-color > /tmp/migration-plan.txt; cat /tmp/migration-plan.txt; if grep -q '^\\[ \\]' /tmp/migration-plan.txt; then exit 10; fi")"

  run_ecs_task "Checking for pending Django migrations" "${overrides}"
  task_id="${LAST_TASK_ARN##*/}"

  case "${LAST_TASK_EXIT_CODE}" in
    0)
      echo "No pending Django migrations detected."
      return 1
      ;;
    10)
      echo "Pending Django migrations detected."
      return 0
      ;;
    *)
      print_task_logs "${task_id}"
      fail "Migration check task failed with exit code ${LAST_TASK_EXIT_CODE}. Stopped reason: ${LAST_TASK_STOPPED_REASON}. Container reason: ${LAST_TASK_CONTAINER_REASON}"
      ;;
  esac
}

print_task_logs() {
  local task_id="$1"
  local log_stream_name
  local task_logs

  log_stream_name="$(aws logs describe-log-streams \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --log-group-name "${MIGRATION_LOG_GROUP}" \
    --log-stream-name-prefix "ecs/migration/${task_id}" \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null || true)"

  if [ -z "${log_stream_name}" ] || [ "${log_stream_name}" = "None" ]; then
    echo "Migration task CloudWatch log stream was not found in ${MIGRATION_LOG_GROUP} for task ${task_id}." >&2
    return
  fi

  echo "Migration task CloudWatch logs from ${MIGRATION_LOG_GROUP}:${log_stream_name}:" >&2
  task_logs="$(aws logs get-log-events \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --log-group-name "${MIGRATION_LOG_GROUP}" \
    --log-stream-name "${log_stream_name}" \
    --limit 200 \
    --query 'events[*].message' \
    --output text 2>/dev/null || true)"

  if [ -z "${task_logs}" ] || [ "${task_logs}" = "None" ]; then
    echo "(no log events found)" >&2
    return
  fi

  printf '%s\n' "${task_logs}" | tr '\t' '\n' >&2
}

resolve_service_network_value() {
  local query="$1"

  aws ecs describe-services \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --cluster "${CLUSTER_NAME}" \
    --services "${API_SERVICE_NAME}" \
    --query "${query}" \
    --output text 2>/dev/null || true
}

if [ -z "${PUBLIC_SUBNET_IDS}" ]; then
  PUBLIC_SUBNET_IDS="$(aws ec2 describe-subnets \
    --profile "${AWS_WORKLOAD_PROFILE}" \
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
  APP_SECURITY_GROUP_ID="$(aws ec2 describe-security-groups \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --filters "Name=group-name,Values=${NAME_PREFIX}-app" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)"

  if [ -z "${APP_SECURITY_GROUP_ID}" ] || [ "${APP_SECURITY_GROUP_ID}" = "None" ]; then
    APP_SECURITY_GROUP_ID="$(resolve_service_network_value 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]')"
  fi
fi

[ -n "${APP_SECURITY_GROUP_ID}" ] && [ "${APP_SECURITY_GROUP_ID}" != "None" ] || fail "Could not resolve app security group for ${NAME_PREFIX}"

TASK_DEFINITION_ARN="$(aws ecs describe-task-definition \
  --profile "${AWS_WORKLOAD_PROFILE}" \
  --region "${REGION}" \
  --task-definition "${TASK_DEFINITION}" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)"

[ -n "${TASK_DEFINITION_ARN}" ] && [ "${TASK_DEFINITION_ARN}" != "None" ] || fail "Could not resolve ECS migration task definition ${TASK_DEFINITION}"

IFS=$'\t \n,' read -r -a SUBNET_IDS <<< "${PUBLIC_SUBNET_IDS}"
[ "${#SUBNET_IDS[@]}" -gt 0 ] || fail "No public subnet IDs available for the migration task"

subnet_csv="$(IFS=,; echo "${SUBNET_IDS[*]}")"
network_configuration="awsvpcConfiguration={subnets=[${subnet_csv}],securityGroups=[${APP_SECURITY_GROUP_ID}],assignPublicIp=ENABLED}"

if ! has_pending_migrations; then
  echo "Django migrations skipped."
  exit 0
fi

run_ecs_task "Running Django migrations"

if [ "${LAST_TASK_EXIT_CODE}" != "0" ]; then
  print_task_logs "${LAST_TASK_ARN##*/}"
  fail "Migration task failed with exit code ${LAST_TASK_EXIT_CODE}. Stopped reason: ${LAST_TASK_STOPPED_REASON}. Container reason: ${LAST_TASK_CONTAINER_REASON}"
fi

echo "Django migrations completed successfully."
