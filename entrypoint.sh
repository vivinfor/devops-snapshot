#!/usr/bin/env sh
set -eu

ENV_NAME="${ENV:-prd}"

echo ">>> Entrypoint (ENV=${ENV_NAME})"

exec "$@"
