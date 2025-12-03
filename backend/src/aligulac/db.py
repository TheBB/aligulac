from __future__ import annotations

from base64 import b64encode
from datetime import date, datetime
from decimal import Decimal
from hashlib import pbkdf2_hmac
from typing import TYPE_CHECKING, Literal, Self, cast

from sqlalchemy import ForeignKey, Function, Index, func, select, text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload


if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType


INACTIVE_THRESHOLD = 4

ROW_NUMBER: Function[int] = func.row_number()


type Session = AsyncSession


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Alias(Base):
    __tablename__ = "alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    player_id: Mapped[int | None] = mapped_column(ForeignKey("player.id"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("group.id"))


class AuthGroup(Base):
    __tablename__ = "auth_group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class AuthGroupMembership(Base):
    __tablename__ = "auth_user_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_user.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("auth_group.id"))


class AuthUser(Base):
    __tablename__ = "auth_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    password: Mapped[str]
    last_login: Mapped[datetime | None]
    is_superuser: Mapped[bool]
    username: Mapped[str]
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    email: Mapped[str | None]
    is_staff: Mapped[bool]
    is_active: Mapped[bool]
    date_joined: Mapped[datetime]

    @staticmethod
    async def from_username(session: Session, username: str) -> AuthUser:
        result = await session.execute(select(AuthUser).where(AuthUser.username == username))
        return result.scalar_one()

    def password_valid(self, password: str) -> bool:
        method, niters, salt, checksum = self.password.encode().split(b"$")
        if method != b"pbkdf2_sha256":
            return False
        return b64encode(pbkdf2_hmac("sha256", password.encode(), salt, int(niters))) == checksum


class ApiKey(Base):
    __tablename__ = "apikey"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str]
    date_opened: Mapped[date]
    organization: Mapped[str]
    contact: Mapped[str]
    requests: Mapped[int]


class BalanceEntry(Base):
    __tablename__ = "balanceentry"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date]
    pvt_wins: Mapped[int]
    pvt_losses: Mapped[int]
    pvz_wins: Mapped[int]
    pvz_losses: Mapped[int]
    tvz_wins: Mapped[int]
    tvz_losses: Mapped[int]
    p_gains: Mapped[float]
    t_gains: Mapped[float]
    z_gains: Mapped[float]


class BlogPost(Base):
    __tablename__ = "blog_post"
    __table_args__ = (Index("ix_blog_post_date", text("date DESC")),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date]
    author: Mapped[str]
    title: Mapped[str]
    text: Mapped[str]

    @staticmethod
    async def posts(session: Session, offset: int = 0, limit: int = 10) -> tuple[Sequence[BlogPost], bool]:
        result = await session.execute(
            select(BlogPost).order_by(BlogPost.date.desc()).offset(offset).limit(limit + 1)
        )

        rows = result.scalars().all()
        has_more = len(rows) == limit + 1
        if has_more:
            rows = rows[:-1]
        return rows, has_more


class Earning(Base):
    __tablename__ = "earnings"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    earnings: Mapped[int | None]
    origearnings: Mapped[Decimal]
    currency: Mapped[str]
    placement: Mapped[int]


class Event(Base):
    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str]

    parent_id: Mapped[int | None] = mapped_column(ForeignKey("event.id"))
    lft: Mapped[int | None]
    rgt: Mapped[int | None]
    idx: Mapped[int] = mapped_column(index=True)

    closed: Mapped[bool] = mapped_column(index=True)
    big: Mapped[bool]
    noprint: Mapped[bool] = mapped_column(index=True)

    fullname: Mapped[str]
    homepage: Mapped[str | None]
    lp_name: Mapped[str | None]

    tlpd_id: Mapped[int | None]
    tlpd_db: Mapped[int | None]
    tl_thread: Mapped[int | None]

    prizepool: Mapped[bool | None] = mapped_column(index=True)
    earliest: Mapped[date | None] = mapped_column(index=True)
    latest: Mapped[date | None] = mapped_column(index=True)

    category: Mapped[str | None] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column("type", index=True)

    wcs_year: Mapped[int | None]
    wcs_tier: Mapped[int | None]


class EventAdjacency(Base):
    __tablename__ = "eventadjacency"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("event.id"), index=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("event.id"), index=True)
    distance: Mapped[int | None]


class FaqPost(Base):
    __tablename__ = "faq_post"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    text: Mapped[str]
    index: Mapped[int]


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(index=True)
    shortname: Mapped[str | None]
    scoreak: Mapped[float | None]
    scorepl: Mapped[float | None]
    meanrating: Mapped[float | None]
    founded: Mapped[date | None]
    disbanded: Mapped[date | None]
    active: Mapped[bool] = mapped_column(index=True)
    homepage: Mapped[str | None]
    lp_name: Mapped[str | None]

    is_team: Mapped[bool] = mapped_column(index=True)
    is_manual: Mapped[bool]

    # players: Mapped[list[Player]] = relationship(
    #     secondary="groupmembership",
    #     # back_populates="groups",
    # )


