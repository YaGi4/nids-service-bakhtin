"""Общие фикстуры.

Тесты не должны зависеть от того, обучил ли кто-то модель руками.
Поэтому маленькая модель обучается прямо здесь, во временном каталоге,
один раз на весь прогон.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))

from make_dataset import generate  # noqa: E402

from nids.train import train  # noqa: E402


@pytest.fixture(scope="session")
def dataset():
    """Маленький набор данных: 1500 строк хватает и быстро считается."""
    return generate(rows=1500)


@pytest.fixture(scope="session")
def trained_model_dir(tmp_path_factory, dataset) -> Path:
    """Каталог с обученной моделью и паспортом."""
    workdir = tmp_path_factory.mktemp("model")
    data_file = workdir / "connections.csv"
    dataset.to_csv(data_file, index=False)

    train(data_file, workdir)
    return workdir


@pytest.fixture
def client(trained_model_dir):
    """TestClient с уже загруженной моделью."""
    from fastapi.testclient import TestClient

    from nids import api

    api.load_model(trained_model_dir)
    with TestClient(api.app) as test_client:
        api.load_model(trained_model_dir)  # lifespan мог сбросить состояние
        yield test_client


@pytest.fixture
def normal_connection() -> dict:
    """Запрос, который модель должна считать нормальным трафиком."""
    return {
        "protocol_type": "tcp",
        "service": "http",
        "flag": "SF",
        "duration": 3.5,
        "src_bytes": 491,
        "dst_bytes": 2032,
        "count": 4,
        "srv_count": 3,
        "serror_rate": 0.0,
        "rerror_rate": 0.0,
        "same_srv_rate": 0.95,
        "diff_srv_rate": 0.05,
        "dst_host_count": 31,
        "dst_host_srv_count": 29,
    }


@pytest.fixture
def attack_connection() -> dict:
    """Запрос с профилем SYN flood."""
    return {
        "protocol_type": "tcp",
        "service": "other",
        "flag": "S0",
        "duration": 0.0,
        "src_bytes": 0,
        "dst_bytes": 0,
        "count": 480,
        "srv_count": 470,
        "serror_rate": 1.0,
        "rerror_rate": 0.05,
        "same_srv_rate": 1.0,
        "diff_srv_rate": 0.0,
        "dst_host_count": 255,
        "dst_host_srv_count": 255,
    }
