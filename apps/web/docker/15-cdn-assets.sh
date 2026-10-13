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
# Trailing slash on proxy_pass strips the /cdn-assets/ prefix (same as pathRewrite in proxy.config.json).
cat > "$out" <<CONF
location /cdn-assets/ {
    proxy_pass ${target}/;
    proxy_ssl_server_name on;
    proxy_set_header Host \$proxy_host;
    proxy_http_version 1.1;
    expires 7d;
}
CONF
echo "15-cdn-assets: proxying /cdn-assets/ to the configured icon CDN"