class GroupMembership(Base):
    __tablename__ = "groupmembership"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"))

    start: Mapped[date | None]
    end: Mapped[date | None]
    current: Mapped[bool] = mapped_column(index=True)
    playing: Mapped[bool] = mapped_column(index=True)


class Match(Base):
    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True)

    period_id: Mapped[int] = mapped_column(ForeignKey("period.id"))
    date: Mapped[date]
    pla_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    plb_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    sca: Mapped[int] = mapped_column(index=True)
    scb: Mapped[int] = mapped_column(index=True)

    rca: Mapped[str] = mapped_column(index=True)
    rcb: Mapped[str] = mapped_column(index=True)

    treated: Mapped[bool]
    event: Mapped[str]
    eventobj_id: Mapped[int | None] = mapped_column(ForeignKey("event.id"))

    submitter_id: Mapped[int | None] = mapped_column(ForeignKey("auth_user.id"))

    game: Mapped[str] = mapped_column(index=True)
    offline: Mapped[bool] = mapped_column(index=True)

    rta_id: Mapped[int | None] = mapped_column(ForeignKey("rating.id"))
    rtb_id: Mapped[int | None] = mapped_column(ForeignKey("rating.id"))


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True)

    type: Mapped[str]
    message: Mapped[str]
    params: Mapped[str]

    player_id: Mapped[int | None] = mapped_column(ForeignKey("player.id"))
    event_id: Mapped[int | None] = mapped_column(ForeignKey("player.id"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("player.id"))
    match_id: Mapped[int | None] = mapped_column(ForeignKey("player.id"))


class MiniUrl(Base):
    __tablename__ = "miniurl"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str]
    long_url: Mapped[str] = mapped_column("longURL")
    date: Mapped[date]
    submitter_id: Mapped[int | None] = mapped_column(ForeignKey("auth_user.id"))
    nb_access: Mapped[int]


class Period(Base):
    __tablename__ = "period"

    id: Mapped[int] = mapped_column(primary_key=True)

    start: Mapped[date] = mapped_column(index=True)
    end: Mapped[date] = mapped_column(index=True)
    computed: Mapped[bool] = mapped_column(index=True)
    needs_recompute: Mapped[bool] = mapped_column(index=True)
    num_retplayers: Mapped[int]
    num_newplayers: Mapped[int]
    num_games: Mapped[int]
    dom_p: Mapped[float | None]
    dom_t: Mapped[float | None]
    dom_z: Mapped[float | None]

    @staticmethod
    async def latest(session: Session) -> Period:
        result = await session.execute(
            select(Period).where(Period.computed).order_by(Period.start.desc()).limit(1)
        )
        return result.scalar_one()

    @staticmethod
    async def first(session: Session) -> Period:
        result = await session.execute(
            select(Period).where(Period.computed).order_by(Period.start.asc()).limit(1)
        )
        return result.scalar_one()

    @staticmethod
    async def from_pk(session: Session, period_id: int) -> Period:
        result = await session.execute(select(Period).where(Period.id == period_id))
        return result.scalar_one()

    async def active_nationalities(self, session: Session) -> Sequence[str]:
        filters = [
            Rating.period_id == self.id,
            Rating.decay < INACTIVE_THRESHOLD,
        ]

        result = await session.execute(
            select(Player.country)
            .join(Rating, Rating.player_id == Player.id)
            .join(Period, Rating.period_id == Period.id)
            .where(*filters, Player.country.is_not(None))
            .distinct()
        )

        # We have filtered away null countries, so this cast should be safe
        return cast("Sequence[str]", result.scalars().all())


class Player(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True)

    tag: Mapped[str] = mapped_column(index=True)
    name: Mapped[str | None]
    romanized_name: Mapped[str | None]
    birthday: Mapped[date | None]
    country: Mapped[str | None] = mapped_column(index=True)
    race: Mapped[str] = mapped_column(index=True)
    mcnum: Mapped[int | None]

    tlpd_id: Mapped[int | None]
    tlpd_db: Mapped[int | None]

    lp_name: Mapped[str | None]
    sc2e_id: Mapped[int | None]

    current_rating_id: Mapped[int | None] = mapped_column(ForeignKey("rating.id"))
    dom_val: Mapped[float | None]
    dom_start_id: Mapped[float | None] = mapped_column(ForeignKey("period.id"))
    dom_end_id: Mapped[float | None] = mapped_column(ForeignKey("period.id"))

    @staticmethod
    async def from_pk(session: Session, player_id: int) -> Player:
        result = await session.execute(select(Player).where(Player.id == player_id))
        return result.scalar_one()


