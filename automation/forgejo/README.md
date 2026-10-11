# Forgejo

[Home](../../README.md) · [Automation](../README.md) · [Renovate](../renovate/README.md)

Forgejo hosts my private configuration repositories, pull requests, and Actions
workflows. It runs on the application VM with PostgreSQL and repository files
on local storage. Caddy and an SSH relay on the Pi provide access under one
hostname; Authentik handles browser sign-in. Actions runners have their own VM.

![Compose validation in Forgejo](../../screenshots/forgejo-validation-run.png)

Compose checks passing on an image-update pull request.

## The setup

```text
Browser / HTTPS Git → Pi Caddy :443 → apps-01 :3000 → Forgejo
SSH Git            → Pi socat :2222 → apps-01 :2222 → Forgejo
                                                     ├─ PostgreSQL
                                                     └─ Local repositories and attachments
Browser sign-in    → Authentik → Forgejo OIDC callback
```

The example uses Forgejo 15 LTS and PostgreSQL 18, with pinned images. Replace
`192.0.2.83` with your application VM's address and `git.example.com` with your
hostname. The [private-access guide](../../networking/private-access/README.md)
covers Caddy, DNS, certificates, Tailscale, and backend firewall rules.

## Install

Requirements: a [Debian Docker VM](../../proxmox/debian-vm/README.md), Docker
Compose, Bash, curl, OpenSSL, and local disk space for repositories and packages.
Use Git and an SSH client on your workstation. On **apps-01**:

```bash
mkdir -p "$HOME/homelab/forgejo"
cd "$HOME/homelab/forgejo"
(
  set -eu
  for file in compose.yml environment.example; do
    curl -fLo "$file" \
      "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/automation/forgejo/$file"
  done
)
(
  set -euC
  umask 077
  sed -e "s/^POSTGRES_PASSWORD=$/POSTGRES_PASSWORD=$(openssl rand -hex 24)/" \
      -e "s/^SECRET_KEY=$/SECRET_KEY=$(openssl rand -hex 32)/" \
      environment.example > .env
)
mkdir -m 755 data db
```

Edit `DOMAIN`, `ROOT_URL` (including its trailing slash), `FORGEJO_BIND_IP`, and
`TZ` in `.env`. Keep the generated secrets for subsequent starts and restores.
The image prepares `data/` for its UID/GID 1000 application user. PostgreSQL
manages ownership of `db/`.

| Host path | Contents |
|---|---|
| `data/` | Repositories, attachments, packages, SSH host keys, and `gitea/conf/app.ini` |
| `db/` | PostgreSQL files, mounted at `/var/lib/postgresql` for PostgreSQL 18 |
| `.env` | Database password, Forgejo secret key, and installation settings |

Both data directories belong on the VM's local disk. My lab uses
`/srv/forgejo/data` and `/srv/forgejo/db`; the relative paths here keep the
installation together in its service directory. PostgreSQL has no published
host port.

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
curl --fail http://192.0.2.83:3000/api/healthz
```

Once startup finishes, create the first administrator:

```bash
docker compose exec --user git forgejo forgejo \
  --config /data/gitea/conf/app.ini admin user create \
  --username operator --email operator@example.com --admin \
  --random-password --random-password-length 32
```

Use your own email address. Save the generated password and change it at first
login. `INSTALL_LOCK` skips the web installer, and open registration is disabled.
Mail delivery is disabled until you configure SMTP.

## HTTPS access

In Pi-hole, point `git.example.com` at the Pi's LAN address. Its DNS-only public
record points at the Pi's Tailscale address, following the private-access guide.
Allow the Pi to reach TCP 3000 on the application VM. Add this block to the Pi's
Caddyfile, alongside that guide's `private_site` and `private_clients` snippets:

```caddyfile
git.example.com {
	import private_site
	route {
		import private_clients
		reverse_proxy 192.0.2.83:3000
	}
}
```

Reload Caddy, open `https://git.example.com`, and sign in with the administrator.
Forgejo handles authentication itself. An extra forward-auth redirect would
interfere with Git clients and the API.

## Authentik sign-in

In Authentik, create an **OAuth2/OpenID Connect** application/provider pair:

| Setting | Value |
|---|---|
| Application slug | `forgejo` |
| Client type | Confidential |
| Grant types | Authorization Code |
| Authorization flow | Your provider consent flow |
| Redirect URI | Strict authorization URI: `https://git.example.com/user/oauth2/authentik/callback` |
| Scopes | `openid`, `email`, `profile` |
| Signing key | An available signing key |

Bind the application to your intended users or group. In Forgejo's **Site
Administration → Authentication Sources → Add Authentication Source**, choose
**OAuth2**, then **OpenID Connect**:

| Setting | Value |
|---|---|
| Authentication name | `authentik` |
| Client ID and secret | From the Authentik provider |
| Auto discovery URL | `https://auth.example.com/application/o/forgejo/.well-known/openid-configuration` |
| Additional scopes | `email profile` |

The authentication name forms part of the callback path. Forgejo's container
must resolve and reach the Authentik HTTPS URL. Allow the application VM through
Caddy's source restriction for this connection, and keep TLS verification on.

