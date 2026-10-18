"""Отправить случайные строки CSV в API и заполнить журнал предсказаний."""

from __future__ import annotations

import argparse
import random

import httpx
import pandas as pd

from nids.features import ALL_FEATURES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/connections.csv")
    parser.add_argument("--url", default="http://localhost:8000/predict")
    parser.add_argument("--count", type=int, default=500)
    args = parser.parse_args()
    rows = pd.read_csv(args.data)[ALL_FEATURES].to_dict("records")
    rng = random.Random(42)
    with httpx.Client(timeout=10) as client:
        for _ in range(args.count):
            response = client.post(args.url, json=rng.choice(rows))
            response.raise_for_status()
    print(f"Успешно отправлено: {args.count}")


if __name__ == "__main__":
    main()
