#!/bin/sh
# Writes the /cdn-assets/ location nginx includes. The CDN host is operator-supplied
# (ICON_CDN_PROXY_TARGET) and never stored in git; without it the location answers 404.
set -eu

out=/tmp/cdn-assets.conf
target="${ICON_CDN_PROXY_TARGET:-}"

if [ -z "$target" ]; then
  echo "15-cdn-assets: ICON_CDN_PROXY_TARGET is empty; /cdn-assets/ will answer 404 (icons will not load)"
  printf 'location /cdn-assets/ { return 404; }\n' > "$out"
  exit 0
fi

case "$target" in
  http://* | https://*) ;;
  *) echo "15-cdn-assets: ICON_CDN_PROXY_TARGET must start with http:// or https://" >&2; exit 1 ;;
esac
# The value is written into an nginx directive: refuse anything that could end it or open a block.
case "$target" in
  *[!A-Za-z0-9:/._~%@-]*) echo "15-cdn-assets: ICON_CDN_PROXY_TARGET contains unsupported characters" >&2; exit 1 ;;
esac

target="${target%/}"
# Split "https://host[:port][/path]" into the origin (proxied to) and an optional path prefix.
rest="${target#*://}"
origin="${target%%://*}://${rest%%/*}"
prefix=""
case "$rest" in
  */*) prefix="/${rest#*/}" ;;
esac

# Resolve the CDN at request time, not at startup: with a literal host in proxy_pass nginx refuses to
# start (and the container crash-loops) whenever the name does not resolve at boot. 127.0.0.11 is
# Docker's embedded DNS on compose/user-defined networks; override with ICON_CDN_RESOLVER elsewhere.
resolver="${ICON_CDN_RESOLVER:-127.0.0.11}"
case "$resolver" in
  "" | *[!A-Za-z0-9:.\[\]-]*) echo "15-cdn-assets: ICON_CDN_RESOLVER contains unsupported characters" >&2; exit 1 ;;
esac

# A variable in proxy_pass forwards the URI as is, so the /cdn-assets/ prefix is stripped by the rewrite
# (same as pathRewrite in proxy.config.json); query strings are kept.
cat > "$out" <<CONF
location /cdn-assets/ {
    resolver ${resolver} valid=30s;
    resolver_timeout 5s;
    set \$cdn_origin "${origin}";
    rewrite ^/cdn-assets/(.*)\$ ${prefix}/\$1 break;
    proxy_pass \$cdn_origin;
    proxy_ssl_server_name on;
    proxy_set_header Host \$proxy_host;
    proxy_http_version 1.1;
    expires 7d;
}
CONF
echo "15-cdn-assets: proxying /cdn-assets/ to the configured icon CDN (resolved at request time via ${resolver})"
