"""SQLAlchemy implementation of the repository protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import desc, func, insert, select

from webmacs_backend.models import Datapoint, Experiment
from webmacs_backend.repositories.protocols import DatapointRecord, ExperimentRecord

if TYPE_CHECKING:
    import datetime
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyDatapointRepository:
    """PostgreSQL/SQLAlchemy datapoint storage."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def create(
        self,
        public_id: str,
        value: float,
        timestamp: datetime.datetime,
        event_public_id: str,
        experiment_public_id: str | None,
    ) -> None:
        self._db.add(
            Datapoint(
                public_id=public_id,
                value=value,
                timestamp=timestamp,
                event_public_id=event_public_id,
                experiment_public_id=experiment_public_id,
            )
        )

    async def create_batch(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        await self._db.execute(insert(Datapoint), rows)
        return len(rows)

    async def get_latest_per_event(self) -> Sequence[DatapointRecord]:
        subq = (
            select(Datapoint.event_public_id, func.max(Datapoint.timestamp).label("max_ts"))
            .group_by(Datapoint.event_public_id)
            .subquery()
        )
        result = await self._db.execute(
            select(Datapoint).join(
                subq,
                (Datapoint.event_public_id == subq.c.event_public_id) & (Datapoint.timestamp == subq.c.max_ts),
            )
        )
        return [self._to_record(dp) for dp in result.scalars().all()]

    async def list_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple[int, Sequence[DatapointRecord]]:
        total = (await self._db.execute(select(func.count(Datapoint.id)))).scalar_one()
        result = await self._db.execute(
            select(Datapoint).order_by(desc(Datapoint.timestamp)).offset((page - 1) * page_size).limit(page_size)
        )
        rows = [self._to_record(dp) for dp in result.scalars().all()]
        return total, rows

    async def get_by_public_id(self, public_id: str) -> DatapointRecord | None:
        result = await self._db.execute(select(Datapoint).where(Datapoint.public_id == public_id))
        dp = result.scalar_one_or_none()
        return self._to_record(dp) if dp else None

    async def delete_by_public_id(self, public_id: str) -> bool:
        result = await self._db.execute(select(Datapoint).where(Datapoint.public_id == public_id))
        dp = result.scalar_one_or_none()
        if not dp:
            return False
        await self._db.delete(dp)
        return True

    async def get_by_experiment(
        self,
        experiment_public_id: str,
    ) -> Sequence[DatapointRecord]:
        result = await self._db.execute(
            select(Datapoint)
            .where(Datapoint.experiment_public_id == experiment_public_id)
            .order_by(Datapoint.timestamp)
        )
        return [self._to_record(dp) for dp in result.scalars().all()]

    @staticmethod
    def _to_record(dp: Datapoint) -> DatapointRecord:
        return DatapointRecord(
            public_id=dp.public_id,
            value=dp.value,
            timestamp=dp.timestamp,
            event_public_id=dp.event_public_id,
            experiment_public_id=dp.experiment_public_id,
        )


class SQLAlchemyExperimentRepository:
    """PostgreSQL/SQLAlchemy experiment storage."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def create(
        self,
        public_id: str,
        name: str,
        user_public_id: str,
    ) -> None:
        self._db.add(
            Experiment(
                public_id=public_id,
                name=name,
                user_public_id=user_public_id,
            )
        )

    async def get_by_public_id(self, public_id: str) -> ExperimentRecord | None:
        result = await self._db.execute(select(Experiment).where(Experiment.public_id == public_id))
        exp = result.scalar_one_or_none()
        return self._to_record(exp) if exp else None

    async def list_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple[int, Sequence[ExperimentRecord]]:
        total = (await self._db.execute(select(func.count(Experiment.id)))).scalar_one()
        result = await self._db.execute(select(Experiment).offset((page - 1) * page_size).limit(page_size))
        rows = [self._to_record(e) for e in result.scalars().all()]
        return total, rows

    async def update(self, public_id: str, **fields: object) -> bool:
        result = await self._db.execute(select(Experiment).where(Experiment.public_id == public_id))
        exp = result.scalar_one_or_none()
        if not exp:
            return False
        for key, value in fields.items():
            setattr(exp, key, value)
        return True

    async def stop(self, public_id: str, stopped_on: datetime.datetime) -> bool:
        return await self.update(public_id, stopped_on=stopped_on)

    async def delete_by_public_id(self, public_id: str) -> bool:
        result = await self._db.execute(select(Experiment).where(Experiment.public_id == public_id))
        exp = result.scalar_one_or_none()
        if not exp:
            return False
        await self._db.delete(exp)
        return True

    async def get_active_experiment_id(self) -> str | None:
        result = await self._db.execute(select(Experiment.public_id).where(Experiment.stopped_on.is_(None)))
        row = result.first()
        return row[0] if row else None

    @staticmethod
    def _to_record(exp: Experiment) -> ExperimentRecord:
        return ExperimentRecord(
            public_id=exp.public_id,
            name=exp.name,
            started_on=exp.started_on,
            stopped_on=exp.stopped_on,
            user_public_id=exp.user_public_id,
        )
