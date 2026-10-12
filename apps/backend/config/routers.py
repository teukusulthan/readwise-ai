"""Which routers the API mounts (see api.py)."""

# Mounted by default: the book library and the auth it needs.
LIBRARY_ROUTERS = ("health", "auth", "book", "search", "chat", "conversation")
# Boilerplate admin surface (Mongo/Redis/S3 backed). Opt-in only: listed explicitly in
# BE_ENABLED_ROUTERS / --routers. "monitoring" is the /monitoring/threadpool endpoint.
LEGACY_ROUTERS = ("user", "role", "group", "permission", "upload", "monitoring")
# Always mounted, whatever the lists say.
ALWAYS_ON_ROUTERS = ("health",)


def parse_router_list(value):
    return {name.strip() for name in (value or "").split(",") if name.strip()}


def select_routers(enabled_routers="", cli_routers=None):
    """Names of the routers (and "monitoring") to mount.

    An explicit list (BE_ENABLED_ROUTERS, narrowed further by --routers) behaves as it always
    did: exactly what is listed, plus health. With no list the safe default applies:
    the library routers only.
    """
    explicit = parse_router_list(enabled_routers)
    if explicit:
        selected = set(explicit)
    elif cli_routers:
        selected = set(LIBRARY_ROUTERS) | set(LEGACY_ROUTERS)
    else:
        selected = set(LIBRARY_ROUTERS)
    if cli_routers:
        # substring match on the raw argument, as before (it may carry "name[endpoint:endpoint]" parts)
        selected = {name for name in selected if name in cli_routers}
    return selected | set(ALWAYS_ON_ROUTERS)
