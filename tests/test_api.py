"""Тесты HTTP-контракта сервиса.

Это контрактные тесты: они проверяют не качество модели, а то, что сервис
отвечает оговоренным форматом и внятно реагирует на плохой вход.
"""

from __future__ import annotations


def test_health_reports_loaded_model(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True


def test_predict_returns_valid_contract(client, normal_connection):
    response = client.post("/predict", json=normal_connection)

    assert response.status_code == 200
    body = response.json()
    assert body["prediction"] in {"normal", "attack"}
    assert 0.0 <= body["probability"] <= 1.0
    assert body["model_version"]


def test_predict_recognises_syn_flood(client, attack_connection):
    """Проверка не контракта, а смысла: явную атаку модель обязана поймать."""
    response = client.post("/predict", json=attack_connection)

    assert response.status_code == 200
    assert response.json()["prediction"] == "attack"


def test_predict_rejects_unknown_protocol(client, normal_connection):
    bad = {**normal_connection, "protocol_type": "carrier_pigeon"}

    response = client.post("/predict", json=bad)

    assert response.status_code == 422


def test_predict_rejects_out_of_range_rate(client, normal_connection):
    bad = {**normal_connection, "serror_rate": 3.14}

    response = client.post("/predict", json=bad)

    assert response.status_code == 422


def test_predict_rejects_missing_field(client, normal_connection):
    bad = {k: v for k, v in normal_connection.items() if k != "src_bytes"}

    response = client.post("/predict", json=bad)

    assert response.status_code == 422
