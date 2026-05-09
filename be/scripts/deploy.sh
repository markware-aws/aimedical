#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

: "${AWS_PROFILE:=aimedical-user}"
: "${LAMBDA_NAME:=aimedical-fetcher}"
: "${AWS_REGION:=eu-central-1}"

bash scripts/package.sh

echo "==> upload to lambda: ${LAMBDA_NAME}"
aws lambda update-function-code \
  --function-name "${LAMBDA_NAME}" \
  --zip-file fileb://function.zip \
  --region "${AWS_REGION}" \
  --profile "${AWS_PROFILE}" \
  --no-cli-pager

echo "==> done"
