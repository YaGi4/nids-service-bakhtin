"""Порог качества на воспроизводимой контрольной выборке."""

import json


def test_f1_at_least_085(trained_model_dir):
    metadata = json.loads((trained_model_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["metrics"]["f1"] >= 0.85
