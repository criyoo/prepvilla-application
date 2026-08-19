#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_DIR="$(cd "${INFRA_DIR}/.." && pwd)"
FRONTEND_DIR="${REPO_DIR}/apps/web"
UPLOADS_DIR="${REPO_DIR}/apps/api/uploads"
TYPES_PACKAGE_DIR="${REPO_DIR}/packages/types"

WORKSPACE="${WORKSPACE:-dev}"
AWS_WORKLOAD_PROFILE="${AWS_WORKLOAD_PROFILE:-${WORKSPACE}-prepvilla}"
TFVARS_FILE="${INFRA_DIR}/terraform/envs/${WORKSPACE}.tfvars"
INSTALL_DEPS="${INSTALL_DEPS:-auto}"

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

read_tfvars_object_string() {
  local object_key="$1"
  local key="$2"
  local value

  value="$(
    sed -nE "/^${object_key}[[:space:]]*=[[:space:]]*\\{/,/^[[:space:]]*\\}/{s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*\"([^\"]*)\".*$/\\1/p;}" "${TFVARS_FILE}" \
      | head -n 1
  )"
  printf '%s\n' "${value}"
}

require_cmd aws
require_cmd npm
require_cmd node
require_cmd grep
require_cmd sed
require_cmd mktemp
require_cmd cp

[ -d "${FRONTEND_DIR}" ] || fail "Missing frontend application directory: ${FRONTEND_DIR}"
[ -d "${UPLOADS_DIR}" ] || fail "Missing uploads directory: ${UPLOADS_DIR}"
[ -d "${TYPES_PACKAGE_DIR}" ] || fail "Missing types package directory: ${TYPES_PACKAGE_DIR}"
[ -f "${TFVARS_FILE}" ] || fail "Missing Terraform variables file: ${TFVARS_FILE}"

PROJECT_NAME="$(read_tfvars_string project_name)"
ENVIRONMENT="$(read_tfvars_string environment)"
REGION="$(read_tfvars_string region)"
FRONTEND_DOMAIN="$(read_tfvars_string domain_name)"
API_DOMAIN="$(read_tfvars_string api_domain_name)"
GOOGLE_OAUTH_CLIENT_ID="$(read_tfvars_object_string app_string_parameters NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID)"
API_BASE_DOMAIN="${API_DOMAIN:-${FRONTEND_DOMAIN}}"

BUCKET_NAME="${FRONTEND_BUCKET_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-frontend}"

aws s3api head-bucket --profile "${AWS_WORKLOAD_PROFILE}" --region "${REGION}" --bucket "${BUCKET_NAME}" >/dev/null 2>&1 \
  || fail "Frontend bucket not found or inaccessible: ${BUCKET_NAME}"

if [ "${INSTALL_DEPS}" = "1" ] || { [ "${INSTALL_DEPS}" = "auto" ] && [ ! -d "${REPO_DIR}/node_modules" ]; }; then
  echo "Installing frontend dependencies..."
  (
    cd "${REPO_DIR}"
    if [ -f package-lock.json ]; then
      npm ci
    else
      npm install
    fi
  )
fi

[ -d "${REPO_DIR}/node_modules" ] || fail "Missing ${REPO_DIR}/node_modules. Run with INSTALL_DEPS=1 or install dependencies first."

BUILD_DIR="$(mktemp -d /tmp/prepvilla-frontend-build.XXXXXX)"
cleanup() {
  rm -rf "${BUILD_DIR}"
}
trap cleanup EXIT

mkdir -p "${BUILD_DIR}/apps" "${BUILD_DIR}/packages"
cp -R "${FRONTEND_DIR}" "${BUILD_DIR}/apps/web"
mkdir -p "${BUILD_DIR}/apps/api"
cp -R "${UPLOADS_DIR}" "${BUILD_DIR}/apps/api/uploads"
cp -R "${TYPES_PACKAGE_DIR}" "${BUILD_DIR}/packages/types"
cp "${REPO_DIR}/package.json" "${BUILD_DIR}/package.json"
if [ -f "${REPO_DIR}/package-lock.json" ]; then
  cp "${REPO_DIR}/package-lock.json" "${BUILD_DIR}/package-lock.json"
fi
ln -s "${REPO_DIR}/node_modules" "${BUILD_DIR}/node_modules"
rm -rf \
  "${BUILD_DIR}/apps/web/.next" \
  "${BUILD_DIR}/apps/web/.next-verify" \
  "${BUILD_DIR}/apps/web/.next-verify-check" \
  "${BUILD_DIR}/apps/web/.next-static-check" \
  "${BUILD_DIR}/apps/web/.next-static-export" \
  "${BUILD_DIR}/apps/web/out"

echo "Building static frontend export..."
(
  cd "${BUILD_DIR}/apps/web"
  NEXT_OUTPUT_MODE=export \
  NEXT_PUBLIC_API_BASE_URL="https://${API_BASE_DOMAIN}" \
  NEXT_PUBLIC_WS_BASE_URL="wss://${API_BASE_DOMAIN}" \
  NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID}" \
  "${BUILD_DIR}/node_modules/.bin/next" build
)

[ -d "${BUILD_DIR}/apps/web/out" ] || fail "Next export output not found at ${BUILD_DIR}/apps/web/out"

echo "Uploading frontend to s3://${BUCKET_NAME}/ ..."
aws s3 sync \
  "${BUILD_DIR}/apps/web/out/" \
  "s3://${BUCKET_NAME}/" \
  --profile "${AWS_WORKLOAD_PROFILE}" \
  --region "${REGION}" \
  --delete \
  --exclude "*.html" \
  --exclude "_next/static/*"

echo "Applying cache headers for HTML documents..."
aws s3 sync \
  "${BUILD_DIR}/apps/web/out/" \
  "s3://${BUCKET_NAME}/" \
  --profile "${AWS_WORKLOAD_PROFILE}" \
  --region "${REGION}" \
  --delete \
  --exclude "*" \
  --include "*.html" \
  --cache-control "public,max-age=0,s-maxage=60,must-revalidate"

if [ -d "${BUILD_DIR}/apps/web/out/_next/static" ]; then
  echo "Applying immutable cache headers for Next static assets..."
  aws s3 sync \
    "${BUILD_DIR}/apps/web/out/_next/static/" \
    "s3://${BUCKET_NAME}/_next/static/" \
    --profile "${AWS_WORKLOAD_PROFILE}" \
    --region "${REGION}" \
    --delete \
    --cache-control "public,max-age=31536000,immutable"
fi

echo "Frontend deployment complete."
echo "Bucket: s3://${BUCKET_NAME}"
echo "URL: https://${FRONTEND_DOMAIN}"
