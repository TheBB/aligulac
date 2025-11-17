from __future__ import annotations

import os
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING

from litestar import Litestar, get
from litestar.di import Provide

from . import db


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from litestar.datastructures import State


def db_connection(url: str) -> Callable[[Litestar], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def inner(app: Litestar) -> AsyncIterator[None]:
        async with db.Database(url) as database:
            app.state.database = database
            yield

    return inner


async def database_provider(state: State) -> db.Database:
    return state.database  # type: ignore[no-any-return]


async def session_provider(database: db.Database) -> AsyncIterator[db.Session]:
    async with database.session.begin() as session:
        yield session


@get("/api/web/player")
async def get_player(player_id: int, session: db.Session) -> dict:
    player = await db.Player.from_pk(session, player_id)
    return {
        "tag": player.tag,
    }


# Suppress annoying 404s when debugging the API from the browser.
@get("/favicon.ico")
async def favicon() -> None:
    return None


def create_app() -> Litestar:
    db_url = os.environ.get("ALIGULAC_DB", "aligulac:aligulac@localhost:5432/aligulac")
    db_connstr = f"postgresql+asyncpg://{db_url}"

    return Litestar(
        [
            favicon,
            get_player,
        ],
        lifespan=[
            db_connection(db_connstr),
        ],
        dependencies={
            "database": Provide(database_provider),
            "session": Provide(session_provider),
        },
    )
