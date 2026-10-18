"""Контракт API: что сервис принимает и что отдаёт.

Pydantic проверяет входные данные до того, как они дойдут до модели.
Это не формальность: модель на мусорном входе не падает, а молча возвращает
уверенное неверное предсказание. Валидация -- единственное место, где такой
запрос можно остановить.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Connection(BaseModel):
    """Одно сетевое соединение."""

    protocol_type: Literal["tcp", "udp", "icmp"]
    service: str = Field(examples=["http"], max_length=32)
    flag: str = Field(examples=["SF"], max_length=8)

    duration: float = Field(ge=0, examples=[3.5])
    src_bytes: int = Field(ge=0, examples=[491])
    dst_bytes: int = Field(ge=0, examples=[2032])
    count: int = Field(ge=0, le=1000, examples=[4])
    srv_count: int = Field(ge=0, le=1000, examples=[3])

    serror_rate: float = Field(ge=0, le=1, examples=[0.0])
    rerror_rate: float = Field(ge=0, le=1, examples=[0.0])
    same_srv_rate: float = Field(ge=0, le=1, examples=[0.95])
    diff_srv_rate: float = Field(ge=0, le=1, examples=[0.05])

    dst_host_count: int = Field(ge=0, le=255, examples=[31])
    dst_host_srv_count: int = Field(ge=0, le=255, examples=[29])


class Prediction(BaseModel):
    """Ответ сервиса."""

    # Без этой строки pydantic ругается на поле, начинающееся с model_:
    # префикс зарезервирован под его собственные атрибуты.
    model_config = ConfigDict(protected_namespaces=())

    prediction: Literal["normal", "attack"]
    probability: float = Field(ge=0, le=1, description="вероятность класса attack")
    model_version: str


class Health(BaseModel):
    """Состояние сервиса для проверок живости."""

    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok", "degraded"]
    model_loaded: bool
    model_version: str | None = None
