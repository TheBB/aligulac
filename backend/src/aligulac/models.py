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
    country: str

    @model_validator(mode="before")
    @classmethod
    def validate(cls, data: Any) -> Any:
        if isinstance(data, db.Player):
            return {
                "id": data.id,
                "tag": data.tag,
                "race": data.race,
                "country": data.country,
            }
        return data


class ListedRating(BaseModel):
    rating: float
    vp: float
    vt: float
    vz: float

    @model_validator(mode="before")
    @classmethod
    def validate(cls, data: Any) -> Any:
        if isinstance(data, db.Rating):
            return {
                "rating": data.rating,
                "vp": data.rating_vp,
                "vt": data.rating_vt,
                "vz": data.rating_vz,
            }
        return data


class ListedRatingEntry(BaseModel):
    player: ListedPlayer
    current: ListedRating
    previous: ListedRating

    @model_validator(mode="before")
    @classmethod
    def validate(cls, data: Any) -> Any:
        if isinstance(data, db.Rating):
            return {
                "player": data.player,
                "current": data,
                "previous": data.prev,
            }
        return data


class TopTenResponse(BaseModel):
    period_start: date
    period_end: date
    ratings: list[ListedRatingEntry]
