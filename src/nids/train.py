"""Обучение модели детектирования аномалий.

Запуск:
    python -m nids.train
    python -m nids.train --data data/connections.csv --out artifacts

Кроме самой модели скрипт сохраняет metadata.json -- паспорт обучения:
seed, версии библиотек, размер выборки и достигнутые метрики. Без паспорта
файл model.joblib -- это чёрный ящик неизвестного происхождения.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from nids.features import build_preprocessor, split_xy

SEED = 42
TEST_SIZE = 0.25
MODEL_FILE = "model.joblib"
METADATA_FILE = "metadata.json"


def build_model() -> Pipeline:
    """Препроцессор и классификатор -- одним объектом.

    n_jobs=-1 ускоряет обучение, но не влияет на результат: детерминизм
    обеспечивает random_state, а не число потоков.
    """
    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=120,
                    max_depth=14,
                    min_samples_leaf=2,
                    random_state=SEED,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def file_digest(path: Path) -> str:
    """SHA-256 файла данных. Позволяет доказать, на чём именно учили."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def train(data_path: Path, out_dir: Path) -> dict:
    df = pd.read_csv(data_path)
    X, y = split_xy(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=SEED, stratify=y
    )

    model = build_model()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "f1": round(float(f1_score(y_test, y_pred)), 4),
    }

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version": "0.1.0",
        "seed": SEED,
        "data_file": data_path.name,
        "data_sha256": file_digest(data_path)[:16],
        "n_samples": int(len(df)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "attack_share": round(float(y.mean()), 4),
        "metrics": metrics,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit-learn": sklearn.__version__,
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / MODEL_FILE)
    (out_dir / METADATA_FILE).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Обучить модель детектирования аномалий")
    parser.add_argument("--data", type=Path, default=Path("data/connections.csv"))
    parser.add_argument("--out", type=Path, default=Path("artifacts"))
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(
            f"нет файла данных: {args.data}\n"
            f"сгенерируйте его командой: python data/make_dataset.py"
        )

    metadata = train(args.data, args.out)

    print(f"модель:   {args.out / MODEL_FILE}")
    print(f"паспорт:  {args.out / METADATA_FILE}")
    for name, value in metadata["metrics"].items():
        print(f"  {name:10} {value}")


if __name__ == "__main__":
    main()
