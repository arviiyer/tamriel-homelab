#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
cp "$source_dir"/*.tf "$work/"
mkdir "$work/tests"
cp "$source_dir"/tests/*.tftest.hcl "$work/tests/"
ssh-keygen -q -t ed25519 -N '' -C 'fixture' -f "$work/tests/operator"
rm "$work/tests/operator"
terraform -chdir="$source_dir" fmt -check -recursive
terraform -chdir="$work" init -backend=false -input=false
terraform -chdir="$work" validate
terraform -chdir="$work" test
