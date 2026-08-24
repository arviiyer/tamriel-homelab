#!/usr/bin/env bash
set -euo pipefail

readonly service_name=example-api
readonly source_address=192.0.2.40
readonly target_address=192.0.2.41
readonly target_port=2222
readonly repository=/var/lib/example-deploy/repositories/apps.git
readonly state_file=/var/lib/example-deploy/state/example-api.json
readonly pending_file=/var/lib/example-deploy/state/example-api.pending.json
readonly live_compose=/srv/example-api/compose.yml
readonly repository_compose=services/example-api/compose.yml
readonly drill_root=/run/disposable-delivery-drill

dockerd_pid=
registry_pid=
sshd_pid=

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

pass() {
  printf 'PASS: %s\n' "$1"
}

stop_process() {
  local pid=$1
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
  fi
}

cleanup() {
  local status=$?
  if docker info >/dev/null 2>&1 && [[ -f "$live_compose" ]]; then
    docker compose \
      --project-name "$service_name" \
      --project-directory /srv/example-api \
      --file "$live_compose" \
      down --remove-orphans >/dev/null 2>&1 || true
  fi
  stop_process "$sshd_pid"
  stop_process "$registry_pid"
  stop_process "$dockerd_pid"
  return "$status"
}
trap cleanup EXIT INT TERM

wait_for_docker() {
  for _ in $(seq 1 30); do
    if docker info >/dev/null 2>&1; then
      return
    fi
    sleep 1
  done
  fail "nested Docker daemon did not become ready"
}

wait_for_registry() {
  for _ in $(seq 1 30); do
    if curl --fail --silent --show-error \
      --cacert "$drill_root/registry/registry.crt" \
      https://registry.example.com/v2/ >/dev/null 2>&1; then
      return
    fi
    sleep 1
  done
  fail "synthetic registry did not become ready"
}

