#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel)
image="tamriel/disposable-delivery-drill:local-$$-$RANDOM"
build_context=
container_id=
image_built=false
build_only=false

cleanup() {
  local status=$?
  if [[ -n "$container_id" ]]; then
    docker container rm --force --volumes "$container_id" >/dev/null 2>&1 || true
  fi
  if [[ "$image_built" == true ]]; then
    docker image rm --force "$image" >/dev/null 2>&1 || true
  fi
  if [[ -n "$build_context" ]]; then
    rm -rf -- "$build_context"
  fi
  return "$status"
}
trap cleanup EXIT INT TERM

case ${1:-} in
  '') ;;
  --build-only)
    build_only=true
    ;;
  *)
    printf 'usage: %s [--build-only]\n' "${0##*/}" >&2
    exit 2
    ;;
esac
[[ $# -le 1 ]] || {
  printf 'usage: %s [--build-only]\n' "${0##*/}" >&2
  exit 2
}

if ! docker info >/dev/null 2>&1; then
  printf 'ERROR: an available Docker daemon is required\n' >&2
  exit 1
fi
if docker image inspect "$image" >/dev/null 2>&1; then
  printf 'ERROR: generated disposable image tag already exists\n' >&2
  exit 1
fi

build_context=$(mktemp -d "${TMPDIR:-/tmp}/disposable-delivery-build.XXXXXX")
install -m 0644 "$script_dir/disposable-host/Dockerfile" \
  "$build_context/Dockerfile"
install -m 0755 "$script_dir/disposable_host_drill.sh" \
  "$build_context/disposable_host_drill.sh"
install -m 0755 "$repo_root/automation/ci/target/restricted_deploy.py" \
  "$build_context/restricted_deploy.py"
install -m 0644 "$repo_root/automation/ci/target/sshd_config.example" \
  "$build_context/sshd_config.example"
install -m 0644 "$repo_root/automation/ci/target/sudoers.example" \
  "$build_context/sudoers.example"

printf 'Building the disposable target from selected public artifacts...\n'
docker build \
  --file "$build_context/Dockerfile" \
  --tag "$image" \
  "$build_context"
image_built=true

if [[ "$build_only" == true ]]; then
  printf 'PASS: disposable target image built successfully\n'
  exit 0
fi

printf 'Starting the network-isolated disposable target...\n'
container_id=$(docker create \
  --privileged \
  --network none \
  --hostname apps-01 \
  --env DISPOSABLE_DELIVERY_DRILL=1 \
  "$image")
docker start --attach "$container_id"

removed_container=$container_id
docker container rm --volumes "$container_id" >/dev/null
container_id=
if docker container inspect "$removed_container" >/dev/null 2>&1; then
  printf 'ERROR: disposable target still exists after the drill\n' >&2
  exit 1
fi

docker image rm "$image" >/dev/null
image_built=false
rm -rf -- "$build_context"
build_context=
trap - EXIT INT TERM
printf 'PASS: disposable target, anonymous volumes, and image tag were removed\n'
