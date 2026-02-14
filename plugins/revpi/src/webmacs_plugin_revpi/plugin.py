"""Revolution Pi plugin — reads and writes IOs from the piCtory process image.

Uses *revpimodio2* to access all configured devices and their inputs/outputs.
Channels are **dynamically discovered** from the active piCtory configuration
at ``/var/www/pictory/projects/_config.rsc``.  When piCtory is unavailable
(development machine, demo mode) a set of fallback DIO channels is provided.

Dependencies
~~~~~~~~~~~~
* ``revpimodio2>=2.8.0`` — install with ``pip install webmacs-plugin-revpi[hardware]``
  or ``pip install revpimodio2``.  The package is only needed at *runtime*
  on the actual Revolution Pi; the plugin class can be imported and its metadata
  inspected without it.

The plugin uses ``SyncDevicePlugin`` because *revpimodio2* is a blocking
library.  All I/O calls are wrapped by ``asyncio.to_thread()`` automatically.
The ``autorefresh`` flag is **disabled** — we do explicit ``readprocimg()`` /
``writeprocimg()`` in each read/write cycle for deterministic timing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import structlog
from pydantic import Field

from webmacs_plugins_core.base import SyncDevicePlugin
from webmacs_plugins_core.channels import (
    ChannelDescriptor,
    ChannelDirection,
    SimulationSpec,
)
from webmacs_plugins_core.config import PluginInstanceConfig, PluginMeta

if TYPE_CHECKING:
    from webmacs_plugins_core.types import ChannelValue

logger = structlog.get_logger()

# Default piCtory config path on the Revolution Pi
_PICTORY_CONFIG_PATH = Path("/var/www/pictory/projects/_config.rsc")


# ── Custom config ────────────────────────────────────────────────────────


class RevPiConfig(PluginInstanceConfig):
    """Extended configuration for the Revolution Pi plugin."""

    device_filter: list[str] = Field(default_factory=list)
    """Optional list of piCtory device bookmarks ("bmk") to include.

    If empty, **all** non-base devices (DIO, AIO, MIO, …) are included.
    Example: ``["DIO_Module_1", "AIO_Module_2"]``.
    """

    configrsc: str = ""
    """Override path to the piCtory ``_config.rsc`` file.

    Leave empty to use the default path.
    """


# ── Plugin ───────────────────────────────────────────────────────────────


class RevPiPlugin(SyncDevicePlugin):
    """Revolution Pi hardware I/O via the piCtory process image.

    *   **Input channels** → correspond to piCtory *inputs* (e.g. digital
        inputs on a DIO module, analog inputs on an AIO module).
    *   **Output channels** → correspond to piCtory *outputs* (e.g. digital
        outputs, relay outputs).

    The plugin uses ``revpimodio2.RevPiModIO`` with ``autorefresh=False``
    and explicit ``readprocimg()`` / ``writeprocimg()`` calls per cycle.
    In demo mode, fallback DIO-style channels are generated.
    """

    meta: ClassVar[PluginMeta] = PluginMeta(
        id="revpi",
        name="Revolution Pi",
        version="0.1.0",
        vendor="KUNBUS GmbH",
        description=(
            "Direct hardware I/O access via the piCtory process image. "
            "Auto-discovers all configured modules and their "
            "inputs/outputs."
        ),
        protocol="piControl",
        url="https://revolutionpi.com/",
        tags=["hardware", "revpi", "kunbus", "dio", "aio"],
    )

    config_schema: ClassVar[type[PluginInstanceConfig]] = RevPiConfig

    def __init__(self) -> None:
        super().__init__()
        self._rpi: Any = None  # revpimodio2.RevPiModIO at runtime
        self._discovered_channels: list[ChannelDescriptor] = []
        self._io_names: dict[str, str] = {}  # channel_id → IO name

    # ── Configuration override ───────────────────────────────────────

    def configure(self, config: dict[str, object]) -> None:
        """Pre-scan piCtory before the base class calls get_channels."""
        device_filter = config.get("device_filter", [])
        configrsc = str(config.get("configrsc", ""))
        self._pre_scan(device_filter, configrsc)
        super().configure(config)

    def _pre_scan(
        self,
        device_filter: list[str] | object,
        configrsc: str,
    ) -> None:
        """Try to read piCtory config and extract IO definitions."""
        # 1. Try revpimodio2 first (most accurate)
        try:
            self._scan_with_revpimodio(device_filter, configrsc)
            return
        except Exception as exc:
            logger.debug(
                "revpimodio2_scan_skipped",
                reason=str(exc),
            )

        # 2. Fall back to raw JSON parsing of _config.rsc
        try:
            self._scan_from_json(device_filter, configrsc)
            return
        except Exception as exc:
            logger.debug(
                "pictory_json_scan_skipped",
                reason=str(exc),
            )

        # 3. No piCtory available — will use fallback channels
        self._discovered_channels = []

    # ── piCtory scanning ─────────────────────────────────────────────

    def _scan_with_revpimodio(
        self,
        device_filter: list[str] | object,
        configrsc: str,
    ) -> None:
        """Discover channels via a temporary revpimodio2 instance."""
        import revpimodio2  # type: ignore[import-untyped]

        kwargs: dict[str, Any] = {
            "autorefresh": False,
            "monitoring": True,
        }
        if configrsc:
            kwargs["configrsc"] = configrsc

        rpi = revpimodio2.RevPiModIO(**kwargs)
        try:
            jconfig = rpi.get_jconfigrsc()
            self._parse_jconfig(jconfig, device_filter)
        finally:
            rpi.exit()

    def _scan_from_json(
        self,
        device_filter: list[str] | object,
        configrsc: str,
    ) -> None:
        """Fall back to direct JSON parsing of piCtory config."""
        path = Path(configrsc) if configrsc else _PICTORY_CONFIG_PATH
        raw = path.read_text(encoding="utf-8")
        jconfig = json.loads(raw)
        self._parse_jconfig(jconfig, device_filter)

    def _parse_jconfig(
        self,
        jconfig: dict[str, Any],
        device_filter: list[str] | object,
    ) -> None:
        """Walk the piCtory JSON and build channel descriptors."""
        channels: list[ChannelDescriptor] = []
        io_names: dict[str, str] = {}
        allowed = set(device_filter) if isinstance(device_filter, list) else set()

        for dev in jconfig.get("Devices", []):
            dev_type = dev.get("type", "")
            bmk = dev.get("bmk", dev.get("id", "device"))

            # Skip base module unless explicitly requested
            if dev_type == "BASE" and not (allowed and bmk in allowed):
                continue
            if allowed and bmk not in allowed:
                continue

            # -- Inputs --
            for io_info in (dev.get("inp") or {}).values():
                name = io_info.get("name", "")
                if not name:
                    continue
                ch_id = f"{bmk}__{name}"
                io_names[ch_id] = name
                channels.append(
                    ChannelDescriptor(
                        id=ch_id,
                        name=f"{bmk} / {name}",
                        direction=ChannelDirection.input,
                        unit=self._unit_for_type(io_info),
                        min_value=0.0,
                        max_value=self._max_for_bit_length(
                            io_info,
                        ),
                    ),
                )

            # -- Outputs --
            for io_info in (dev.get("out") or {}).values():
                name = io_info.get("name", "")
                if not name:
                    continue
                ch_id = f"{bmk}__{name}"
                io_names[ch_id] = name
                channels.append(
                    ChannelDescriptor(
                        id=ch_id,
                        name=f"{bmk} / {name}",
                        direction=ChannelDirection.output,
                        unit=self._unit_for_type(io_info),
                        min_value=0.0,
                        max_value=self._max_for_bit_length(
                            io_info,
                        ),
                        safe_value=0.0,
                    ),
                )

        self._discovered_channels = channels
        self._io_names = io_names
        logger.info(
            "pictory_channels_discovered",
            count=len(channels),
            devices=[d.get("bmk", "?") for d in jconfig.get("Devices", [])],
        )

    # ── Channel helpers ──────────────────────────────────────────────

    @staticmethod
    def _max_for_bit_length(io_info: dict[str, Any]) -> float:
        """Derive max value from the piCtory ``bitLength`` field."""
        try:
            bits = int(io_info.get("bitLength", 1))
        except (TypeError, ValueError):
            bits = 1
        if bits <= 1:
            return 1.0
        return float(2 ** min(bits, 32) - 1)

    @staticmethod
    def _unit_for_type(io_info: dict[str, Any]) -> str:
        """Infer a unit from IO metadata (best effort)."""
        comment = str(io_info.get("comment", "")).lower()
        if "temp" in comment:
            return "°C"
        if "volt" in comment:
            return "V"
        if "current" in comment or "ampere" in comment:
            return "mA"
        return ""

    # ── get_channels ─────────────────────────────────────────────────

    def get_channels(self) -> list[ChannelDescriptor]:
        """Return piCtory channels or fallback defaults for demo."""
        if self._discovered_channels:
            return self._discovered_channels
        return self._fallback_channels()

    @staticmethod
    def _fallback_channels() -> list[ChannelDescriptor]:
        """Default DIO-style channels for demo / dev environments."""
        channels: list[ChannelDescriptor] = [
            ChannelDescriptor(
                id=f"Input_{i}",
                name=f"Digital Input {i}",
                direction=ChannelDirection.input,
                unit="",
                min_value=0.0,
                max_value=1.0,
                simulation=SimulationSpec(
                    profile="step",
                    base_value=0.5,
                    amplitude=0.5,
                    period_seconds=5.0 + i * 2,
                ),
            )
            for i in range(1, 15)
        ]
        channels.extend(
            ChannelDescriptor(
                id=f"Output_{i}",
                name=f"Digital Output {i}",
                direction=ChannelDirection.output,
                unit="",
                min_value=0.0,
                max_value=1.0,
                safe_value=0.0,
            )
            for i in range(1, 15)
        )
        return channels

    # ── SyncDevicePlugin interface ───────────────────────────────────

    def connect_sync(self) -> None:
        """Create the RevPiModIO instance (autorefresh=False)."""
        import revpimodio2  # type: ignore[import-untyped]

        kwargs: dict[str, Any] = {"autorefresh": False}
        if isinstance(self._config, RevPiConfig) and self._config.configrsc:
            kwargs["configrsc"] = self._config.configrsc

        self._rpi = revpimodio2.RevPiModIO(**kwargs)
        self._log.info("revpi_connected")

    def disconnect_sync(self) -> None:
        """Shut down the process-image handle."""
        if self._rpi is not None:
            self._rpi.exit()
            self._rpi = None

    def read_sync(self, channel_id: str) -> ChannelValue | None:
        """Read a single IO from the process image."""
        if self._rpi is None:
            return None
        # Refresh the process image before reading
        self._rpi.readprocimg()
        io_name = self._io_names.get(channel_id, channel_id)
        try:
            return getattr(self._rpi.io, io_name).value
        except AttributeError:
            self._log.warning("io_not_found", io_name=io_name)
            return None

    def write_sync(
        self,
        channel_id: str,
        value: ChannelValue,
    ) -> None:
        """Write a single IO to the process image."""
        if self._rpi is None:
            return
        io_name = self._io_names.get(channel_id, channel_id)
        try:
            getattr(self._rpi.io, io_name).value = value
            # Flush the process image after writing
            self._rpi.writeprocimg()
        except AttributeError:
            self._log.warning("io_not_found", io_name=io_name)
