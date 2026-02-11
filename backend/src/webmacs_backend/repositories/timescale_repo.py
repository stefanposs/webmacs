"""TimescaleDB repository stub — placeholder for future hypertable-based storage.

from __future__ import annotations
TimescaleDB extends PostgreSQL with automatic time-series partitioning (hypertables),
continuous aggregates, and compression policies. This stub uses the same SQLAlchemy
backend but is the designated extension point for:

  - CREATE TABLE ... WITH (timescaledb.hypertable) DDL at migration time
  - Continuous aggregate materialized views for fast historical queries
  - Compression policies for long-term retention

To activate: set STORAGE_BACKEND=timescale in environment variables.
"""

from __future__ import annotations

from webmacs_backend.repositories.sqlalchemy_repo import (
    SQLAlchemyDatapointRepository,
    SQLAlchemyExperimentRepository,
)


class TimescaleDatapointRepository(SQLAlchemyDatapointRepository):
    """TimescaleDB-aware datapoint repository.

    Currently inherits the standard SQLAlchemy implementation.
    Override methods here when hypertable-specific queries are needed,
    e.g. time_bucket() aggregations, continuous aggregates, etc.
    """


class TimescaleExperimentRepository(SQLAlchemyExperimentRepository):
    """TimescaleDB experiment repository — same as SQLAlchemy for now."""