fixture_image() {
  local revision=$1
  local include_health=$2
  local context="$drill_root/images/$revision"
  local tag="registry.example.com/example-api:$revision"
  local httpd_binary
  local -a loaders
  local repository_digest

  install -d -m 0755 "$context/rootfs/bin" "$context/rootfs/lib" "$context/rootfs/www"
  httpd_binary=$(readlink -f "$(command -v httpd)")
  install -m 0755 "$httpd_binary" "$context/rootfs/bin/httpd"
  loaders=(/lib/ld-musl-*.so.1)
  [[ ${#loaders[@]} -eq 1 && -f ${loaders[0]} ]] || \
    fail "could not identify the fixture dynamic loader"
  install -m 0755 "${loaders[0]}" "$context/rootfs/lib/$(basename "${loaders[0]}")"
  printf '%s\n' "$revision" > "$context/rootfs/www/version"
  if [[ "$include_health" == true ]]; then
    printf 'healthy\n' > "$context/rootfs/www/health"
  fi
  chmod 0644 "$context/rootfs/www/"*

  cat > "$context/Dockerfile" <<'EOF'
FROM scratch
COPY rootfs /
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/bin/httpd", "-f", "-p", "8080", "-h", "/www"]
EOF

  docker build --quiet --tag "$tag" "$context" >/dev/null
  docker push --quiet "$tag" >/dev/null
  repository_digest=$(
    docker image inspect --format '{{index .RepoDigests 0}}' "$tag"
  )
  printf '%s@%s\n' "$tag" "${repository_digest#*@}"
}

write_compose() {
  local image=$1
  local policy_change=${2:-false}

  cat > "$drill_root/source/$repository_compose" <<EOF
services:
  example-api:
    image: $image
    ports:
      - "127.0.0.1:8080:8080"
    read_only: true
    user: "65532:65532"
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
EOF
  if [[ "$policy_change" == true ]]; then
    cat >> "$drill_root/source/$repository_compose" <<'EOF'
    environment:
      DRILL_POLICY_CHANGE: rejected
EOF
  fi
}

commit_revision() {
  local message=$1
  git -C "$drill_root/source" add "$repository_compose"
  git -C "$drill_root/source" commit --quiet --message "$message"
  git -C "$drill_root/source" rev-parse HEAD
}

assert_state() {
  local expected_current=$1
  local expected_previous=$2
  python3 - "$state_file" "$expected_current" "$expected_previous" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_previous = None if sys.argv[3] == "none" else sys.argv[3]
expected = {"current": sys.argv[2], "previous": expected_previous}
if payload != expected:
    raise SystemExit(f"unexpected deployment state: {payload!r}")
PY
}

assert_pending() {
  local expected_source=$1
  local expected_target=$2
  python3 - "$pending_file" "$expected_source" "$expected_target" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {"operation": "deploy", "source": sys.argv[2], "target": sys.argv[3]}
if payload != expected:
    raise SystemExit(f"unexpected pending transaction: {payload!r}")
PY
}

assert_live_revision() {
  local revision=$1
  git --git-dir="$repository" show "$revision:$repository_compose" \
    > "$drill_root/expected-compose.yml"
  cmp --silent "$drill_root/expected-compose.yml" "$live_compose" || \
    fail "live Compose file does not match the recorded revision"
}

assert_service() {
  local expected_version=$1
  local observed
  for _ in $(seq 1 15); do
    if curl --fail --silent http://127.0.0.1:8080/health >/dev/null 2>&1; then
      observed=$(curl --fail --silent http://127.0.0.1:8080/version || true)
      if [[ "$observed" == "$expected_version" ]]; then
        return
      fi
    fi
    sleep 1
  done
  docker compose \
    --project-name "$service_name" \
    --project-directory /srv/example-api \
    --file "$live_compose" \
    ps >&2 || true
  docker compose \
    --project-name "$service_name" \
    --project-directory /srv/example-api \
    --file "$live_compose" \
    logs --no-color >&2 || true
  fail "service did not reach the expected healthy revision"
}

request() {
  # The caller supplies the complete allowlisted request as one SSH argument.
  # shellcheck disable=SC2029
  ssh "${ssh_options[@]}" "deploy-request@$target_address" "$1"
}

[[ ${DISPOSABLE_DELIVERY_DRILL:-} == 1 ]] || \
  fail "explicit disposable-target confirmation is required"
[[ $(id -u) == 0 ]] || fail "the disposable target must run as root"
[[ -f /.dockerenv ]] || fail "the drill must run inside its disposable container"
[[ -z $(ip route show default) ]] || \
  fail "the disposable target must not have a default network route"

for protected_path in \
  /var/lib/example-deploy \
  /srv/example-api \
  /run/example-deploy; do
  [[ ! -e "$protected_path" && ! -L "$protected_path" ]] || \
    fail "a deployment path already exists: $protected_path"
done
pass "entry criteria confirmed network and path isolation"

install -d -m 0700 \
  "$drill_root/registry" \
  /etc/docker/certs.d/registry.example.com \
  /var/lib/registry
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 1 \
  -subj /CN=registry.example.com \
  -addext subjectAltName=DNS:registry.example.com \
  -keyout "$drill_root/registry/registry.key" \
  -out "$drill_root/registry/registry.crt" >/dev/null 2>&1
install -m 0644 "$drill_root/registry/registry.crt" \
  /etc/docker/certs.d/registry.example.com/ca.crt
cat > "$drill_root/registry/config.yml" <<'EOF'
version: 0.1
log:
  level: error
storage:
  filesystem:
    rootdirectory: /var/lib/registry
http:
  addr: 127.0.0.1:443
  tls:
    certificate: /run/disposable-delivery-drill/registry/registry.crt
    key: /run/disposable-delivery-drill/registry/registry.key
EOF
printf '127.0.0.1 registry.example.com\n' >> /etc/hosts

registry_binary=$(command -v docker-registry || command -v registry) || \
  fail "registry binary is unavailable"
"$registry_binary" serve "$drill_root/registry/config.yml" \
  > "$drill_root/registry-output" 2>&1 &
registry_pid=$!
wait_for_registry

dockerd \
  --host unix:///var/run/docker.sock \
  --data-root "$drill_root/docker" \
  --exec-root "$drill_root/docker-exec" \
  --pidfile "$drill_root/dockerd.pid" \
  --storage-driver vfs \
  > "$drill_root/dockerd-output" 2>&1 &
dockerd_pid=$!
wait_for_docker
pass "nested Docker daemon and synthetic TLS registry started"

image_a=$(fixture_image revision-a true)
image_b=$(fixture_image revision-b true)
image_c=$(fixture_image revision-c false)
pass "three synthetic digest-pinned service images published locally"

install -d -m 0755 "$(dirname "$drill_root/source/$repository_compose")"
git init --quiet --object-format=sha1 --initial-branch=main "$drill_root/source"
git -C "$drill_root/source" config user.name "Synthetic Drill"
git -C "$drill_root/source" config user.email "drill@example.com"

write_compose "$image_a"
revision_a=$(commit_revision "revision a: healthy baseline")
write_compose "$image_b"
revision_b=$(commit_revision "revision b: healthy promotion")
write_compose "$image_c"
revision_c=$(commit_revision "revision c: failed health check")
write_compose "$image_c" true
revision_d=$(commit_revision "revision d: rejected policy change")

install -d -m 0700 \
  /var/lib/example-deploy/repositories \
  /var/lib/example-deploy/state \
  /srv/example-api \
  /run/example-deploy
git clone --quiet --bare "$drill_root/source" "$repository"
install -o root -g root -m 0755 \
  /opt/disposable-delivery-drill/restricted_deploy.py \
  /usr/local/sbin/restricted-deploy
printf '{"current":"%s","previous":null}\n' "$revision_a" > "$state_file"
chmod 0600 "$state_file"
git --git-dir="$repository" show "$revision_a:$repository_compose" > "$live_compose"
chmod 0600 "$live_compose"

docker compose \
  --project-name "$service_name" \
  --project-directory /srv/example-api \
  --file "$live_compose" \
  pull --quiet
docker compose \
  --project-name "$service_name" \
  --project-directory /srv/example-api \
  --file "$live_compose" \
  up --detach --pull never >/dev/null
assert_service revision-a
pass "healthy baseline bootstrapped from revision a"

useradd --create-home --shell /bin/sh deploy-request
passwd --delete deploy-request >/dev/null
install -d -o deploy-request -g deploy-request -m 0700 /home/deploy-request/.ssh
ssh-keygen -q -t ed25519 -N '' -f "$drill_root/request-key"
public_key=$(<"$drill_root/request-key.pub")
printf 'from="%s",restrict,command="sudo -n /usr/local/sbin/restricted-deploy" %s\n' \
  "$source_address" "$public_key" > /home/deploy-request/.ssh/authorized_keys
chown deploy-request:deploy-request /home/deploy-request/.ssh/authorized_keys
chmod 0600 /home/deploy-request/.ssh/authorized_keys
install -m 0440 /opt/disposable-delivery-drill/sudoers.example \
  /etc/sudoers.d/restricted-deploy
visudo -cf /etc/sudoers.d/restricted-deploy >/dev/null
ssh-keygen -q -t ed25519 -N '' -f "$drill_root/ssh-host-key"

ip address add "$source_address/32" dev lo
ip address add "$target_address/32" dev lo
cat > "$drill_root/sshd_config" <<EOF
Port $target_port
ListenAddress $target_address
HostKey $drill_root/ssh-host-key
PidFile $drill_root/sshd.pid
AuthorizedKeysFile .ssh/authorized_keys
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AllowUsers deploy-request
LogLevel ERROR
EOF
cat /opt/disposable-delivery-drill/sshd_config.example \
  >> "$drill_root/sshd_config"
sshd_binary=$(command -v sshd) || fail "sshd binary is unavailable"
"$sshd_binary" -t -f "$drill_root/sshd_config"
"$sshd_binary" -D -e -f "$drill_root/sshd_config" \
  > "$drill_root/sshd-output" 2>&1 &
sshd_pid=$!

for _ in $(seq 1 30); do
  if ssh-keyscan -q -p "$target_port" "$target_address" \
    > "$drill_root/known-hosts" 2>/dev/null && \
    [[ -s "$drill_root/known-hosts" ]]; then
    break
  fi
  sleep 1
done
if [[ ! -s "$drill_root/known-hosts" ]]; then
  while IFS= read -r line; do
    printf 'sshd: %s\n' "$line" >&2
  done < "$drill_root/sshd-output"
  fail "disposable SSH endpoint did not start"
fi

ssh_options=(
  -o BatchMode=yes
  -o ConnectTimeout=5
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=yes
  -o "UserKnownHostsFile=$drill_root/known-hosts"
  -i "$drill_root/request-key"
  -p "$target_port"
  -b "$source_address"
)

if request id > "$drill_root/rejected-shell-output" 2>&1; then
  fail "forced-command boundary accepted a shell command"
fi
if [[ $(<"$drill_root/rejected-shell-output") != *"allowed commands"* ]]; then
  fail "shell request did not reach the restricted parser"
fi
pass "forced-command SSH and sudo boundary rejected shell access"

request "deploy $service_name $revision_b" \
  > "$drill_root/deploy-b-output" 2>&1
assert_state "$revision_b" "$revision_a"
[[ ! -e "$pending_file" ]] || fail "pending metadata remained after promotion"
assert_live_revision "$revision_b"
assert_service revision-b
pass "exact revision b passed policy, deployment, and health validation"

if request "deploy $service_name $revision_d" \
  > "$drill_root/rejected-policy-output" 2>&1; then
  fail "candidate policy accepted a non-image change"
fi
if [[ $(<"$drill_root/rejected-policy-output") != \
  *"candidate changes more than the allowlisted image digest"* ]]; then
  fail "candidate policy did not report the expected rejection"
fi
assert_state "$revision_b" "$revision_a"
assert_live_revision "$revision_b"
assert_service revision-b
pass "image-only candidate policy rejected an environment change"

request "deploy $service_name $revision_c" \
  > "$drill_root/deploy-c-output" 2>&1 &
failed_deploy_pid=$!
observed_pending=false
for _ in $(seq 1 30); do
  if [[ -f "$pending_file" ]] && \
    [[ $(curl --silent http://127.0.0.1:8080/version || true) == revision-c ]]; then
    observed_pending=true
    break
  fi
  sleep 1
done
[[ "$observed_pending" == true ]] || \
  fail "failed-health candidate and pending transaction were not observed"
assert_pending "$revision_b" "$revision_c"
if curl --fail --silent http://127.0.0.1:8080/health >/dev/null 2>&1; then
  fail "revision c unexpectedly passed its health check"
fi
pass "failed-health revision c was active with durable pending metadata"

set +e
wait "$failed_deploy_pid"
failed_deploy_status=$?
set -e
[[ "$failed_deploy_status" -ne 0 ]] || \
  fail "failed-health deployment returned success"
if [[ $(<"$drill_root/deploy-c-output") != \
  *"the recorded current revision was restored"* ]]; then
  fail "failed-health deployment did not report automatic recovery"
fi
assert_state "$revision_b" "$revision_a"
[[ ! -e "$pending_file" ]] || \
  fail "pending metadata remained after automatic recovery"
assert_live_revision "$revision_b"
assert_service revision-b
pass "failed-health deployment restored revision b and preserved state"

request "rollback $service_name $revision_b" \
  > "$drill_root/rollback-output" 2>&1
assert_state "$revision_a" "$revision_b"
[[ ! -e "$pending_file" ]] || fail "pending metadata remained after rollback"
assert_live_revision "$revision_a"
assert_service revision-a
pass "guarded rollback selected recorded revision a and passed health validation"

docker compose \
  --project-name "$service_name" \
  --project-directory /srv/example-api \
  --file "$live_compose" \
  down --remove-orphans >/dev/null
[[ -z $(docker container list --quiet) ]] || \
  fail "running nested service containers remained after cleanup"
[[ -z $(docker container list --all --quiet) ]] || \
  fail "stopped nested service containers remained after cleanup"
if docker network inspect example-api_default >/dev/null 2>&1; then
  fail "nested service network remained after cleanup"
fi
pass "nested service resources were removed"

trap - EXIT INT TERM
stop_process "$sshd_pid"
stop_process "$registry_pid"
stop_process "$dockerd_pid"
printf 'Disposable delivery drill completed successfully.\n'
