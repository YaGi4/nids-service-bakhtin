# NIDS Service

[![CI](https://github.com/YaGi4/nids-service-bakhtin/actions/workflows/ci.yml/badge.svg)](https://github.com/YaGi4/nids-service-bakhtin/actions/workflows/ci.yml)

Сервис анализирует сетевые соединения и выявляет потенциальные угрозы. Модель Random Forest обучается на воспроизводимом учебном наборе, а FastAPI предоставляет эндпоинты `/health` и `/predict`.

Сервис детектирования аномалий сетевого трафика. Учебный сквозной проект
дисциплины «Инструментальные средства разработки инфокоммуникационных
систем с ИИ».

## Состав проекта

Репозиторий содержит модель, HTTP API, журнал предсказаний в PostgreSQL, контейнерную сборку и CI.

Для запуска требуются Docker Desktop и Docker Compose. Локальный запуск через Python описан ниже.

## Запуск стека в три команды

```bash
cp .env.example .env
docker compose up -d --build --wait
curl -s http://localhost:8000/health
```

Перед запуском замените `POSTGRES_PASSWORD` в `.env`. Сервис `db` хранит журнал в именованном томе и создаёт схему из `migrations/` на пустом томе. Сервис `api` ожидает готовности базы, а модель обучается при сборке образа. Документация API: <http://localhost:8000/docs>.

`docker compose down` сохраняет том; `docker compose down -v` удаляет его вместе с журналом. SQL-скрипты в `/docker-entrypoint-initdb.d` выполняются только при первом создании тома. Для следующих изменений схемы требуется отдельный механизм миграций.

| Переменная | Назначение |
|---|---|
| `POSTGRES_USER` | Пользователь базы |
| `POSTGRES_PASSWORD` | Пароль базы; хранить только в `.env` |
| `POSTGRES_DB` | Имя базы |
| `API_PORT` | Порт API на хосте |
| `DATABASE_URL` | Адрес PostgreSQL для локального запуска API; в Compose формируется автоматически |

Для ручного запуска базы: `docker compose up -d db`. Миграции на уже созданной базе можно применить командой `for file in migrations/*.sql; do docker compose exec -T db psql -U nids -d nids < "$file"; done` с учётом значений пользователя и базы из `.env`. Для нагрузки: `python scripts/load.py --count 500`; аналитика: `docker compose exec -T db psql -U nids -d nids < sql/analytics.sql`.

Для проверки трёх копий API без конфликта портов: `docker compose -f compose.yaml -f compose.scale.yaml up -d --scale api=3`. Этот режим снимает публикацию порта API на хосте; для внешнего доступа к нескольким копиям нужен прокси.

Отсутствие этих файлов — не недоработка шаблона, а ваша программа на семестр.

## Требования

Python 3.12 или новее. Для локального запуска нужен менеджер пакетов pip.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python data/make_dataset.py      # сгенерировать данные
python -m nids.train             # обучить модель
uvicorn nids.api:app --app-dir src --reload
```

Документация API откроется на http://localhost:8000/docs

Проверка:

```bash
curl -s localhost:8000/health
```

## Структура

```
data/make_dataset.py    генератор учебного набора соединений
src/nids/features.py    описание признаков и препроцессор
src/nids/train.py       обучение, сохранение модели и паспорта
src/nids/api.py         HTTP-сервис
src/nids/schemas.py     контракт API
tests/                  контрактные тесты и тесты признаков
artifacts/              сюда попадают model.joblib и metadata.json
```

## Тесты

```bash
pytest
```

## Непрерывная интеграция

GitHub Actions выполняет `ruff check .` и `pytest -q` для каждого Pull Request. Обязательный статус `test` защищает ветку `main`; публикация образа в GHCR начинается только после успешной проверки и слияния. Образ получает тег полного SHA коммита. Шаг Trivy останавливает job при уязвимостях HIGH или CRITICAL.

Десять тестов, проходят примерно за секунду. Модель для тестов обучается
на лету во временном каталоге — заранее запускать `train` не нужно.

## Качество модели

На сгенерированных данных (20 000 записей, seed 42):

| Метрика | Значение |
|---|---|
| accuracy | 0,92 |
| precision | 0,98 |
| recall | 0,85 |

Recall заметно ниже precision, и это не дефект. В наборе есть класс
медленных скрытных атак, которые по имеющимся признакам неотличимы от
обычного трафика — примерно их модель и пропускает. Для детектора вторжений
такое соотношение — предмет отдельного инженерного разговора, а не повод
крутить гиперпараметры.

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `MODEL_DIR` | `artifacts` | где искать `model.joblib` |

Понадобится в цикле 4, когда артефакты переедут в том контейнера.
