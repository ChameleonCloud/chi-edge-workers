#!/bin/bash
set -euo pipefail

DEVICE_UUID="$1"
DEVICE_LOCAL_NAME="$2"

BALENA_ENVS_JSON="$(balena envs -d $DEVICE_UUID --json)"

get_env_from_json(){
    local key=$1
    local value="$(jq --arg key $key '.[] | select(.name==$key).value' <<<$BALENA_ENVS_JSON)"
    echo "${value}"

}

K3S_TOKEN=$(get_env_from_json "K3S_TOKEN")
K3S_URL=$(get_env_from_json "K3S_URL")
OS_APPLICATION_CREDENTIAL_ID=$(get_env_from_json "OS_APPLICATION_CREDENTIAL_ID")
OS_APPLICATION_CREDENTIAL_SECRET=$(get_env_from_json "OS_APPLICATION_CREDENTIAL_SECRET")
OS_AUTH_URL=$(get_env_from_json "OS_AUTH_URL")

set -x
balena push "$DEVICE_LOCAL_NAME" \
    --env "${K3S_TOKEN}" \
    --env "${K3S_URL}" \
    --env "${OS_APPLICATION_CREDENTIAL_ID}" \
    --env "${OS_APPLICATION_CREDENTIAL_SECRET}" \
    --env "${OS_AUTH_URL}"
set +x
