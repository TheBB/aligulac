from __future__ import annotations

import os
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING

from litestar import Litestar, Request, Response, get, post
from litestar.connection import ASGIConnection
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from litestar.security.jwt import JWTCookieAuth, Token
from pydantic import BaseModel

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


class LoginData(BaseModel):
    username: str
    password: str


@post("/api/login")
async def login(data: LoginData) -> Response:
    if data.username != "eivind" or data.password != "heihei":
        raise NotAuthorizedException
    return jwt_auth.login(identifier="eivind", response_body={"message": "login successful"})


@post("/api/logout")
async def logout() -> Response:
    response = Response({"message": "logout successful"})
    response.delete_cookie("access_token")
    return response


@get("/api/protected")
async def protected() -> dict:
    return {
        "bonk": "hi",
    }


class User(BaseModel):
    username: str


def retrieve_user_handler(token: Token, _: ASGIConnection) -> User | None:
    if token.sub == "eivind":
        return User(username="eivind")
    return None


jwt_auth = JWTCookieAuth[User](
    retrieve_user_handler=retrieve_user_handler,
    token_secret=os.environ.get("ALIGULAC_SECRET", "dev-secret"),
    exclude=["/favicon.ico", "/api/login", "/api/logout", "/api/web/player"],
    key="access_token",
    secure=bool(os.environ.get("ALIGULAC_PROD")),
    samesite="strict",
)


def create_app() -> Litestar:
    db_url = os.environ.get("ALIGULAC_DB", "aligulac:aligulac@localhost:5432/aligulac")
    db_connstr = f"postgresql+asyncpg://{db_url}"

    return Litestar(
        [
            favicon,
            get_player,
            login,
            logout,
            protected,
        ],
        lifespan=[
            db_connection(db_connstr),
        ],
        dependencies={
            "database": Provide(database_provider),
            "session": Provide(session_provider),
        },
        middleware=[jwt_auth.middleware],
    )
