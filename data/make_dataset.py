"""Генератор учебного набора данных о сетевых соединениях.

Структура повторяет NSL-KDD: те же имена признаков и та же постановка --
бинарная классификация «нормальное соединение / атака».

Данные синтетические, но не случайный шум: каждый класс атаки имеет свой
профиль признаков, поэтому модель учится осмысленным закономерностям,
а не запоминает шум.

Генерация детерминирована: при одном и том же SEED файл побайтово одинаков
у всех. Это сознательно -- метрики у всех студентов сравнимы.

Запуск:
    python data/make_dataset.py
    python data/make_dataset.py --rows 50000 --out data/big.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260901
DEFAULT_ROWS = 20_000
DEFAULT_OUT = Path(__file__).parent / "connections.csv"

SERVICES = ["http", "smtp", "dns", "ftp", "ssh", "telnet", "other"]

COLUMNS = [
    "duration",
    "protocol_type",
    "service",
    "flag",
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
    "label",
]


def _normal(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """Обычный трафик: сессия завершена, ошибок мало, сервис один и тот же."""
    return pd.DataFrame(
        {
            "duration": rng.exponential(scale=12.0, size=n).round(2),
            "protocol_type": rng.choice(["tcp", "udp", "icmp"], size=n, p=[0.8, 0.17, 0.03]),
            "service": rng.choice(SERVICES, size=n, p=[0.45, 0.1, 0.15, 0.08, 0.1, 0.02, 0.1]),
            "flag": rng.choice(["SF", "S0", "REJ"], size=n, p=[0.93, 0.04, 0.03]),
            "src_bytes": rng.lognormal(mean=5.4, sigma=1.3, size=n).astype(int),
            "dst_bytes": rng.lognormal(mean=6.6, sigma=1.6, size=n).astype(int),
            "count": rng.integers(1, 12, size=n),
            "srv_count": rng.integers(1, 10, size=n),
            "serror_rate": rng.beta(0.4, 14, size=n).round(3),
            "rerror_rate": rng.beta(0.4, 14, size=n).round(3),
            "same_srv_rate": rng.beta(9, 1.2, size=n).round(3),
            "diff_srv_rate": rng.beta(1.0, 9, size=n).round(3),
            "dst_host_count": rng.integers(1, 60, size=n),
            "dst_host_srv_count": rng.integers(1, 55, size=n),
            "label": "normal",
        }
    )


def _dos(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """SYN flood: соединение не установлено, ответных байт нет, ошибок много."""
    return pd.DataFrame(
        {
            "duration": np.zeros(n),
            "protocol_type": rng.choice(["tcp", "icmp"], size=n, p=[0.85, 0.15]),
            "service": rng.choice(SERVICES, size=n, p=[0.5, 0.05, 0.05, 0.05, 0.05, 0.1, 0.2]),
            "flag": rng.choice(["S0", "REJ", "RSTO"], size=n, p=[0.78, 0.15, 0.07]),
            "src_bytes": rng.integers(0, 60, size=n),
            "dst_bytes": np.zeros(n, dtype=int),
            "count": rng.integers(150, 511, size=n),
            "srv_count": rng.integers(150, 511, size=n),
            "serror_rate": rng.beta(14, 0.5, size=n).round(3),
            "rerror_rate": rng.beta(1.2, 6, size=n).round(3),
            "same_srv_rate": rng.beta(11, 1.0, size=n).round(3),
            "diff_srv_rate": rng.beta(0.6, 12, size=n).round(3),
            "dst_host_count": rng.integers(200, 256, size=n),
            "dst_host_srv_count": rng.integers(200, 256, size=n),
            "label": "attack",
        }
    )


def _probe(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """Сканирование портов: много разных сервисов, отказы, короткие сессии."""
    return pd.DataFrame(
        {
            "duration": rng.exponential(scale=0.6, size=n).round(2),
            "protocol_type": rng.choice(["tcp", "udp", "icmp"], size=n, p=[0.6, 0.25, 0.15]),
            "service": rng.choice(SERVICES, size=n, p=[0.1, 0.1, 0.1, 0.15, 0.15, 0.15, 0.25]),
            "flag": rng.choice(["REJ", "S0", "SF"], size=n, p=[0.6, 0.25, 0.15]),
            "src_bytes": rng.integers(0, 300, size=n),
            "dst_bytes": rng.integers(0, 120, size=n),
            "count": rng.integers(20, 180, size=n),
            "srv_count": rng.integers(1, 20, size=n),
            "serror_rate": rng.beta(1.2, 5, size=n).round(3),
            "rerror_rate": rng.beta(9, 1.2, size=n).round(3),
            "same_srv_rate": rng.beta(1.0, 10, size=n).round(3),
            "diff_srv_rate": rng.beta(9, 1.2, size=n).round(3),
            "dst_host_count": rng.integers(100, 256, size=n),
            "dst_host_srv_count": rng.integers(1, 30, size=n),
            "label": "attack",
        }
    )


def _r2l(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """Подбор пароля: сессия устанавливается, но трафик аномально мал.

    Самый трудный класс -- внешне похож на нормальный.
    """
    return pd.DataFrame(
        {
            "duration": rng.exponential(scale=30.0, size=n).round(2),
            "protocol_type": np.full(n, "tcp"),
            "service": rng.choice(["ftp", "ssh", "telnet", "smtp"], size=n, p=[0.3, 0.3, 0.3, 0.1]),
            "flag": rng.choice(["SF", "RSTO"], size=n, p=[0.85, 0.15]),
            "src_bytes": rng.integers(80, 900, size=n),
            "dst_bytes": rng.integers(10, 400, size=n),
            "count": rng.integers(1, 9, size=n),
            "srv_count": rng.integers(1, 9, size=n),
            "serror_rate": rng.beta(0.5, 12, size=n).round(3),
            "rerror_rate": rng.beta(0.5, 12, size=n).round(3),
            "same_srv_rate": rng.beta(7, 1.5, size=n).round(3),
            "diff_srv_rate": rng.beta(1.2, 7, size=n).round(3),
            "dst_host_count": rng.integers(1, 40, size=n),
            "dst_host_srv_count": rng.integers(1, 35, size=n),
            "label": "attack",
        }
    )


def _stealth(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """Медленная скрытная атака: по признакам неотличима от обычного трафика.

    Этот класс добавлен намеренно. Без него задача решается почти идеально,
    и у студента складывается ложное впечатление, что детектирование атак --
    простая задача. В реальности именно такие соединения и пропускают:
    информации в признаках физически не хватает, чтобы отличить их от нормы.

    Он же задаёт потолок качества: выше примерно 0,95 по F1 на этих данных
    не прыгнуть никакой моделью, и это правильный ориентир для порога в CI.
    """
    df = _normal(rng, n)
    df["duration"] = (df["duration"] * rng.uniform(1.0, 1.6, size=n)).round(2)
    df["src_bytes"] = (df["src_bytes"] * rng.uniform(0.8, 1.2, size=n)).astype(int)
    df["label"] = "attack"
    return df


def generate(rows: int = DEFAULT_ROWS, seed: int = SEED) -> pd.DataFrame:
    """Собрать набор: 52 % нормального трафика и 48 % атак четырёх типов."""
    rng = np.random.default_rng(seed)

    n_normal = int(rows * 0.52)
    n_dos = int(rows * 0.20)
    n_probe = int(rows * 0.13)
    n_stealth = int(rows * 0.07)
    n_r2l = rows - n_normal - n_dos - n_probe - n_stealth

    df = pd.concat(
        [
            _normal(rng, n_normal),
            _dos(rng, n_dos),
            _probe(rng, n_probe),
            _r2l(rng, n_r2l),
            _stealth(rng, n_stealth),
        ],
        ignore_index=True,
    )

    # Перемешать, иначе первые 55 % файла -- сплошь normal.
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df[COLUMNS]


def main() -> None:
    parser = argparse.ArgumentParser(description="Сгенерировать учебный набор соединений")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help="число записей")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="куда записать CSV")
    parser.add_argument("--seed", type=int, default=SEED, help="зерно генератора")
    args = parser.parse_args()

    df = generate(rows=args.rows, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)

    size_mb = args.out.stat().st_size / 1024 / 1024
    share = (df["label"] == "attack").mean()
    print(f"записано: {args.out} ({size_mb:.1f} МБ)")
    print(f"строк: {len(df)}, доля атак: {share:.1%}")


if __name__ == "__main__":
    main()
