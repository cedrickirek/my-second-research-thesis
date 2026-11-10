"""Database layer for the teacher annotation app.

DB-agnostic SQLAlchemy Core. Defaults to a local SQLite file so the app runs
with zero setup; set the ``DATABASE_URL`` environment variable (e.g. a Supabase
Postgres URL) to deploy with a shared, hosted database.

Teacher identity is a *code only* (e.g. ``T01``). Names never enter the
database -- see the anonymisation rule in ``code-for-the-thesis/CLAUDE.md``.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_URL = "sqlite:///annotations.db"

# Annotation item types.
RESPONSE = "response"
RETRIEVAL = "retrieval"

metadata = MetaData()

items = Table(
    "items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("item_type", String(20), nullable=False),  # RESPONSE | RETRIEVAL
    Column("query", Text, nullable=False),  # the student / BAC question
    Column("content", Text, nullable=False),  # tutor response, or retrieved chunk
    Column("source", String(200)),  # optional provenance label
)

# Annotators are identified by code only -- no names, ever.
annotators = Table(
    "annotators",
    metadata,
    Column("code", String(20), primary_key=True),
)

# Which annotator sees which item. This table encodes the overlap design
# (some items triple-annotated for inter-rater agreement, some single).
assignments = Table(
    "assignments",
    metadata,
    Column("annotator_code", String(20), primary_key=True),
    Column("item_id", Integer, primary_key=True),
)

annotations = Table(
    "annotations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("annotator_code", String(20), nullable=False),
    Column("item_id", Integer, nullable=False),
    Column("item_type", String(20), nullable=False),
    # Response-scoring criteria (1-5), null for retrieval items.
    Column("factual_accuracy", Integer),
    Column("curriculum_alignment", Integer),
    Column("pedagogical_quality", Integer),
    Column("language_register", Integer),
    # Retrieval relevance (0-3), null for response items.
    Column("relevance", Integer),
    Column("comment", Text),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    UniqueConstraint("annotator_code", "item_id", name="uq_annotator_item"),
)


def get_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine.

    Resolution order: explicit ``url`` arg, then ``DATABASE_URL`` env var, then
    a local SQLite file. ``pool_pre_ping`` keeps pooled Postgres connections
    healthy across Streamlit reruns.
    """
    url = url or os.environ.get("DATABASE_URL") or DEFAULT_SQLITE_URL
    logger.info("Creating engine for %s", url.split("@")[-1])  # don't log creds
    return create_engine(url, pool_pre_ping=True, future=True)


def init_db(engine: Engine) -> None:
    """Create all tables if they do not already exist."""
    metadata.create_all(engine)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def is_empty(engine: Engine) -> bool:
    """True if no items have been loaded yet."""
    with engine.begin() as conn:
        count = conn.execute(select(func.count()).select_from(items)).scalar_one()
    return count == 0


def seed(
    engine: Engine,
    seed_items: list[dict[str, Any]],
    seed_annotators: list[str],
    seed_assignments: list[tuple[str, int]],
) -> None:
    """Insert placeholder content. Idempotent guard lives in the caller."""
    with engine.begin() as conn:
        conn.execute(insert(items), seed_items)
        conn.execute(insert(annotators), [{"code": c} for c in seed_annotators])
        conn.execute(
            insert(assignments),
            [{"annotator_code": a, "item_id": i} for a, i in seed_assignments],
        )
    logger.info(
        "Seeded %d items, %d annotators, %d assignments",
        len(seed_items),
        len(seed_annotators),
        len(seed_assignments),
    )


def annotator_exists(engine: Engine, code: str) -> bool:
    with engine.begin() as conn:
        row = conn.execute(
            select(annotators.c.code).where(annotators.c.code == code)
        ).first()
    return row is not None


def get_assigned_items(engine: Engine, code: str) -> list[dict[str, Any]]:
    """All items assigned to ``code``, ordered by id."""
    stmt = (
        select(items)
        .join(assignments, assignments.c.item_id == items.c.id)
        .where(assignments.c.annotator_code == code)
        .order_by(items.c.id)
    )
    with engine.begin() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_annotated_item_ids(engine: Engine, code: str) -> set[int]:
    """Item ids this annotator has already submitted."""
    stmt = select(annotations.c.item_id).where(annotations.c.annotator_code == code)
    with engine.begin() as conn:
        return {r[0] for r in conn.execute(stmt).all()}


def get_annotation(engine: Engine, code: str, item_id: int) -> dict[str, Any] | None:
    """Return an existing annotation (for resume / edit), or None."""
    stmt = select(annotations).where(
        annotations.c.annotator_code == code, annotations.c.item_id == item_id
    )
    with engine.begin() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def upsert_annotation(
    engine: Engine,
    code: str,
    item_id: int,
    item_type: str,
    scores: dict[str, int | None],
    comment: str,
) -> None:
    """Insert a new annotation or update the existing one for (code, item).

    Manual upsert (SELECT-then-INSERT/UPDATE) keeps this portable across SQLite
    and Postgres without dialect-specific ON CONFLICT clauses. Concurrency at
    5-10 annotators is negligible.
    """
    now = _now()
    payload = {**scores, "comment": comment, "updated_at": now}
    with engine.begin() as conn:
        existing = conn.execute(
            select(annotations.c.id).where(
                annotations.c.annotator_code == code,
                annotations.c.item_id == item_id,
            )
        ).first()
        if existing:
            conn.execute(
                update(annotations)
                .where(annotations.c.id == existing[0])
                .values(**payload)
            )
        else:
            conn.execute(
                insert(annotations).values(
                    annotator_code=code,
                    item_id=item_id,
                    item_type=item_type,
                    created_at=now,
                    **payload,
                )
            )


def export_dataframe(engine: Engine) -> pd.DataFrame:
    """All annotations joined with item context, ready for analysis / CSV."""
    stmt = (
        select(
            annotations.c.annotator_code,
            annotations.c.item_id,
            annotations.c.item_type,
            annotations.c.factual_accuracy,
            annotations.c.curriculum_alignment,
            annotations.c.pedagogical_quality,
            annotations.c.language_register,
            annotations.c.relevance,
            annotations.c.comment,
            annotations.c.created_at,
            annotations.c.updated_at,
            items.c.source,
            items.c.query,
        )
        .join(items, items.c.id == annotations.c.item_id)
        .order_by(annotations.c.item_id, annotations.c.annotator_code)
    )
    with engine.begin() as conn:
        return pd.read_sql(stmt, conn)