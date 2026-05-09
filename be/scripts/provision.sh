#!/usr/bin/env bash
# One-shot provisioning of all AWS resources for the aimedical pipeline.
# Idempotent where possible — existing-resource errors are tolerated.
#
# Required env (or pass on command line):
#   AWS_PROFILE                (default: aimedical-user)
#   AWS_REGION                 (default: eu-central-1)
#   ACCOUNT_ID                 (queried via STS if not set)
#   S3_BUCKET                  (default: aimedical-frontend)
#   DDB_TABLE                  (default: aimedical_articles)
#   LAMBDA_NAME                (default: aimedical-fetcher)
#   ROLE_NAME                  (default: aimedical-lambda-role)
#   CRON_SCHEDULE              (default: cron(0 */6 * * ? *))
#
# Run AFTER you have built the Lambda zip:
#   bash scripts/package.sh

set -euo pipefail

: "${AWS_PROFILE:=aimedical-user}"
: "${AWS_REGION:=eu-central-1}"
: "${S3_BUCKET:=aimedical-frontend}"
: "${DDB_TABLE:=aimedical_articles}"
: "${LAMBDA_NAME:=aimedical-fetcher}"
: "${ROLE_NAME:=aimedical-lambda-role}"
: "${CRON_SCHEDULE:=cron(0 */6 * * ? *)}"

if [[ -z "${ACCOUNT_ID:-}" ]]; then
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile "${AWS_PROFILE}")
fi

aws_call() {
  aws "$@" --region "${AWS_REGION}" --profile "${AWS_PROFILE}" --no-cli-pager
}

ok_or_exists() {
  "$@" || echo "  (already exists, continuing)"
}

echo "==> S3 bucket: ${S3_BUCKET}"
ok_or_exists aws_call s3api create-bucket \
  --bucket "${S3_BUCKET}" \
  --create-bucket-configuration LocationConstraint="${AWS_REGION}"

aws_call s3 website "s3://${S3_BUCKET}/" --index-document index.html --error-document 404.html

aws_call s3api put-public-access-block \
  --bucket "${S3_BUCKET}" \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "==> DynamoDB table: ${DDB_TABLE}"
ok_or_exists aws_call dynamodb create-table \
  --table-name "${DDB_TABLE}" \
  --attribute-definitions AttributeName=pk,AttributeType=S \
  --key-schema AttributeName=pk,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

echo "==> IAM role: ${ROLE_NAME}"
TRUST=$(cat <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF
)
ok_or_exists aws_call iam create-role \
  --role-name "${ROLE_NAME}" \
  --assume-role-policy-document "${TRUST}"

POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":"*"},
    {"Effect":"Allow","Action":["dynamodb:GetItem","dynamodb:PutItem"],"Resource":"arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${DDB_TABLE}"}
  ]
}
EOF
)
aws_call iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name aimedical-inline \
  --policy-document "${POLICY}"

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo "==> waiting 10s for IAM propagation"
sleep 10

echo "==> Lambda: ${LAMBDA_NAME}"
if [[ ! -f function.zip ]]; then
  echo "function.zip not found — run 'bash scripts/package.sh' first" >&2
  exit 1
fi

if aws_call lambda get-function --function-name "${LAMBDA_NAME}" >/dev/null 2>&1; then
  aws_call lambda update-function-code \
    --function-name "${LAMBDA_NAME}" \
    --zip-file fileb://function.zip
else
  aws_call lambda create-function \
    --function-name "${LAMBDA_NAME}" \
    --runtime python3.12 \
    --role "${ROLE_ARN}" \
    --handler medical_news.handlers.orchestrator.handler \
    --zip-file fileb://function.zip \
    --timeout 300 \
    --memory-size 1024
fi

echo "==> EventBridge cron: ${CRON_SCHEDULE}"
aws_call events put-rule \
  --name aimedical-cron \
  --schedule-expression "${CRON_SCHEDULE}"

aws_call events put-targets \
  --rule aimedical-cron \
  --targets "Id=1,Arn=arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${LAMBDA_NAME}"

ok_or_exists aws_call lambda add-permission \
  --function-name "${LAMBDA_NAME}" \
  --statement-id eventbridge-invoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${AWS_REGION}:${ACCOUNT_ID}:rule/aimedical-cron"

echo "==> all resources provisioned"
echo "    next: aws lambda update-function-configuration --function-name ${LAMBDA_NAME} --environment Variables={OPENAI_API_KEY=...,GITHUB_TOKEN=...,DYNAMODB_TABLE=${DDB_TABLE},...}"
