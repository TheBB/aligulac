from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, model_validator

from . import db


type Race = Literal["P", "T", "Z", "R"]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: str


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


class TopTenResponse(BaseModel):
    period_id: int
    period_start: date
    period_end: date
    ratings: list[ListedRatingEntry]
