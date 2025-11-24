from __future__ import annotations

import json
import os
import sys
from contextlib import AbstractAsyncContextManager, asynccontextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from litestar import Litestar, Response, get, post
from litestar import Request as LitestarRequest
from litestar.datastructures import State as LitestarState
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.config import OpenAPIConfig
from litestar.params import Parameter
from litestar.security.jwt import JWTCookieAuth, Token
from sqlalchemy.exc import NoResultFound

from . import db, models


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from litestar.connection import ASGIConnection as LitestarASGIConnection


class State(LitestarState):
    database: db.Database


type User = db.AuthUser
type Auth = JWTCookieAuth[User]
type AsgiConnection = LitestarASGIConnection[HTTPRouteHandler, User, Auth, State]
type Request = LitestarRequest[User, Auth, State]
type Session = db.Session


def db_connection(url: str) -> Callable[[Litestar], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def inner(app: Litestar) -> AsyncIterator[None]:
        async with db.Database(url) as database:
            app.state.database = database
            yield

    return inner


async def database_provider(state: State) -> db.Database:
    return state.database


async def session_provider(database: db.Database) -> AsyncIterator[Session]:
    async with database.session.begin() as session:
        yield session


@asynccontextmanager
async def session_context(app: Litestar) -> AsyncIterator[Session]:
    database: db.Database = app.state.database
    session_provider = app.dependencies["session"]
    session_it = (await session_provider(database=database)).__aiter__()

    session: db.Session = await session_it.__anext__()
    try:
        yield session
    finally:
        with suppress(StopAsyncIteration):
            await session_it.__anext__()


@get("/api/web/blog")
async def blog(
    session: Session,
    start: Annotated[int, Parameter(ge=0)] = 0,
    limit: Annotated[int, Parameter(ge=1, le=10)] = 10,
) -> models.BlogResponse:
    posts = await db.BlogPost.posts(session, start, limit)
    return models.BlogResponse.model_validate({"posts": posts})


@get("/api/web/topten")
async def top_ten(session: Session) -> models.TopTenResponse:
    period = await db.Period.latest(session)
    ratings = await db.Rating.ranking(session, period_id=period.id)
    return models.TopTenResponse.model_validate(
        {
            "period_id": period.id,
            "period_start": period.start,
            "period_end": period.end,
            "ratings": ratings,
        }
    )


@get("/api/web/whoami")
async def whoami(request: Request) -> models.LoginResponse:
    """Return the ID of the currently logged-in user.

    This endpoint is protected, so will trigger a 401 error if nobody is logged in."""
    return models.LoginResponse(username=request.user.username)


@get("/api/web/player")
async def get_player(player_id: int, session: Session) -> dict:
    player = await db.Player.from_pk(session, player_id)
    return {
        "tag": player.tag,
    }


# Suppress annoying 404s when debugging the API from the browser.
@get("/favicon.ico")
async def favicon() -> None:
    return None


@post("/api/web/login")
async def login(data: models.LoginRequest, session: Session) -> Response[models.LoginResponse]:
    try:
        user = await db.AuthUser.from_username(session, data.username)
    except NoResultFound:
        raise NotAuthorizedException

    if not user.password_valid(data.password):
        raise NotAuthorizedException

    return jwt_auth.login(
        identifier=data.username,
        response_body=models.LoginResponse(username=data.username),
    )


@post("/api/web/logout")
async def logout() -> Response:
    response = Response({"message": "logout successful"})
    response.delete_cookie("access_token")
    return response


@get("/api/web/protected")
async def protected() -> dict:
    return {
        "bonk": "hi",
    }


async def retrieve_user_handler(token: Token, connection: AsgiConnection) -> User | None:
    async with session_context(connection.app) as session:
        try:
            return await db.AuthUser.from_username(session, token.sub)
        except NoResultFound:
            return None


jwt_auth = JWTCookieAuth[User](
    retrieve_user_handler=retrieve_user_handler,
    token_secret=os.environ.get("ALIGULAC_SECRET", "dev-secret"),
    exclude=[
        "/favicon.ico",
        "/schema",
        "/api/web/login",
        "/api/web/logout",
        "/api/web/blog",
        "/api/web/player",
        "/api/web/topten",
    ],
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
            protected,
            top_ten,
            blog,
            login,
            logout,
            whoami,
        ],
        lifespan=[
            db_connection(db_connstr),
        ],
        dependencies={
            "database": Provide(database_provider),
            "session": Provide(session_provider),
        },
        openapi_config=OpenAPIConfig(title="Aligulac", version="0.0.1"),
        middleware=[jwt_auth.middleware],
    )


def dump_openapi() -> None:
    path = Path(sys.argv[1])
    schema = create_app().openapi_schema.to_schema()

    with path.open("w") as f:
        json.dump(schema, f, indent=2)


if __name__ == "__main__":
    dump_openapi()
