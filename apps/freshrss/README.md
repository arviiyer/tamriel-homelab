# FreshRSS

[Home](../../README.md) · [Apps](../README.md) · [Networking](../../networking/README.md)

FreshRSS is my browser-based feed reader. It holds security news and technical
articles and supplies the input for the [Morning SOC Briefing](../projects/README.md#morning-soc-briefing).

## The setup

FreshRSS runs in Docker on the application VM. SQLite and configuration stay on
local storage. Caddy supplies the HTTPS route, and Authentik provides sign-in
through the image's `mod_auth_openidc` integration.

Local DNS points the hostname at the proxy's LAN address. Remote access uses
Tailscale. Both paths retain the same HTTPS hostname and OIDC callback.

## Sign-in

The integration uses a confidential OAuth2/OIDC provider with `openid`, `email`,
and `profile` scopes. FreshRSS uses the authenticated username supplied by the web
server. The initial FreshRSS username must match the selected identity claim.

Register exact callback URLs. In this setup, both the ordinary callback and its
explicit `:443` form were needed. For a documentation hostname, those would be
`https://rss.example.com/i/oidc/` and `https://rss.example.com:443/i/oidc/`.

After configuration, check logout and a fresh login through Caddy, then verify
that anonymous requests cannot read articles or cached images. Homarr links to
the reader, but keeps its own local login.

## Article text and images

Some feeds only provide summaries. I enable FreshRSS's full-content extraction
for selected feeds instead of applying it to every subscription. Selectors need
to match the publisher's page structure and occasionally need updating.

The custom Local Media Cache extension downloads article images during ingestion
and serves them behind the reader's authentication. Its cache has a size limit.
It uses FreshRSS's protected fetch path so private destinations and unsafe
redirects stay blocked.

## Backups

Keep the SQLite database, application configuration, and custom extensions. Use
a consistent SQLite backup or stop the application while copying its database.
The article-image cache is disposable and separate from the reader's saved data.
Record the Authentik provider settings and keep its credentials outside Git.

## Notes

- [FreshRSS documentation](https://freshrss.github.io/FreshRSS/)
- [Official container setup](https://github.com/FreshRSS/FreshRSS/tree/edge/Docker)
- [Authentik integration](https://integrations.goauthentik.io/media/freshrss/)
- [Try a local reverse proxy](../../networking/caddy/README.md)
