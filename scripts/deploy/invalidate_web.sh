#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

WORKSPACE="${WORKSPACE:-dev}"
DOMAIN_NAME="${DOMAIN_NAME:-dev.prepvilla.info}"
AWS_WORKLOAD_PROFILE="${AWS_WORKLOAD_PROFILE:-${WORKSPACE}-prepvilla}"

export AWS_PAGER=""
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_SECURITY_TOKEN AWS_SESSION_EXPIRATION AWS_ACCESS_KEY AWS_SECRET_KEY

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

require_cmd aws
require_cmd grep
require_cmd sed

DISTRIBUTION_ID="$(aws cloudfront list-distributions \
  --profile "${AWS_WORKLOAD_PROFILE}" \
  --query "DistributionList.Items[?Aliases.Items!=null && contains(Aliases.Items, '${DOMAIN_NAME}')].Id | [0]" \
  --output text)"

[ -n "${DISTRIBUTION_ID}" ] && [ "${DISTRIBUTION_ID}" != "None" ] \
  || fail "Could not find CloudFront distribution for alias ${DOMAIN_NAME}"

echo "Creating CloudFront invalidation for ${DISTRIBUTION_ID}..."
aws cloudfront create-invalidation \
  --profile "${AWS_WORKLOAD_PROFILE}" \
  --distribution-id "${DISTRIBUTION_ID}" \
  --paths "/*" >/dev/null

echo "CloudFront invalidation complete."
echo "Distribution: ${DISTRIBUTION_ID}"
echo "URL: https://${DOMAIN_NAME}"
