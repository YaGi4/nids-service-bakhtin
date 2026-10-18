"""Запись результатов классификации в PostgreSQL."""

from __future__ import annotations

import logging
import os

import psycopg

logger = logging.getLogger(__name__)


def save_prediction(connection: dict, prediction: str, probability: float,
                    model_version: str, response_ms: float) -> None:
    """Записать предсказание; ошибка БД не должна прерывать ответ API."""
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO predictions
                    (model_version, protocol_type, service, flag, duration, src_bytes,
                     dst_bytes, prediction, probability, response_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (model_version, connection["protocol_type"], connection["service"],
                     connection["flag"], connection["duration"], connection["src_bytes"],
                     connection["dst_bytes"], prediction, probability, response_ms),
                )
    except psycopg.Error:
        logger.exception("Не удалось записать предсказание в PostgreSQL")
