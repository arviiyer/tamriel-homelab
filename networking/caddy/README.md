# Caddy reverse proxy

[Home](../../README.md) · [Networking](../README.md)

A local example of hostname routing. Caddy forwards `app.example.com` to a tiny
HTTP upstream on an internal Docker network. Only the proxy has a published port.

## Run it

Requirements: Docker Engine, Docker Compose, and curl. From the repository root:

```bash
docker compose -p caddy-example -f networking/caddy/compose.yml up -d
curl --fail --resolve app.example.com:8080:127.0.0.1 http://app.example.com:8080
```

The response is `Example application reached through Caddy`. `--resolve` supplies
the local address while retaining the hostname, so no DNS or hosts-file change
is needed. If your shell has an HTTP proxy configured, add `--noproxy '*'`.

An unconfigured hostname returns 404:

```bash
curl --include -H 'Host: other.example.com' http://127.0.0.1:8080
```

## How it maps to the lab

The [Caddyfile](Caddyfile) demonstrates choosing an upstream by hostname. In the
lab, the proxy runs on the Pi and reaches application VMs across the allowed
network paths. Pi-hole and public DNS provide the appropriate address for local
and Tailscale clients.

This example uses plain HTTP on loopback. A real private application also needs
TLS, the intended client access rules, and either its own login or an Authentik
integration. See [the sign-in table](../README.md#caddy-and-authentik) and
the [private HTTPS walkthrough](../private-access/README.md) to add those pieces.

## Check and stop

Validate routing, unknown-host rejection, and upstream-failure behavior with a
separate temporary project:

```bash
python3 scripts/check-service-examples.py --smoke caddy
```

Stop your interactive example:

```bash
docker compose -p caddy-example -f networking/caddy/compose.yml down
```

[Caddy reverse proxy reference](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
