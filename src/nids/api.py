"""HTTP-сервис детектирования аномалий сетевого трафика.

Запуск в разработке:
    uvicorn nids.api:app --reload --app-dir src

Документация API поднимается сама: http://localhost:8000/docs

Модель грузится один раз при старте, а не на каждый запрос. Путь берётся
из переменной окружения MODEL_DIR -- это понадобится в цикле 4, когда
артефакты переедут в том контейнера.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
from fastapi import FastAPI, HTTPException

from nids.features import to_frame
from nids.schemas import Connection, Health, Prediction

MODEL_DIR = Path(os.getenv("MODEL_DIR", "artifacts"))
MODEL_FILE = "model.joblib"
METADATA_FILE = "metadata.json"

state: dict[str, Any] = {"model": None, "metadata": None}


def load_model(model_dir: Path | None = None) -> bool:
    """Загрузить модель и паспорт. Вернуть True, если получилось.

    Сервис намеренно поднимается даже без модели: так /health может честно
    сообщить, что он нездоров. Контейнер, падающий при старте, не даёт
    оркестратору ни одного внятного сигнала о причине.
    """
    directory = model_dir or MODEL_DIR
    model_path = directory / MODEL_FILE

    if not model_path.exists():
        state["model"] = None
        state["metadata"] = None
        return False

    state["model"] = joblib.load(model_path)

    metadata_path = directory / METADATA_FILE
    if metadata_path.exists():
        state["metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        state["metadata"] = {"model_version": "unknown"}
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    loaded = load_model()
    if not loaded:
        print(f"модель не найдена в {MODEL_DIR}; сервис отвечает 503 на /predict")
    yield
    state["model"] = None
    state["metadata"] = None


app = FastAPI(
    title="NIDS service",
    description="Детектирование аномалий сетевого трафика",
    version="0.1.0",
    lifespan=lifespan,
)


def _model_version() -> str:
    metadata = state.get("metadata") or {}
    return str(metadata.get("model_version", "unknown"))


@app.get("/health", response_model=Health, tags=["служебные"])
def health() -> Health:
    """Готовность сервиса. Используется healthcheck-ом в цикле 6."""
    loaded = state.get("model") is not None
    return Health(
        status="ok" if loaded else "degraded",
        model_loaded=loaded,
        model_version=_model_version() if loaded else None,
    )


@app.post("/predict", response_model=Prediction, tags=["предсказание"])
def predict(connection: Connection) -> Prediction:
    """Классифицировать соединение: нормальное или атака."""
    model = state.get("model")
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="модель не загружена; обучите её: python -m nids.train",
        )

    frame = to_frame(connection.model_dump())
    probability = float(model.predict_proba(frame)[0][1])
    label = "attack" if probability >= 0.5 else "normal"

    return Prediction(
        prediction=label,
        probability=round(probability, 4),
        model_version=_model_version(),
    )
