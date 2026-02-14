"""Plugin discovery — finds installed plugin packages via Python entry points."""

from __future__ import annotations

import importlib.metadata

import structlog

from webmacs_plugins_core.base import DevicePlugin
from webmacs_plugins_core.config import PluginMeta
from webmacs_plugins_core.errors import PluginLoadError

logger = structlog.get_logger()

ENTRY_POINT_GROUP = "webmacs.plugins"


def discover_plugins() -> dict[str, type[DevicePlugin]]:
    """Scan installed packages for WebMACS plugins.

    Plugins register themselves via ``pyproject.toml``::

        [project.entry-points."webmacs.plugins"]
        my-plugin = "my_package:MyPlugin"

    Returns a dict mapping plugin_id → plugin class.
    """
    found: dict[str, type[DevicePlugin]] = {}
    eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)

    for ep in eps:
        try:
            cls = ep.load()
            _validate_plugin_class(cls, ep.name)
            meta: PluginMeta = cls.meta
            found[meta.id] = cls
            logger.info("plugin_discovered", plugin_id=meta.id, name=meta.name, version=meta.version)
        except Exception as exc:
            logger.error("plugin_load_failed", entry_point=ep.name, error=str(exc))

    logger.info("plugin_discovery_complete", count=len(found))
    return found


def _validate_plugin_class(cls: type, ep_name: str) -> None:
    """Validate that a loaded class is a proper DevicePlugin subclass."""
    if not isinstance(cls, type) or not issubclass(cls, DevicePlugin):
        raise PluginLoadError(ep_name, f"{cls} is not a DevicePlugin subclass")

    if not hasattr(cls, "meta") or not isinstance(cls.meta, PluginMeta):
        raise PluginLoadError(ep_name, f"{cls.__name__} is missing a 'meta: ClassVar[PluginMeta]'")

    if not cls.meta.id:
        raise PluginLoadError(ep_name, f"{cls.__name__}.meta.id must not be empty")

    if not cls.meta.version:
        raise PluginLoadError(ep_name, f"{cls.__name__}.meta.version must not be empty")
