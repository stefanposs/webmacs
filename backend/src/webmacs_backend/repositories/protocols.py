"""Storage Protocols — abstract interface for database backends.

These protocols define the contracts that any persistence layer must fulfill.
Not decorated with @runtime_checkable — we rely on mypy for static verification.
"""

from __future__ import annotations

import datetime
from typing import Protocol, Sequence


class DatapointRecord:
    """Minimal data-transfer object for a datapoint row."""

    __slots__ = ("public_id", "value", "timestamp", "event_public_id", "experiment_public_id")

    def __init__(
        self,
        public_id: str,
        value: float,
        timestamp: datetime.datetime | None,
        event_public_id: str,
        experiment_public_id: str | None,
    ) -> None:
        self.public_id = public_id
        self.value = value
        self.timestamp = timestamp
        self.event_public_id = event_public_id
        self.experiment_public_id = experiment_public_id


class ExperimentRecord:
    """Minimal data-transfer object for an experiment row."""

    __slots__ = ("public_id", "name", "started_on", "stopped_on", "user_public_id")

    def __init__(
        self,
        public_id: str,
        name: str,
        started_on: datetime.datetime | None,
        stopped_on: datetime.datetime | None,
        user_public_id: str,
    ) -> None:
        self.public_id = public_id
        self.name = name
        self.started_on = started_on
        self.stopped_on = stopped_on
        self.user_public_id = user_public_id


class DatapointRepository(Protocol):
    """Protocol for datapoint storage operations."""

    async def create(
        self,
        public_id: str,
        value: float,
        timestamp: datetime.datetime,
        event_public_id: str,
        experiment_public_id: str | None,
    ) -> None: ...

    async def create_batch(
        self,
        rows: list[dict],
    ) -> int: ...

    async def get_latest_per_event(self) -> Sequence[DatapointRecord]: ...

    async def list_paginated(
        self, page: int, page_size: int,
    ) -> tuple[int, Sequence[DatapointRecord]]: ...

    async def get_by_public_id(self, public_id: str) -> DatapointRecord | None: ...

    async def delete_by_public_id(self, public_id: str) -> bool: ...

    async def get_by_experiment(
        self, experiment_public_id: str,
    ) -> Sequence[DatapointRecord]: ...


class ExperimentRepository(Protocol):
    """Protocol for experiment storage operations."""

    async def create(
        self, public_id: str, name: str, user_public_id: str,
    ) -> None: ...

    async def get_by_public_id(self, public_id: str) -> ExperimentRecord | None: ...

    async def list_paginated(
        self, page: int, page_size: int,
    ) -> tuple[int, Sequence[ExperimentRecord]]: ...

    async def update(self, public_id: str, **fields: object) -> bool: ...

    async def stop(self, public_id: str, stopped_on: datetime.datetime) -> bool: ...

    async def delete_by_public_id(self, public_id: str) -> bool: ...

    async def get_active_experiment_id(self) -> str | None: ...
