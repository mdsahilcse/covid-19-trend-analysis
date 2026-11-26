#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 ]]; then
    printf 'Usage: %s [export-directory]\n' "$0" >&2
    exit 2
fi

scripts_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
input_path=${1:-"$scripts_dir/../data/processed"}
if [[ ! -d "$input_path" ]]; then
    printf 'Export directory does not exist: %s\n' "$input_path" >&2
    exit 2
fi
input_dir=$(cd -- "$input_path" && pwd -P)
for filename in countries.csv dates.csv daily.csv weekly.csv; do
    if [[ ! -r "$input_dir/$filename" ]]; then
        printf 'Missing or unreadable export: %s\n' "$input_dir/$filename" >&2
        exit 2
    fi
done

docker info >/dev/null
image='docker.io/gvenzl/oracle-free:23.26.3-slim-faststart@sha256:31aa4d1623c302e495e90a35b5ef809c8e51ba800e5a64dd4c2dd6e346ec6831'
container=$(docker run -d --rm \
    -e ORACLE_RANDOM_PASSWORD=yes \
    --health-cmd healthcheck.sh \
    --health-interval 2s \
    --health-timeout 5s \
    --mount "type=bind,source=$input_dir,target=/input,readonly" \
    --mount "type=bind,source=$scripts_dir,target=/workflow,readonly" \
    "$image")
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'Waiting for Oracle Database Free...\n'
health=starting
for ((attempt = 0; attempt < 150; attempt++)); do
    health=$(docker inspect --format '{{.State.Health.Status}}' "$container")
    if [[ "$health" == healthy ]]; then
        break
    fi
    sleep 2
done
if [[ "$health" != healthy ]]; then
    printf 'Oracle did not become healthy within five minutes (status: %s).\n' "$health" >&2
    exit 1
fi

docker exec "$container" sqlplus -L -S '/ as sysdba' @/workflow/00_setup.sql
docker exec "$container" sqlplus -L -S '/ as sysdba' @/workflow/03_refresh.sql
