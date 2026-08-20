#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_DIR="${BACKEND_DIR:-${REPO_DIR}/api}"

WORKSPACE="${WORKSPACE:-dev}"
AWS_WORKLOAD_PROFILE="${AWS_WORKLOAD_PROFILE:-${WORKSPACE}-prepvilla}"
PROJECT_NAME="prepvilla"
ENVIRONMENT="$1"
REGION="${REGION:-eu-west-1}"
CONTAINER_ARCHITECTURE="ARM64"
FRONTEND_DOMAIN="${FRONTEND_DOMAIN:-prep-villa.com}"
API_DOMAIN="${API_DOMAIN:-api.prep-villa.com}"


STABLE_TAG="${STABLE_TAG:-${WORKSPACE}}"
IMAGE_TAG="${IMAGE_TAG:-}"
API_DESIRED_COUNT="${API_DESIRED_COUNT:-}"
WAIT_FOR_STABLE="${WAIT_FOR_STABLE:-1}"
DEPLOY_ECS="${DEPLOY_ECS:-1}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
BUILDER_NAME="${BUILDER_NAME:-prepvilla-multiarch}"
INSTALL_BINFMT="${INSTALL_BINFMT:-1}"

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

ensure_buildx() {
  docker buildx version >/dev/null 2>&1 || fail "docker buildx is required for multi-architecture image builds"

  if ! docker buildx inspect "${BUILDER_NAME}" >/dev/null 2>&1; then
    docker buildx create --name "${BUILDER_NAME}" --driver docker-container --use >/dev/null
  else
    docker buildx use "${BUILDER_NAME}" >/dev/null
  fi

  docker buildx inspect --bootstrap "${BUILDER_NAME}" >/dev/null
}

recreate_buildx() {
  if docker buildx inspect "${BUILDER_NAME}" >/dev/null 2>&1; then
    docker buildx rm --force "${BUILDER_NAME}" >/dev/null 2>&1 || true
  fi

  docker buildx create --name "${BUILDER_NAME}" --driver docker-container --use >/dev/null
  docker buildx inspect --bootstrap "${BUILDER_NAME}" >/dev/null
}

builder_supports_platform() {
  docker buildx inspect "${BUILDER_NAME}" \
    | awk -F': ' '/Platforms:/{print $2}' \
    | tr ',' '\n' \
    | sed 's/^ *//; s/ *$//' \
    | grep -Fxq "${DOCKER_PLATFORM}"
}

ensure_platform_support() {
  if builder_supports_platform; then
    return
  fi

  if [ "${DOCKER_PLATFORM}" = "linux/arm64" ] && [ "${INSTALL_BINFMT}" = "1" ]; then
    echo "Enabling arm64 emulation for Docker builds..."
    docker run --privileged --rm tonistiigi/binfmt --install arm64 >/dev/null
    docker buildx inspect --bootstrap "${BUILDER_NAME}" >/dev/null

    if ! builder_supports_platform; then
      echo "Recreating Docker builder ${BUILDER_NAME} to refresh supported platforms..."
      recreate_buildx
    fi
  fi

  builder_supports_platform || fail "Docker builder ${BUILDER_NAME} does not support ${DOCKER_PLATFORM}. Re-run with INSTALL_BINFMT=1 or install binfmt/QEMU support for Docker."
}

require_cmd aws
require_cmd docker
require_cmd grep
require_cmd sed
require_cmd tr
set_aws_auth_mode

[ -d "${BACKEND_DIR}" ] || fail "Missing backend application directory: ${BACKEND_DIR}"
[ -f "${BACKEND_DIR}/Dockerfile" ] || fail "Missing backend Dockerfile: ${BACKEND_DIR}/Dockerfile"

API_DESIRED_COUNT=1

NAME_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"
REPOSITORY_NAME="${NAME_PREFIX}-api"
CLUSTER_NAME="${NAME_PREFIX}-cluster"

case "${CONTAINER_ARCHITECTURE}" in
  ARM64)
    DOCKER_PLATFORM="linux/arm64"
    ;;
  X86_64)
    DOCKER_PLATFORM="linux/amd64"
    ;;
  *)
    fail "Unsupported container_architecture: ${CONTAINER_ARCHITECTURE}"
    ;;
esac

REPOSITORY_URI="$(aws_with_auth ecr describe-repositories \
  --region "${REGION}" \
  --repository-names "${REPOSITORY_NAME}" \
  --query 'repositories[0].repositoryUri' \
  --output text)"

[ -n "${REPOSITORY_URI}" ] && [ "${REPOSITORY_URI}" != "None" ] || fail "Could not resolve ECR repository ${REPOSITORY_NAME}"

REGISTRY_HOST="${REPOSITORY_URI%%/*}"

