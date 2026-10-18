"""Тесты подготовки признаков."""

from __future__ import annotations

import pandas as pd
import pytest

from nids.features import ALL_FEATURES, split_xy, to_frame


def test_split_xy_returns_expected_shape(dataset):
    X, y = split_xy(dataset)

    assert list(X.columns) == ALL_FEATURES
    assert len(X) == len(dataset)
    assert set(y.unique()) <= {0, 1}


def test_split_xy_rejects_missing_columns(dataset):
    broken = dataset.drop(columns=["src_bytes"])

    with pytest.raises(ValueError, match="src_bytes"):
        split_xy(broken)


def test_to_frame_preserves_feature_order(normal_connection):
    frame = to_frame(normal_connection)

    assert list(frame.columns) == ALL_FEATURES
    assert len(frame) == 1


def test_dataset_generation_is_deterministic():
    """Один seed -- один и тот же набор. На этом держится сравнимость метрик."""
    from make_dataset import generate

    first = generate(rows=500)
    second = generate(rows=500)

    pd.testing.assert_frame_equal(first, second)
