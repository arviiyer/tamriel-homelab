#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

failed=0

report() {
  printf 'PUBLICATION SAFETY: %s\n' "$1" >&2
  failed=1
}

candidate_files=()
candidate_list=$(mktemp)
trap 'rm -f "$candidate_list"' EXIT
if git ls-files --cached --others --exclude-standard -z > "$candidate_list"; then
  mapfile -d '' candidate_files < "$candidate_list"
else
  report 'failed to enumerate publication candidates'
fi

revisions=()
if revision_output=$(git rev-list --all); then
  if [[ -n "$revision_output" ]]; then
    mapfile -t revisions <<< "$revision_output"
  fi
else
  report 'failed to enumerate retained Git history'
fi

for path in "${candidate_files[@]}"; do
  lower_path=${path,,}
  screenshot_path=0

  case "$lower_path" in
    .env|.env.*|*/.env|*/.env.*|\
    *.tfstate|*.tfstate.*|*.pcap|*.pcapng|*.log|*.sqlite|*.sqlite3|*.db|\
    *.sql|*.sql.*|*.dump|*.dump.*|*.bak|*.bak.*|*.backup|*.backup.*|\
    *.tar|*.tar.*|*.tgz|*.zip|*.7z|*.rar|*.gz|*.xz|\
    *.vma|*.vma.*|*.vmdk|*.qcow2|*.raw|\
    *.pem|*.p12|*.pfx|*.key|*.ppk|*.gpg|*.age|*.enc|*.kdbx|\
    *.der|*.cer|*.crt|*.csr|*.ovpn|*.mobileconfig|\
    *.xml|*.har|*.pdf|*.pyc|\
    id_rsa|id_ed25519|secrets/*|*/secrets/*|artifacts/*|*/artifacts/*|\
    exports/*|*/exports/*|backups/*|*/backups/*|\
    restore-output/*|*/restore-output/*|recovery-output/*|*/recovery-output/*)
      report "prohibited tracked path: $path"
      ;;
  esac

  case "$lower_path" in
    evidence/screenshots/*.png|evidence/screenshots/*.jpg|\
    evidence/screenshots/*.jpeg|evidence/screenshots/*.webp)
      screenshot_path=1
      review="${path%.*}.review.md"
      if ! git ls-files --error-unmatch "$review" >/dev/null 2>&1; then
        report "screenshot is missing review record: $review"
      fi
      ;;
  esac

  if [[ -L "$path" ]]; then
    report "symbolic links are prohibited: $path"
    continue
  fi

  if [[ -f "$path" ]]; then
    size=$(stat -c '%s' "$path")
    if (( size > 2 * 1024 * 1024 )); then
      report "tracked file exceeds 2 MiB review limit: $path"
    fi

    if (( screenshot_path == 0 )) && [[ -s "$path" ]] &&
      ! grep -Iq '' -- "$path"; then
      report "non-text publication file is prohibited: $path"
    fi
  fi
done

if tracked_entries=$(git ls-files --stage); then
  while read -r mode _object _stage tracked_path; do
    case "$mode" in
      100644|100755)
        ;;
      120000)
        report "symbolic links are prohibited: $tracked_path"
        ;;
      160000)
        report "Git submodules are prohibited: $tracked_path"
        ;;
      *)
        report "unsupported tracked file mode $mode: $tracked_path"
        ;;
    esac
  done <<< "$tracked_entries"
else
  report 'failed to inspect tracked file modes'
fi

searchable_files=()
for path in "${candidate_files[@]}"; do
  if [[ -f "$path" ]]; then
    searchable_files+=("$path")
  fi
done

check_regex() {
  local description=$1
  local pattern=$2
  local matches
  local search_status

  if ((${#searchable_files[@]} != 0)); then
    if matches=$(grep -lEIH -- "$pattern" "${searchable_files[@]}"); then
      report "$description in the current tree"
      printf '%s\n' "$matches" >&2
    else
      search_status=$?
      if (( search_status > 1 )); then
        report "failed current-tree scan: $description"
      fi
    fi
  fi

  if matches=$(git grep --cached -l -I -E -e "$pattern" -- 2>/dev/null); then
    report "$description in the staged index"
    printf '%s\n' "$matches" >&2
  else
    search_status=$?
    if (( search_status > 1 )); then
      report "failed staged-index scan: $description"
    fi
  fi

  if ((${#revisions[@]} != 0)); then
    if matches=$(git grep -l -I -E -e "$pattern" \
      "${revisions[@]}" -- 2>/dev/null); then
      report "$description in retained Git history"
      printf '%s\n' "$matches" >&2
    else
      search_status=$?
      if (( search_status > 1 )); then
        report "failed history scan: $description"
      fi
    fi
  fi
}

check_regex \
  'private IPv4 address found; use RFC 5737 documentation ranges' \
  '(^|[^0-9])(10[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}|192[.]168[.][0-9]{1,3}[.][0-9]{1,3}|172[.](1[6-9]|2[0-9]|3[01])[.][0-9]{1,3}[.][0-9]{1,3})([^0-9]|$)'

check_regex \
  'overlay-network address found; use a public alias' \
  '(^|[^0-9])100[.](6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])[.][0-9]{1,3}[.][0-9]{1,3}([^0-9]|$)'

check_regex \
  'user-specific checkout path found; use a generic public path' \
  '(/(home|Users)/[A-Za-z0-9._-]+/(code(base)?|src|projects|workspace|repos(itories)?)/|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\(code|src|projects|workspace|repos(itories)?)\\)'
check_regex \
  'MAC address found; remove device identity' \
  '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}'
check_regex \
  'SSH public key found; remove host or user identity' \
  'ssh-(rsa|ed25519|ecdsa)[[:space:]]+[A-Za-z0-9+/]{20,}'
check_regex \
  'private key marker found' \
  'BEGIN ([A-Z0-9 ]+ )?PRIVATE K''EY'
check_regex 'Ansible Vault payload found' 'ANSIBLE_''VAULT'

denylist_file=${PUBLIC_SAFETY_DENYLIST_FILE:-}
if [[ -n "$denylist_file" ]]; then
  denylist_valid=1

  if [[ ! -f "$denylist_file" || ! -r "$denylist_file" ]]; then
    report 'private denylist is not a readable regular file'
    denylist_valid=0
  else
    denylist_path=$(realpath "$denylist_file")
    case "$denylist_path" in
      "$repo_root"|"$repo_root"/*)
        report 'private denylist must remain outside the repository'
        denylist_valid=0
        ;;
    esac
  fi

  if (( denylist_valid != 0 )); then
    denylist_entries=0
    while IFS= read -r token || [[ -n "$token" ]]; do
      if [[ -z "$token" || ${#token} -lt 4 ]]; then
        report 'private denylist contains a blank or undersized entry'
        denylist_valid=0
        break
      fi
      if [[ "$token" == *$'\r'* || "$token" =~ ^[[:space:]] ||
        "$token" =~ [[:space:]]$ ]]; then
        report 'private denylist contains surrounding whitespace or CRLF data'
        denylist_valid=0
        break
      fi
      denylist_entries=$((denylist_entries + 1))
    done < "$denylist_path"

    if (( denylist_entries == 0 )); then
      report 'private denylist contains no entries'
      denylist_valid=0
    fi
  fi

  if (( denylist_valid != 0 )); then
    if ((${#searchable_files[@]} != 0)); then
      if matches=$(grep -lFIi -f "$denylist_path" -- "${searchable_files[@]}"); then
        report 'private denylist match found in the current tree'
      else
        search_status=$?
        if (( search_status > 1 )); then
          report 'private denylist current-tree scan failed'
        fi
      fi
    fi

    if matches=$(git grep --cached -l -I -F -i -f "$denylist_path" \
      -- 2>/dev/null); then
      report 'private denylist match found in the staged index'
    else
      search_status=$?
      if (( search_status > 1 )); then
        report 'private denylist staged-index scan failed'
      fi
    fi

    if ((${#revisions[@]} != 0)); then
      if matches=$(git grep -l -I -F -i -f "$denylist_path" \
        "${revisions[@]}" -- 2>/dev/null); then
        report 'private denylist match found in retained Git history'
      else
        search_status=$?
        if (( search_status > 1 )); then
          report 'private denylist history scan failed'
        fi
      fi

      if history_listing=$(git log --all --name-only \
        --format='%H%n%an%n%ae%n%cn%n%ce%n%B'); then
        if grep -Fi -f "$denylist_path" >/dev/null <<< "$history_listing"; then
          report 'private denylist match found in Git metadata or paths'
        fi
      else
        report 'failed to inspect Git metadata and paths'
      fi
    fi

    if current_paths=$(printf '%s\n' "${candidate_files[@]}"); then
      if grep -Fi -f "$denylist_path" >/dev/null <<< "$current_paths"; then
        report 'private denylist match found in a publication path'
      fi
    else
      report 'failed to inspect publication paths'
    fi
  fi
fi

if (( failed != 0 )); then
  exit 1
fi

if [[ -n "$denylist_file" ]]; then
  printf 'Publication safety checks passed, including private denylist.\n'
else
  printf 'Publication safety generic checks passed; private denylist not run.\n'
fi
