#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repositories_file=${REPOSITORIES_FILE:-"${script_dir}/repositories.tsv"}
baseline_dir=${BASELINE_DIR:-"${script_dir}/var/baseline"}
pushgateway_url=${PUSHGATEWAY_URL:-}
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/tamriel-trivy-XXXXXX")
current_dir="${work_dir}/current"
status_file="${work_dir}/repository-status.tsv"
findings_metrics="${work_dir}/findings.prom"
delta_report="${current_dir}/_delta-report.json"
health_metrics="${work_dir}/health.prom"
scan_started_at=$(date +%s)

cleanup() {
    rm -rf -- "$work_dir"
}
trap cleanup EXIT

log() {
    printf '[trivy-scan %s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
    printf 'trivy-scan: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

validate_alias() {
    [[ $1 =~ ^[a-z0-9]([a-z0-9_]|-[a-z0-9_])*$ ]]
}

load_repositories() {
    local line_number=0
    local extra

    aliases=()
    clone_urls=()
    revisions=()

    while IFS=$'\t' read -r alias clone_url revision extra || [[ -n ${alias:-} ]]; do
        line_number=$((line_number + 1))
        [[ -z ${alias//[[:space:]]/} ]] && continue
        [[ $alias =~ ^[[:space:]]*# ]] && continue

        if [[ -n ${extra:-} || -z ${clone_url:-} || -z ${revision:-} ]]; then
            fail "${repositories_file}:${line_number}: expected three tab-separated fields"
        fi
        validate_alias "$alias" || fail "${repositories_file}:${line_number}: invalid alias: $alias"
        if printf '%s\n' "${aliases[@]:-}" | grep -Fxq -- "$alias"; then
            fail "${repositories_file}:${line_number}: duplicate alias: $alias"
        fi
        if [[ $clone_url == /* ]]; then
            : # Absolute local paths are supported for tests and offline use.
        elif [[ $clone_url != https://* ]]; then
            fail "${repositories_file}:${line_number}: remote clone URLs must use HTTPS"
        elif [[ $clone_url == *"@"* || $clone_url == *"?"* || $clone_url == *"#"* ]]; then
            fail "${repositories_file}:${line_number}: clone URLs must not contain userinfo, queries, or fragments"
        fi

        aliases+=("$alias")
        clone_urls+=("$clone_url")
        revisions+=("$revision")
    done < "$repositories_file"

    ((${#aliases[@]} > 0)) || fail "repository configuration is empty: $repositories_file"
}

validate_json() {
    python3 - "$1" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
document = json.loads(path.read_text(encoding="utf-8"))
if not isinstance(document, dict):
    raise ValueError(f"Trivy output must be a JSON object: {path}")
if document.get("SchemaVersion") != 2:
    raise ValueError(f"Trivy output SchemaVersion must be 2: {path}")
if not isinstance(document.get("ArtifactName"), str) or not document["ArtifactName"].strip():
    raise ValueError(f"Trivy output has no ArtifactName: {path}")
if document.get("ArtifactType") not in {"filesystem", "repository", "container_image"}:
    raise ValueError(f"Trivy output has an unsupported ArtifactType: {path}")
if not isinstance(document.get("ReportID"), str) or not document["ReportID"].strip():
    raise ValueError(f"Trivy output has no ReportID: {path}")
if "Results" in document and not isinstance(document["Results"], list):
    raise ValueError(f"Trivy output Results must be a list when present: {path}")
PY
}

scan_repository() {
    local alias=$1
    local clone_url=$2
    local revision=$3
    local repository_dir="${work_dir}/repositories/${alias}"
    local misconfiguration_output="${current_dir}/${alias}-misconfig.json"
    local secret_output="${current_dir}/${alias}-secret.json"
    local images_file="${work_dir}/${alias}-images.txt"
    local image image_hash vulnerability_output
    local images=()

    log "[$alias] fetching exact revision"
    git init --quiet "$repository_dir"
    git -C "$repository_dir" remote add origin "$clone_url"
    GIT_TERMINAL_PROMPT=0 git -C "$repository_dir" fetch --quiet --depth=1 origin "$revision"
    git -C "$repository_dir" checkout --quiet --detach FETCH_HEAD

    log "[$alias] scanning configuration"
    trivy config \
        --exit-code 0 \
        --format json \
        --output "$misconfiguration_output" \
        --quiet \
        "$repository_dir"
    validate_json "$misconfiguration_output"

    # Trivy scans the checked-out tree. Full Git-history scanning is a separate
    # Gitleaks control and is not claimed by this pipeline.
    log "[$alias] scanning current repository tree for secrets"
    trivy repo \
        --scanners secret \
        --exit-code 0 \
        --format json \
        --output "$secret_output" \
        --quiet \
        "$repository_dir"
    validate_json "$secret_output"

    python3 "${script_dir}/extract_images.py" "$repository_dir" > "$images_file"
    mapfile -t images < "$images_file"
    log "[$alias] scanning ${#images[@]} referenced image(s)"
    for image in "${images[@]}"; do
        image_hash=$(printf '%s' "$image" | sha256sum | cut -c1-16)
        vulnerability_output="${current_dir}/${alias}--${image_hash}-vuln.json"
        trivy image \
            --scanners vuln \
            --exit-code 0 \
            --format json \
            --output "$vulnerability_output" \
            --quiet \
            --timeout 10m \
            "$image"
        validate_json "$vulnerability_output"
    done
}

write_health_metrics() {
    local overall_success=$1
    local completed_at duration alias status
    completed_at=$(date +%s)
    duration=$((completed_at - scan_started_at))

    {
        printf '# HELP trivy_scan_success Whether the latest scan attempt completed and promoted a baseline\n'
        printf '# TYPE trivy_scan_success gauge\n'
        printf 'trivy_scan_success %s\n' "$overall_success"
        printf '# HELP trivy_scan_attempt_timestamp_seconds Unix timestamp of the latest scan attempt\n'
        printf '# TYPE trivy_scan_attempt_timestamp_seconds gauge\n'
        printf 'trivy_scan_attempt_timestamp_seconds %s\n' "$completed_at"
        printf '# HELP trivy_scan_duration_seconds Duration of the latest scan attempt\n'
        printf '# TYPE trivy_scan_duration_seconds gauge\n'
        printf 'trivy_scan_duration_seconds %s\n' "$duration"
        printf '# HELP trivy_scan_repository_success Whether a repository completed every configured scanner\n'
        printf '# TYPE trivy_scan_repository_success gauge\n'
        while IFS=$'\t' read -r alias status; do
            printf 'trivy_scan_repository_success{repository="%s"} %s\n' "$alias" "$status"
        done < "$status_file"
    } > "$health_metrics"
}

push_metrics() {
    local job=$1
    local metrics_file=$2

    [[ -z $pushgateway_url ]] && return 0
    curl \
        --fail \
        --silent \
        --show-error \
        --max-time 10 \
        --request PUT \
        --data-binary "@${metrics_file}" \
        "${pushgateway_url%/}/metrics/job/${job}"
}

promote_baseline_and_publish() {
    local baseline_parent staging_dir old_dir
    baseline_parent=$(dirname -- "$baseline_dir")
    mkdir -p -- "$baseline_parent" || return 1
    staging_dir=$(mktemp -d "${baseline_parent}/.trivy-baseline-new-XXXXXX") || return 1
    old_dir="${baseline_parent}/.trivy-baseline-old-$$"

    cp -- "${current_dir}"/*.json "$staging_dir/" || {
        rm -rf -- "$staging_dir"
        return 1
    }
    if [[ -d $baseline_dir ]]; then
        mv -- "$baseline_dir" "$old_dir" || {
            rm -rf -- "$staging_dir"
            return 1
        }
    fi
    if ! mv -- "$staging_dir" "$baseline_dir"; then
        rm -rf -- "$staging_dir"
        if [[ -d $old_dir ]] && ! mv -- "$old_dir" "$baseline_dir"; then
            log "CRITICAL: candidate install and baseline rollback both failed"
        fi
        return 1
    fi

    if ! push_metrics trivy_findings "$findings_metrics"; then
        rm -rf -- "$baseline_dir" || return 1
        if [[ -d $old_dir ]] && ! mv -- "$old_dir" "$baseline_dir"; then
            log "CRITICAL: findings publication and baseline rollback both failed"
        fi
        return 1
    fi

    if ! rm -rf -- "$old_dir"; then
        log "WARNING: baseline advanced but old baseline cleanup failed: $old_dir"
    fi
}

require_command curl
require_command flock
require_command git
require_command python3
require_command sha256sum
require_command trivy

[[ -f $repositories_file ]] || fail "repository configuration not found: $repositories_file"
baseline_parent=$(dirname -- "$baseline_dir")
mkdir -p -- "$current_dir" "${work_dir}/repositories" "$baseline_parent"
exec 9>"${baseline_parent}/.trivy-scan.lock"
flock --nonblock 9 || fail "another scan is already running for baseline: $baseline_dir"
load_repositories
: > "$status_file"

initialize_baseline=${INITIALIZE_BASELINE:-0}
if [[ $initialize_baseline != 0 && $initialize_baseline != 1 ]]; then
    fail "INITIALIZE_BASELINE must be 0 or 1"
fi
if [[ $initialize_baseline == 1 && -e $baseline_dir ]]; then
    fail "refusing to initialize over an existing baseline: $baseline_dir"
fi
if [[ $initialize_baseline == 0 && ! -f ${baseline_dir}/_baseline.json ]]; then
    fail "no valid baseline found; set INITIALIZE_BASELINE=1 for the first complete scan"
fi

failed=0
for index in "${!aliases[@]}"; do
    alias=${aliases[$index]}
    set +e
    (
        set -e
        scan_repository "$alias" "${clone_urls[$index]}" "${revisions[$index]}"
    )
    status=$?
    set -e

    if ((status == 0)); then
        printf '%s\t1\n' "$alias" >> "$status_file"
    else
        printf '%s\t0\n' "$alias" >> "$status_file"
        failed=1
        log "[$alias] scan failed with exit status $status"
    fi
done

if ((failed != 0)); then
    write_health_metrics 0
    push_metrics trivy_health "$health_metrics" || log "failed to push scan-health metrics"
    fail "one or more repository scans failed; previous baseline preserved"
fi

delta_arguments=(
    report
    --current-dir "$current_dir"
    --last-dir "$baseline_dir"
    --repositories "$repositories_file"
    --output "$findings_metrics"
    --report-output "$delta_report"
    --manifest-output "${current_dir}/_baseline.json"
    --scan-time "$(date +%s)"
)
if [[ $initialize_baseline == 1 ]]; then
    delta_arguments+=(--initialize-baseline)
fi

if ! python3 "${script_dir}/delta.py" "${delta_arguments[@]}"; then
    write_health_metrics 0
    push_metrics trivy_health "$health_metrics" || log "failed to push scan-health metrics"
    fail "finding validation or publication failed; previous baseline preserved"
fi

if ! promote_baseline_and_publish; then
    write_health_metrics 0
    push_metrics trivy_health "$health_metrics" || log "failed to push scan-health metrics"
    fail "baseline promotion or findings publication failed; inspect local baseline state"
fi

write_health_metrics 1
push_metrics trivy_health "$health_metrics" || fail "baseline promoted but health metric push failed"
log "scan complete; baseline promoted"
