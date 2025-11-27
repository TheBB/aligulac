from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, model_validator

from . import db


if TYPE_CHECKING:
    from collections.abc import Callable


def is_at_most(hi: int, desc: str) -> Callable[[int], int]:
    def validator(value: int) -> int:
        if value > hi:
            raise ValueError(f"{desc} cannot be more than {hi}")
        return value

    return validator


type Race = Literal["P", "T", "Z", "R"]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: str


class BlogRequest(BaseModel):
    start: int = 0
    limit: Annotated[int, AfterValidator(is_at_most(10, "limit"))] = 10


class BlogPost(BaseModel):
    date: date
    author: str
    title: str
    text: str

    @model_validator(mode="before")
    @classmethod
    def pre_validate(cls, data: Any) -> Any:
        if isinstance(data, db.BlogPost):
            return {
                "date": data.date,
                "author": data.author,
                "title": data.title,
                "text": data.text,
            }
        return data


class BlogResponse(BaseModel):
    posts: list[BlogPost]
    next_offset: int | None


class ListedPlayer(BaseModel):
    id: int
    tag: str
    race: Race
    country: str | None

    @model_validator(mode="before")
    @classmethod
    def pre_validate(cls, data: Any) -> Any:
        if isinstance(data, db.Player):
            return {
                "id": data.id,
                "tag": data.tag,
                "race": data.race,
                "country": data.country,
            }
        return data


class ListedRating(BaseModel):
    period_id: int

    rating: float
    rating_vp: float
    rating_vt: float
    rating_vz: float

    position: int | None
    position_vp: int | None
    position_vt: int | None
    position_vz: int | None

    decay: int

    @model_validator(mode="before")
    @classmethod
    def pre_validate(cls, data: Any) -> Any:
        if isinstance(data, db.Rating):
            return {
                "period_id": data.period_id,
                "rating": data.rating,
                "rating_vp": data.rating_vp,
                "rating_vt": data.rating_vt,
                "rating_vz": data.rating_vz,
                "position": data.position,
                "position_vp": data.position_vp,
                "position_vt": data.position_vt,
                "position_vz": data.position_vz,
                "decay": data.decay,
            }
        return data


class ListedRatingEntry(BaseModel):
    player: ListedPlayer
    current: ListedRating
    previous: ListedRating | None

    @model_validator(mode="before")
    @classmethod
    def pre_validate(cls, data: Any) -> Any:
        if isinstance(data, db.Rating):
            return {
                "player": data.player,
                "current": data,
                "previous": data.prev,
            }
        return data


class RatingList(BaseModel):
    period_id: int
    period_start: date
    period_end: date
    first_period_id: int
    last_period_id: int
    count: int
    ratings: list[ListedRatingEntry]


class TopTen(BaseModel):
    period_id: int
    period_start: date
    period_end: date
    ratings: list[ListedRatingEntry]