To create Forgejo accounts on the first successful Authentik login, set
`OIDC_AUTO_REGISTRATION=true` in `.env` and run `docker compose up -d forgejo`.
Local self-registration stays disabled. Existing accounts use Forgejo's default
account-linking login; normal new accounts do not receive administrator rights.

In a private browser window, choose **Sign in with authentik**. Check an allowed
user, then a user outside the application binding. Manage repository and
organization membership in Forgejo. See the
[Authentik integration reference](https://integrations.goauthentik.io/development/forgejo/)
for optional group-to-permission mappings.

## SSH Git through the Pi

The Git hostname resolves to the Pi, so SSH needs its own TCP relay. Caddy's HTTP
proxy does not carry SSH. On the Pi, install `socat` and save this as
`/etc/systemd/system/git-ssh-proxy.service`, using your application's address:

```ini
[Unit]
Description=Forward Git SSH to the application VM
After=network.target

[Service]
DynamicUser=yes
ExecStart=/usr/bin/socat TCP-LISTEN:2222,fork,reuseaddr TCP:192.0.2.83:2222
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo apt install socat
sudo systemctl daemon-reload
sudo systemctl enable --now git-ssh-proxy.service
```

Permit trusted LAN and tailnet clients to the Pi on TCP 2222, and the Pi to
the application VM on TCP 2222. Apply this in the tailnet policy and host/router
firewalls; Caddy's client restriction covers only HTTP. Keep WAN forwarding off.

Add your SSH public key under Forgejo **Settings → SSH / GPG Keys**. To check the
server's fingerprint, run on the application VM:

```bash
docker compose exec --user git forgejo sh -c \
  'for key in /data/gitea/ssh/*.pub; do ssh-keygen -lf "$key"; done'
```

Compare it with the first connection prompt from your workstation:

```bash
ssh -T -p 2222 git@git.example.com
```

Expect a successful-authentication greeting without shell access. Create a
private repository named `notes`, initialize it with a README, and try:

```bash
git clone ssh://git@git.example.com:2222/operator/notes.git
cd notes
printf '\nFirst lab note.\n' >> README.md
git add README.md
git commit -m "Add a lab note"
git push
```

Use your Forgejo username in the clone URL. For HTTPS Git, use a scoped Forgejo
access token in your credential manager; browser OIDC sessions do not authenticate
Git commands. The [Renovate guide](../renovate/README.md) covers its bot account,
and the [runner notes](../README.md#runners-and-deployment) explain Actions.

## Backups and restore

PBS backs up my application VM's local disks. Before an upgrade, a stopped-stack
archive is also a simple way to keep the database and repository files together.
This causes downtime. From the Forgejo service directory:

```bash
(
  set -eu
  umask 077
  mkdir -p "$HOME/backups"
  backup="$HOME/backups/forgejo-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
  docker compose stop forgejo
  docker compose stop db
  sudo tar --numeric-owner -czf - compose.yml .env data db > "$backup"
  docker compose up -d
  printf 'Backup: %s\n' "$backup"
)
```

If archiving fails, investigate before restarting with `docker compose up -d`.
Keep the archive private: it includes credentials, host keys, and application
data. Copy completed archives off-host using [Restic](../../storage/restic/README.md).
Retain the original `SECRET_KEY`, which decrypts stored application secrets.

To test a restore, copy an archive to an isolated Docker VM with no access to
production services, runners, or webhook destinations. Extract into a new directory:

```bash
read -r -p 'Absolute backup archive path: ' BACKUP
mkdir "$HOME/forgejo-restore"
cd "$HOME/forgejo-restore"
sudo tar --numeric-owner -xzf "$BACKUP"
sudo chown "$(id -u):$(id -g)" compose.yml .env
```

In the restored `.env`, set `FORGEJO_BIND_IP=127.0.0.1`, `DOMAIN=localhost`, and
`ROOT_URL=http://localhost:3000/`. Keep the restored passwords and keys. Start
with the archived image versions using `docker compose -p forgejo-restore up -d`.
From your workstation, tunnel ports 3000 and 2222 to the restore VM:

```bash
ssh -N -L 3000:127.0.0.1:3000 -L 2222:127.0.0.1:2222 operator@test-01
```

Open `http://localhost:3000`, sign in with the administrator created during setup,
and check an older issue, attachment, and repository. Clone using
`ssh://git@localhost:2222/operator/notes.git` and compare a known commit. Test OIDC
separately with a test provider and its own HTTPS callback. Stop the restored
stack with `docker compose -p forgejo-restore down` when finished.

## Updates and notes

- Back up first, read the [upgrade notes](https://forgejo.org/docs/v15.0/admin/upgrade/),
  then update the image tag and digest, pull, and recreate Forgejo. Check sign-in,
  clone/push, and an Actions job afterward.
- Database migrations can prevent an image-only downgrade. Restore the matching
  database, files, configuration, and old images together when required.
- PostgreSQL major upgrades need a database migration. Changing `18` to a new
  major version against the existing directory is not an upgrade procedure.
- A failed SSH connection usually means the relay, port rule, or uploaded public
  key needs checking. A failed OIDC callback usually means the source name,
  callback URL, discovery reachability, or provider binding differs.

[Forgejo Docker installation](https://forgejo.org/docs/v15.0/admin/installation/docker/) ·
[Configuration reference](https://forgejo.org/docs/v15.0/admin/config-cheat-sheet/)