echo "Authenticating Docker to ${REGISTRY_HOST}..."
aws_with_auth ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${REGISTRY_HOST}" >/dev/null

ensure_buildx
ensure_platform_support

echo "Building and pushing ${REPOSITORY_URI}:${STABLE_TAG} (${DOCKER_PLATFORM})..."
build_args=(
  docker buildx build
  --builder "${BUILDER_NAME}"
  --platform "${DOCKER_PLATFORM}"
  --file "${BACKEND_DIR}/Dockerfile"
  --tag "${REPOSITORY_URI}:${STABLE_TAG}"
)

if [ -n "${IMAGE_TAG}" ] && [ "${IMAGE_TAG}" != "${STABLE_TAG}" ]; then
  build_args+=(--tag "${REPOSITORY_URI}:${IMAGE_TAG}")
fi

build_args+=(
  --load
  "${BACKEND_DIR}"
)

"${build_args[@]}"

docker push "${REPOSITORY_URI}:${STABLE_TAG}"

if [ -n "${IMAGE_TAG}" ] && [ "${IMAGE_TAG}" != "${STABLE_TAG}" ]; then
  docker push "${REPOSITORY_URI}:${IMAGE_TAG}"
fi

if [ "${DEPLOY_ECS}" != "1" ]; then
  echo "Backend image bootstrap complete."
  echo "Image tags pushed: ${STABLE_TAG}${IMAGE_TAG:+, ${IMAGE_TAG}}"
  exit 0
fi

if [ "${RUN_MIGRATIONS}" = "1" ]; then
  WORKSPACE="${WORKSPACE}" \
  AWS_WORKLOAD_PROFILE="${AWS_WORKLOAD_PROFILE}" \
  AWS_REGION="${REGION}" \
  ECS_CLUSTER_NAME="${CLUSTER_NAME}" \
  MIGRATION_TASK_DEFINITION="${NAME_PREFIX}-migration" \
  MIGRATION_LOG_GROUP="/ecs/${NAME_PREFIX}/migration" \
  bash "scripts/migrate.sh"
fi

mapfile -t SERVICE_ARNS < <(aws_with_auth ecs list-services \
  --region "${REGION}" \
  --cluster "${CLUSTER_NAME}" \
  --query 'serviceArns' \
  --output text | tr '\t' '\n')

[ "${#SERVICE_ARNS[@]}" -gt 0 ] || fail "No ECS services found in cluster ${CLUSTER_NAME}"

SERVICES=()
for service_arn in "${SERVICE_ARNS[@]}"; do
  [ -n "${service_arn}" ] || continue
  [ "${service_arn}" = "None" ] && continue
  SERVICES+=("${service_arn##*/}")
done

[ "${#SERVICES[@]}" -gt 0 ] || fail "No active ECS services found in cluster ${CLUSTER_NAME}"

for service_name in "${SERVICES[@]}"; do
  echo "Triggering deployment for ${service_name}..."

  if [ "${service_name}" = "${NAME_PREFIX}-api" ]; then
    desired_count="$(aws_with_auth ecs describe-services \
      --region "${REGION}" \
      --cluster "${CLUSTER_NAME}" \
      --services "${service_name}" \
      --query 'services[0].desiredCount' \
      --output text)"

    if [ "${desired_count}" = "0" ] && [ "${API_DESIRED_COUNT}" -gt 0 ]; then
      echo "Scaling ${service_name} to ${API_DESIRED_COUNT} so the API can serve traffic."
      aws_with_auth ecs update-service \
        --region "${REGION}" \
        --cluster "${CLUSTER_NAME}" \
        --service "${service_name}" \
        --desired-count "${API_DESIRED_COUNT}" \
        --force-new-deployment >/dev/null
      continue
    fi
  fi

  aws_with_auth ecs update-service \
    --region "${REGION}" \
    --cluster "${CLUSTER_NAME}" \
    --service "${service_name}" \
    --force-new-deployment >/dev/null
done

if [ "${WAIT_FOR_STABLE}" = "1" ]; then
  echo "Waiting for ECS services to stabilize..."
  aws_with_auth ecs wait services-stable \
    --region "${REGION}" \
    --cluster "${CLUSTER_NAME}" \
    --services "${SERVICES[@]}"
fi

echo "Backend deployment complete."
if [ -n "${API_DOMAIN}" ]; then
  echo "API URL: https://${API_DOMAIN}"
else
  echo "API URL: https://${FRONTEND_DOMAIN}/api/"
fi
echo "Configured frontend URL: https://${FRONTEND_DOMAIN}"
echo "Image tags pushed: ${STABLE_TAG}${IMAGE_TAG:+, ${IMAGE_TAG}}"
