#!/usr/bin/env bash
# InsightOps EC2 deployment script.
#
# Runs on the GitLab runner (deploy stage). It:
#   1. copies the production compose file + prod env to EC2
#   2. authenticates to the GitLab Container Registry
#   3. pulls the exact commit-tagged backend image
#   4. recreates the api + worker containers (redis data preserved)
#   5. waits for the API health check
#
# Required environment (set as GitLab CI/CD variables):
#   EC2_HOST, SSH_PRIVATE_KEY, CI_REGISTRY, CI_REGISTRY_USER,
#   CI_REGISTRY_PASSWORD (or CI_JOB_TOKEN), CI_COMMIT_SHA,
#   BACKEND_IMAGE, AWS_REGION
#
# This script NEVER prints secrets.
set -euo pipefail

: "${EC2_HOST:?EC2_HOST is required}"
: "${CI_COMMIT_SHA:?CI_COMMIT_SHA is required}"
: "${BACKEND_IMAGE:?BACKEND_IMAGE is required (e.g. registry.gitlab.com/ns/insight-ops/backend:<sha>)}"
: "${CI_REGISTRY:?CI_REGISTRY is required}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_DIR="/opt/insight-ops"

# --- 1. Configure SSH (host key verified via ssh-keyscan TOFU) -------------
if [[ -z "${SSH_PRIVATE_KEY:-}" ]]; then
  echo "SSH_PRIVATE_KEY is not set; skipping deployment." >&2
  exit 1
fi
export SSH_AUTH_SOCK_DIR="$(mktemp -d)"
trap 'rm -rf "$SSH_AUTH_SOCK_DIR"' EXIT
eval "$(ssh-agent -s -a "$SSH_AUTH_SOCK_DIR/agent.sock" >/dev/null)"
printf '%s\n' "$SSH_PRIVATE_KEY" | ssh-add - >/dev/null

SSH_USER="${SSH_USER:-ec2-user}"

# Trust-on-first-use host key pinning: record the host key before connecting
# so StrictHostKeyChecking actually verifies subsequent connections.
KNOWN_HOSTS="$SSH_AUTH_SOCK_DIR/known_hosts"
ssh-keyscan -T 10 "$EC2_HOST" >"$KNOWN_HOSTS" 2>/dev/null || {
  echo "ssh-keyscan failed for $EC2_HOST" >&2
  exit 1
}
SSH_OPTS=(-o StrictHostKeyChecking=yes -o UserKnownHostsFile="$KNOWN_HOSTS" -o LogLevel=ERROR)

# --- 2. Copy compose + environment to EC2 --------------------------------
echo "==> Copying deployment files to ${EC2_HOST}"
scp "${SSH_OPTS[@]}" \
  "$SCRIPT_DIR/docker-compose.prod.yml" \
  "${SSH_USER}@${EC2_HOST}:${REMOTE_DIR}/docker-compose.prod.yml"

if [[ -f "${PROD_ENV_FILE:-/dev/null}" ]]; then
  scp "${SSH_OPTS[@]}" "$PROD_ENV_FILE" "${SSH_USER}@${EC2_HOST}:${REMOTE_DIR}/.env.prod"
else
  echo "PROD_ENV_FILE not provided; keeping existing .env.prod on EC2."
fi

# --- 3. Login, pull, recreate containers ---------------------------------
# CI_JOB_TOKEN works with GitLab's built-in registry auth; prefer it when set.
REGISTRY_PASSWORD="${CI_REGISTRY_PASSWORD:-${CI_JOB_TOKEN:-}}"
if [[ -z "$REGISTRY_PASSWORD" ]]; then
  echo "CI_REGISTRY_PASSWORD / CI_JOB_TOKEN is required to pull images." >&2
  exit 1
fi

echo "==> Deploying ${BACKEND_IMAGE}"
# Password is passed over stdin, never embedded in a command line or logged.
printf '%s' "$REGISTRY_PASSWORD" | ssh "${SSH_OPTS[@]}" "${SSH_USER}@${EC2_HOST}" \
  "docker login ${CI_REGISTRY} -u '${CI_REGISTRY_USER}' --password-stdin"

ssh "${SSH_OPTS[@]}" "${SSH_USER}@${EC2_HOST}" \
  "set -euo pipefail; \
   cd ${REMOTE_DIR}; \
   BACKEND_IMAGE='${BACKEND_IMAGE}' AWS_REGION='${AWS_REGION:-eu-west-1}' \
     docker compose -f docker-compose.prod.yml -p insight-ops pull api worker; \
   BACKEND_IMAGE='${BACKEND_IMAGE}' AWS_REGION='${AWS_REGION:-eu-west-1}' \
     docker compose -f docker-compose.prod.yml -p insight-ops up -d --no-deps api worker"

# --- 4. Health check (bounded retries) ------------------------------------
echo "==> Waiting for API health check"
API_URL="${DEPLOYMENT_URL:-http://${EC2_HOST}:8000}"
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 5 "${API_URL}/health" >/dev/null 2>&1; then
    echo "API is healthy at ${API_URL}"
    exit 0
  fi
  echo "  health check attempt ${attempt}/30 ..."
  sleep 5
done

echo "API failed to become healthy at ${API_URL}" >&2
exit 1
