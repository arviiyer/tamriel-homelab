#!/usr/bin/env bash
set -Eeuo pipefail

ci_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
temporary=$(mktemp -d "${TMPDIR:-/tmp}/example-deploy-policy.XXXXXX")
trap 'rm -rf -- "$temporary"' EXIT HUP INT TERM

ssh-keygen -q -t ed25519 -N '' -f "$temporary/host-key"
{
  printf 'HostKey %s\n' "$temporary/host-key"
  cat "$ci_root/target/sshd_config.example"
} >"$temporary/sshd_config"

sshd=$(command -v sshd)
"$sshd" -t -f "$temporary/sshd_config"
for address in 192.0.2.40 198.51.100.40; do
  effective=$(
    "$sshd" -T -f "$temporary/sshd_config" \
      -C "user=deploy-request,addr=${address},host=apps-01.example.com"
  )
  grep -Fxiq \
    'forcecommand sudo -n /usr/local/sbin/restricted-deploy' <<<"$effective"
  grep -Fxiq 'disableforwarding yes' <<<"$effective"
  grep -Fxiq 'permittty no' <<<"$effective"
  grep -Fxiq 'passwordauthentication no' <<<"$effective"
done

visudo -cf "$ci_root/target/sudoers.example"

expected_key_policy='from="192.0.2.40",restrict,command="sudo -n /usr/local/sbin/restricted-deploy" <deployment-public-key>'
grep -Fxq "$expected_key_policy" "$ci_root/target/authorized_keys.example"

printf 'Restricted target policy validation passed.\n'
