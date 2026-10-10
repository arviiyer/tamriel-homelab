# Renovate

[Home](../../README.md) · [Automation](../README.md) · [Deployment](../ci/README.md)

Renovate checks the Docker images in my private Forgejo repositories and opens
update pull requests. A daily timer runs the bot. I review and merge the changes,
then apply them separately on the service host.

[![Compose checks on an update pull request in Forgejo](../../screenshots/forgejo-validation-run.png)](../../screenshots/README.md#forgejo-ci)

This example runs one scan at a time against an explicit repository list. It pins
Docker digests, groups patch updates, and leaves automerge disabled.

- [Set up the bot account](#set-up-the-bot-account)
- [Install](#install)
- [Run a scan](#run-a-scan)
- [Run daily](#run-daily)
- [From update PR to deployment](#from-update-pr-to-deployment)

## Set up the bot account

In Forgejo, create a dedicated Renovate account with a display name and email.
Give it write access to the configuration repositories it should update, then
create a personal access token for that account with these scopes:

| Scope | Use |
|---|---|
| `read:user` | Read the bot's identity |
| `write:repository` | Read repositories and push update branches |
| `write:issue` | Create and update pull requests and comments |
| `read:organization` | Read organization labels and teams |

Write scopes include the corresponding read access. Add `read:package` only if
the bot needs private Forgejo packages, checking the scope name in your Forgejo
version. The [Renovate Forgejo page](https://docs.renovatebot.com/modules/platform/forgejo/)
lists version-specific requirements.

Protect `main` and require the repository's validation checks and review. The bot
needs to push its update branches, but does not need permission to bypass those
rules or any deployment SSH key.

## Install

Requirements: a Docker host that can reach Forgejo and the image registries,
Docker Compose, curl, and an account allowed to run Docker. The timer below also
needs systemd. Keep its configuration outside this public checkout.

On the bot host, create a new working directory and download the examples:

```bash
sudo install -d -m 0750 -o "$(id -un)" -g "$(id -gn)" /srv/renovate
cd /srv/renovate
(
  set -eu
  for file in compose.yml config.js renovate.service renovate.timer; do
    curl --fail --location --output "$file" \
      "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/automation/renovate/$file"
  done
  chmod 644 config.js
)
```

Edit [config.js](config.js):

- Set `endpoint` to your Forgejo base URL, such as `https://git.example.com`.
- Set `gitAuthor` to the bot's display name and email.
- Replace `homelab/apps` with the owner/repository names you want to scan.
- Change `baseBranchPatterns` if those repositories use another default branch.

Keep `config.js` readable by the container's user and put credentials in `.env`.

The example uses the current `forgejo` platform adapter. Older lab configurations
used `gitea`; use the adapter and option names supported by the Renovate version
you run.

Create `.env` from a Bash prompt so the token is not part of a command in shell
history. The `noclobber` option prevents replacing an existing file:

```bash
read -r -s -p 'Forgejo bot token: ' RENOVATE_TOKEN
printf '\n'
(
  set -euC
  umask 077
  printf 'RENOVATE_TOKEN=%s\n' "$RENOVATE_TOKEN" > .env
)
unset RENOVATE_TOKEN
docker compose config --quiet
docker compose pull
```

The [Compose file](compose.yml) runs Renovate as a one-shot container. Its only
host mount is the read-only bot configuration. Compose supplies the token from
`.env`; the container exits after its repository list has been processed.

### What the configuration does

Only `docker-compose` and `dockerfile` managers are enabled. `pinDigests: true`
adds or updates the digest alongside an image tag. A tag such as `latest` remains
`latest@sha256:...`; digest pinning does not turn it into a numbered release tag.
Use versioned tags when you want visible version changes in review.

Patch updates share a PR within each repository. Minor, major, and digest updates
are not included in that patch group. At most two new PRs per hour and five open
PRs per repository keep the queue manageable; the bot must run again to process
changes deferred by those limits.

The policy is in the bot's `config.js`, so onboarding and the dependency dashboard
are disabled. Repositories can add their own `renovate.json` to override policy.
Only give this bot access to repositories whose configuration you trust.

## Run a scan

Validate the bot configuration, then perform a full dry run:

```bash
docker compose run --rm -T --entrypoint renovate-config-validator renovate \
  --strict /usr/src/app/config.js
docker compose run --rm -T renovate --dry-run=full
```

The dry run contacts Forgejo and the registries and reports proposed updates
without creating update branches or PRs. Check the repository names, discovered
Compose files, and proposed image changes. Then run without the dry-run flag:

```bash
docker compose run --rm -T renovate
```

Open Forgejo and check the resulting PRs. A successful bot run does not mean a
new PR is needed: images may already be current, an update branch may already
exist, or PR limits may defer creation.

## Run daily

Edit `User=operator` in [renovate.service](renovate.service) to the account that
owns `/srv/renovate` and can run Docker. Check that `/usr/bin/docker` is correct.
The [timer](renovate.timer) runs at 06:00 in the host's timezone and catches up
after downtime. Change its calendar expression for your schedule.

```bash
sudo install -m 0644 renovate.service renovate.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start renovate.service
sudo systemctl enable --now renovate.timer
systemctl list-timers renovate.timer
journalctl -u renovate.service -n 50 --no-pager
```

The first manual service run checks the same working directory, permissions, and
environment the timer will use. After enabling it, use `systemctl start
renovate.service` for extra scans so systemd serializes them with scheduled runs.

The bot image itself is pinned. Update its tag and digest in `compose.yml`, run
the checks below, and pull the new image before the next scan. Include this bot
configuration in a watched repository if you want Renovate to propose its own
image updates too. Keep `.env` outside that repository.

## From update PR to deployment

For an image update such as Homarr:

1. **Review the PR.** Check the tag and digest, upstream release notes, database
   migrations, and configuration changes. Digest-only updates still change the
   image being run.
2. **Run validation.** Render Compose with synthetic credentials and run the
   service's relevant checks. In this repository, use
   `python3 scripts/check-service-examples.py --validate` and
   `python3 scripts/check-service-examples.py --smoke homarr`. Private Forgejo
   repositories need their own workflow with those checks adapted to their files.
3. **Merge and validate the merge commit.** Record its full SHA. If merging or
   rebasing changed the commit, wait for checks on that resulting commit.
4. **Back up the service.** For Homarr, save appdata, the current Compose file,
   and its encryption key using the [backup steps](../../apps/homarr/README.md#backups-and-restore).
5. **Request deployment of that SHA.** Use the service's manual deployment
   workflow or host runbook to apply the Compose definition from that exact
   checked commit. For Homarr, pull the selected image and recreate the container,
   then check login, board layout, links, and the reading brief.
6. **Record the result.** Keep the deployed SHA, image digest, backup location,
   and check results with your private maintenance notes. If an upgrade fails,
   use the matching previous image and data backup as the application requires.

The [deployment example](../ci/README.md) demonstrates selecting the checked SHA,
a restricted SSH request, image-only changes, health checks, and rollback. It
targets a disposable API service. Adapt its target policy and data handling
before using that pattern for an application such as Homarr.

In my lab, Stirling PDF and the sandbox have manually triggered deployment
workflows. Other services use manual apply steps after merge. The
[runner notes](../README.md#runners-and-deployment) cover that setup, and the
[rollback drill](../../docs/drills/2026-08-24-fail-closed-delivery-rollback.md)
shows the public example's tested behavior.

## Troubleshooting

| Symptom | First thing to check |
|---|---|
| Forgejo returns 401 or 403 | Token scope, expiry, bot repository access, and endpoint |
| No dependency files found | File names supported by the Compose/Dockerfile managers and the selected branch |
| Private registry lookup fails | Registry credentials in Renovate host rules, supplied outside Git |
| Version update is not proposed | Image tag/version scheme, existing PR, repository overrides, and limits |
| Works manually but fails under systemd | Unit user, Docker access, working directory, and `.env` readability |
| Pulling an updated Compose file changes nothing | A pinned digest still selects the old image; review and update the pin first |

## Checks

From the repository root, with Python 3, Docker, and Compose:

```bash
python3 scripts/check-service-examples.py --validate
python3 automation/renovate/check.py
systemd-analyze verify --recursive-errors=no \
  automation/renovate/renovate.service automation/renovate/renovate.timer
```

The check uses the pinned Renovate image to validate `config.js` in strict mode,
then extracts a synthetic Compose dependency with container networking disabled.
It checks the extracted image name and tag and that an npm dependency is ignored.
It needs no Forgejo account. Authentication, PR creation, and branch rules are
checked against your Forgejo instance during setup.

- [Forgejo platform support](https://docs.renovatebot.com/modules/platform/forgejo/)
- [Self-hosted configuration](https://docs.renovatebot.com/self-hosted-configuration/)
- [Docker image versioning](https://docs.renovatebot.com/docker/)