class PreMatchGroup(Base):
    __tablename__ = "prematchgroup"

    id: Mapped[int] = mapped_column(primary_key=True)

    date: Mapped[date]
    event: Mapped[str]
    source: Mapped[str | None]
    contact: Mapped[str | None]
    notes: Mapped[str | None]

    game: Mapped[str]
    offline: Mapped[bool]


class PreMatch(Base):
    __tablename__ = "prematch"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("prematchgroup.id"))

    pla_id: Mapped[int | None] = mapped_column(ForeignKey("player.id"))
    plb_id: Mapped[int | None] = mapped_column(ForeignKey("player.id"))
    pla_string: Mapped[str | None]
    plb_string: Mapped[str | None]
    sca: Mapped[int]
    scb: Mapped[int]
    date: Mapped[date]

    rca: Mapped[str | None]
    rcb: Mapped[str | None]


class Rating(Base):
    __tablename__ = "rating"
    __table_args__ = (Index("ix_rating_period_decay", "period_id", "decay"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    period_id: Mapped[int] = mapped_column(ForeignKey("period.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    prev_id: Mapped[int | None] = mapped_column(ForeignKey("rating.id"))

    rating: Mapped[float]
    rating_vp: Mapped[float]
    rating_vt: Mapped[float]
    rating_vz: Mapped[float]

    dev: Mapped[float]
    dev_vp: Mapped[float]
    dev_vt: Mapped[float]
    dev_vz: Mapped[float]

    comp_rat: Mapped[float | None]
    comp_rat_vp: Mapped[float | None]
    comp_rat_vt: Mapped[float | None]
    comp_rat_vz: Mapped[float | None]

    bf_rating: Mapped[float]
    bf_rating_vp: Mapped[float]
    bf_rating_vt: Mapped[float]
    bf_rating_vz: Mapped[float]

    bf_dev: Mapped[float]
    bf_dev_vp: Mapped[float]
    bf_dev_vt: Mapped[float]
    bf_dev_vz: Mapped[float]

    position: Mapped[int | None]
    position_vp: Mapped[int | None]
    position_vt: Mapped[int | None]
    position_vz: Mapped[int | None]

    decay: Mapped[int]
    domination: Mapped[float | None]

    player: Mapped[Player] = relationship(foreign_keys="Rating.player_id")
    prev: Mapped[Rating | None] = relationship(foreign_keys="Rating.prev_id", remote_side="Rating.id")

    @staticmethod
    async def ranking(
        session: Session,
        period_id: int,
        offset: int = 0,
        limit: int = 10,
        sort: Literal["vp", "vt", "vz"] | None = None,
        nats: str | None = None,
    ) -> tuple[Sequence[Rating], int]:
        filters = [
            Rating.period_id == period_id,
            Rating.decay < INACTIVE_THRESHOLD,
        ]

        if nats == "foreigners":
            filters.append(Rating.player.has(Player.country != "KR"))
        elif nats is not None:
            filters.append(Rating.player.has(Player.country == nats))

        match sort:
            case None:
                sort_expr = Rating.rating.desc()
            case "vp":
                sort_expr = (Rating.rating_vp + Rating.rating).desc()
            case "vt":
                sort_expr = (Rating.rating_vt + Rating.rating).desc()
            case "vz":
                sort_expr = (Rating.rating_vz + Rating.rating).desc()

        result_count = await session.execute(select(func.count()).select_from(Rating).where(*filters))
        count = result_count.scalar_one()

        result = await session.execute(
            select(Rating)
            .where(*filters)
            .order_by(sort_expr)
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(Rating.player),
                selectinload(Rating.prev),
            )
        )
        rows = result.scalars().all()

        return rows, count

    @staticmethod
    async def posts(session: Session, offset: int = 0, limit: int = 10) -> tuple[Sequence[BlogPost], bool]:
        result = await session.execute(
            select(BlogPost).order_by(BlogPost.date.desc()).offset(offset).limit(limit + 1)
        )

        rows = result.scalars().all()
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:-1]
        return rows, has_more


class Story(Base):
    __tablename__ = "story"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    date: Mapped[date]

    event_id: Mapped[int | None] = mapped_column(ForeignKey("event.id"))
    message: Mapped[str]
    params: Mapped[str]


class WcsPoints(Base):
    __tablename__ = "wcspoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    points: Mapped[int]
    placement: Mapped[int]


class Database:
    url: str
    session: async_sessionmaker[Session]

    _engine: AsyncEngine

    def __init__(self, url: str) -> None:
        self.url = url

    async def __aenter__(self) -> Self:
        engine = create_async_engine(self.url)
        self._engine = engine
        self.session = async_sessionmaker(engine, expire_on_commit=False)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._engine.dispose()
