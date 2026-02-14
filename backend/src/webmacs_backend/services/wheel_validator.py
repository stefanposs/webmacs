"""Wheel validation — inspects ``.whl`` files before installation.

Checks:
1. Is the file a valid ZIP archive?
2. Does it contain a ``METADATA`` file?
3. Does the METADATA declare an entry-point in the ``webmacs.plugins`` group?
"""

from __future__ import annotations

import email.parser
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class WheelInfo:
    """Metadata extracted from a ``.whl`` file."""

    name: str
    version: str
    has_plugin_entry_point: bool


class InvalidWheelError(Exception):
    """Raised when a ``.whl`` file is structurally invalid."""


def validate_wheel(path: Path) -> WheelInfo:
    """Validate a ``.whl`` file and extract metadata.

    Raises ``InvalidWheelError`` if the file is not a valid wheel or
    does not declare a ``webmacs.plugins`` entry point.
    """
    if not path.name.endswith(".whl"):
        raise InvalidWheelError(
            f"File must have a .whl extension, got: {path.name}",
        )

    try:
        zf = zipfile.ZipFile(path, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise InvalidWheelError(
            f"Not a valid ZIP/wheel archive: {exc}",
        ) from exc

    with zf:
        # Find the *.dist-info/METADATA file
        metadata_path = _find_metadata(zf)
        if metadata_path is None:
            raise InvalidWheelError(
                "No .dist-info/METADATA found in wheel.",
            )

        raw = zf.read(metadata_path).decode("utf-8", errors="replace")
        parser = email.parser.Parser()
        meta = parser.parsestr(raw)
        name = meta.get("Name", "unknown")
        version = meta.get("Version", "0.0.0")

        # Check for webmacs.plugins entry point in entry_points.txt
        ep_path = metadata_path.replace("METADATA", "entry_points.txt")
        has_ep = False
        if ep_path in zf.namelist():
            ep_text = zf.read(ep_path).decode("utf-8", errors="replace")
            has_ep = "[webmacs.plugins]" in ep_text

        if not has_ep:
            raise InvalidWheelError(
                f"Wheel '{name}' does not declare a "
                f"[webmacs.plugins] entry point. "
                f"It is not a valid WebMACS plugin package.",
            )

        return WheelInfo(
            name=name,
            version=version,
            has_plugin_entry_point=True,
        )


def _find_metadata(zf: zipfile.ZipFile) -> str | None:
    """Find the first ``*.dist-info/METADATA`` file in a wheel."""
    for name in zf.namelist():
        if name.endswith(".dist-info/METADATA"):
            return name
    return None
