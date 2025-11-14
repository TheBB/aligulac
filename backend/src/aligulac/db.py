from __future__ import annotations

import asyncio

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, types
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    password: Mapped[bytes]
    last_login: Mapped[datetime | None]
    is_superuser: Mapped[bool]
    username: Mapped[str]
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    email: Mapped[str | None]
    is_staff: Mapped[bool]
    is_active: Mapped[bool]
    date_joined: Mapped[datetime]


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

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date]
    author: Mapped[str]
    title: Mapped[str]
    text: Mapped[str]


class Earning(Base):
    __tablename__ = "earnings"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[id] = mapped_column(ForeignKey("event.id"))
    player_id: Mapped[id] = mapped_column(ForeignKey("player.id"))
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
    idx: Mapped[int]

    closed: Mapped[bool]
    big: Mapped[bool]
    noprint: Mapped[bool]

    fullname: Mapped[str]
    homepage: Mapped[str | None]
    lp_name: Mapped[str | None]

    tlpd_id: Mapped[int | None]
    tlpd_db: Mapped[int | None]
    tl_thread: Mapped[int | None]

    prizepool: Mapped[bool | None]
    earliest: Mapped[date | None]
    latest: Mapped[date | None]

    category: Mapped[str | None]
    kind: Mapped[str] = mapped_column("type")

    family: Mapped[list[Event]] = relationship(secondary="EventAdjacency")

    wcs_year: Mapped[int | None]
    wcs_tier: Mapped[int | None]


class EventAdjacency(Base):
    __tablename__ = "eventadjacency"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
    child_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
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

    name: Mapped[str]
    shortname: Mapped[str | None]
    scoreak: Mapped[float | None]
    scorepl: Mapped[float | None]
    meanrating: Mapped[float | None]
    founded: Mapped[date | None]
    disbanded: Mapped[date | None]
    active: Mapped[bool]
    homepage: Mapped[str | None]
    lp_name: Mapped[str | None]

    is_team: Mapped[bool]
    is_manual: Mapped[bool]

    players: Mapped[list[Player]] = relationship(
        secondary="GroupMembership",
        back_populates="groups",
    )


class GroupMembership(Base):
    __tablename__ = "groupmembership"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"))

    start: Mapped[date | None]
    end: Mapped[date | None]
    current: Mapped[bool]
    playing: Mapped[bool]


class Match(Base):
    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True)

    period_id: Mapped[int] = mapped_column(ForeignKey("period.id"))
    date: Mapped[date]
    pla_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    plb_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    sca: Mapped[int]
    scb: Mapped[int]

    rca: Mapped[str]
    rcb: Mapped[str]

    treated: Mapped[bool]
    event: Mapped[str]
    eventobj_id: Mapped[int | None] = mapped_column(ForeignKey("event.id"))

    submitter_id: Mapped[int | None] = mapped_column(ForeignKey("auth_user.id"))

    game: Mapped[str]
    offline: Mapped[bool]

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

    start: Mapped[date]
    end: Mapped[date]
    computed: Mapped[bool]
    needs_recompute: Mapped[bool]
    num_retplayers: Mapped[int]
    num_newplayers: Mapped[int]
    num_games: Mapped[int]
    dom_p: Mapped[float | None]
    dom_t: Mapped[float | None]
    dom_z: Mapped[float | None]


class Player(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True)

    tag: Mapped[str]
    name: Mapped[str | None]
    romanized_name: Mapped[str | None]
    birthday: Mapped[date | None]
    country: Mapped[str | None]
    race: Mapped[str]
    mcnum: Mapped[int | None]

    tlpd_id: Mapped[int | None]
    tlpd_db: Mapped[int | None]

    lp_name: Mapped[str | None]
    sc2e_id: Mapped[int | None]

    current_rating_id: Mapped[int | None] = mapped_column(ForeignKey("rating.id"))
    dom_val: Mapped[float | None]
    dom_start_id: Mapped[float | None] = mapped_column(ForeignKey("period.id"))
    dom_end_id: Mapped[float | None] = mapped_column(ForeignKey("period.id"))


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
