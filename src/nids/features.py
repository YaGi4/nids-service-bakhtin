"""Описание признаков и сборка препроцессора.

Здесь один принцип, ради которого этот модуль вообще отделён от train.py:
преобразование признаков при обучении и при предсказании должно быть
буквально одним и тем же объектом. Если их два -- рано или поздно они
разойдутся, и сервис начнёт отвечать уверенную чушь, не падая.

Поэтому препроцессор не применяется отдельно, а входит в Pipeline, который
целиком сохраняется в artifacts/model.joblib.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATEGORICAL_FEATURES = ["protocol_type", "service", "flag"]

NUMERIC_FEATURES = [
    "duration",
    "src_bytes",
    "dst_bytes",
    "count",
    "srv_count",
    "serror_rate",
    "rerror_rate",
    "same_srv_rate",
    "diff_srv_rate",
    "dst_host_count",
    "dst_host_srv_count",
]

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

LABEL_COLUMN = "label"
POSITIVE_LABEL = "attack"


def build_preprocessor() -> ColumnTransformer:
    """Категориальные -- в one-hot, числовые -- к нулевому среднему.

    handle_unknown="ignore" обязателен: в проде обязательно приедет service,
    которого не было в обучающей выборке. Без этого сервис упадёт на первом
    же незнакомом значении вместо того, чтобы дать предсказание.
    """
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            ("num", StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder="drop",
    )


def split_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Разделить таблицу на признаки и бинарную целевую переменную."""
    missing = [c for c in ALL_FEATURES + [LABEL_COLUMN] if c not in df.columns]
    if missing:
        raise ValueError(f"в данных нет колонок: {', '.join(missing)}")

    X = df[ALL_FEATURES].copy()
    y = (df[LABEL_COLUMN] == POSITIVE_LABEL).astype(int)
    return X, y


def to_frame(record: dict) -> pd.DataFrame:
    """Один запрос к API -> таблица из одной строки в порядке ALL_FEATURES."""
    return pd.DataFrame([{name: record[name] for name in ALL_FEATURES}])
