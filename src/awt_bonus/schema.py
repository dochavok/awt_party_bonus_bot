"""The database tables (requirements section 11), as SQLAlchemy Core.

Only catalog IDs are stored, never catalog data (CT-2, CT-3). Every time is stored
in UTC (NF-10). The schema is created and changed only by the Alembic migrations in
``awt_bonus/migrations`` (DB-4); these definitions must match them.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Dialect,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    TypeDecorator,
    UniqueConstraint,
)


class UTCDateTime(TypeDecorator[datetime]):
    """A timezone-aware time, stored in UTC (NF-10).

    Refuses naive times, so a local time can never be stored by mistake, and always
    reads back an aware UTC time.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError(f"times must be timezone-aware (NF-10), got {value!r}")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        assert isinstance(value, datetime)
        return value.replace(tzinfo=UTC)


metadata = MetaData()

player = Table(
    "player",
    metadata,
    Column("discord_user_id", BigInteger, primary_key=True, autoincrement=False),
    Column(
        "current_character_id",
        Integer,
        ForeignKey("character.id", ondelete="SET NULL"),
        nullable=True,
    ),
)

character = Table(
    "character",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("discord_user_id", BigInteger, nullable=False, index=True),
    Column("name", String(collation="NOCASE"), nullable=False, unique=True),
    Column("level", Integer, nullable=True),
    Column("level_updated_at", UTCDateTime, nullable=True),
)

character_entry = Table(
    "character_entry",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "character_id",
        Integer,
        ForeignKey("character.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("entry_id", String, nullable=False, index=True),
    UniqueConstraint("character_id", "entry_id"),
)

character_guild = Table(
    "character_guild",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "character_id",
        Integer,
        ForeignKey("character.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("guild_id", String, nullable=False),
    Column("joined_at", UTCDateTime, nullable=False),
    UniqueConstraint("character_id", "guild_id"),
)

character_item_count = Table(
    "character_item_count",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "character_id",
        Integer,
        ForeignKey("character.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("item_class_id", String, nullable=False),
    # How many items of the class are in use (IC-1); no row means 0.
    Column("count", Integer, nullable=False),
    UniqueConstraint("character_id", "item_class_id"),
    CheckConstraint("count BETWEEN 1 AND 30", name="ck_character_item_count_count"),
)

sit_out = Table(
    "sit_out",
    metadata,
    Column("discord_user_id", BigInteger, primary_key=True, autoincrement=False),
    Column("until", UTCDateTime, nullable=False),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("actor_user_id", BigInteger, nullable=False),
    # No foreign key: the record outlives a character the maintainer removes (CH-2).
    Column("character_id", Integer, nullable=False, index=True),
    Column("action", String, nullable=False),
    Column("before_json", Text, nullable=True),
    Column("after_json", Text, nullable=True),
    Column("at", UTCDateTime, nullable=False),
)
