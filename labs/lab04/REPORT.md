# Лабораторная работа № 4. PostgreSQL и журнал предсказаний

## Цель
Сохранять предсказания сервиса в PostgreSQL и анализировать журнал SQL-запросами, сохраняя доступность API при сбое базы.

## Ход работы
В `pyproject.toml` добавлена зависимость `psycopg[binary]`, создан модуль `src/nids/db.py`. Параметр `DATABASE_URL` считывается из окружения. Подключение создаётся для записи результата; при ошибке запись журналируется, а предсказание остаётся доступным. Для задачи обнаружения атак важнее своевременный ответ. В системе, где факт записи обязателен юридически, приоритет мог бы быть обратным.

Миграция `001_create_predictions.sql` создаёт журнал с `created_at timestamptz`, версией модели, признаками, классом, вероятностью и временем ответа. `timestamptz` фиксирует абсолютный момент времени и корректно переводится между часовыми поясами. Миграция `002_index_created_at.sql` добавляет индекс по времени.

Проверено на 500 HTTP-запросах (`python scripts/load.py --count 500`). Запросы лежат в `sql/analytics.sql`; ниже приведены все шесть вместе с результатами.

```sql
SELECT count(*) AS total, round(100.0 * count(*) FILTER (WHERE prediction = 'attack') / nullif(count(*), 0), 2) AS attack_percent FROM predictions;
-- total=500, attack_percent=42.20
```
Доля срабатываний модели в тестовом потоке составила 42,20 %.

```sql
SELECT protocol_type, count(*) FILTER (WHERE prediction = 'attack') AS attacks, count(*) FILTER (WHERE prediction = 'normal') AS normals FROM predictions GROUP BY protocol_type ORDER BY protocol_type;
-- icmp: 29/8; tcp: 162/233; udp: 20/48 (атаки/норма)
```
Наибольшее абсолютное число срабатываний пришлось на TCP из-за его преобладания в потоке.

```sql
SELECT date_trunc('hour', created_at) AS hour, count(*) AS requests FROM predictions WHERE created_at >= now() - interval '1 day' GROUP BY hour ORDER BY hour;
-- 2026-10-18 16:00:00+00: 500
```
Все тестовые запросы попали в один час UTC.

```sql
SELECT prediction, round(avg(probability)::numeric, 4) AS mean_probability, min(probability), max(probability) FROM predictions GROUP BY prediction ORDER BY prediction;
-- attack: 0.9614, 0.5008, 1.0000
-- normal: 0.1275, 0.0498, 0.4995
```
Средняя вероятность для класса attack высокая, но есть результаты около порога 0,5.

```sql
SELECT service, count(*) AS total, round(100.0 * count(*) FILTER (WHERE prediction = 'attack') / count(*), 2) AS attack_percent FROM predictions GROUP BY service HAVING count(*) >= 10 ORDER BY attack_percent DESC LIMIT 5;
-- telnet 43 88.37%; ssh 51 60.78%; ftp 58 56.90%; other 64 53.13%; smtp 52 28.85%
```
У telnet наибольшая доля срабатываний среди сервисов с минимум десятью наблюдениями.

```sql
SELECT percentile_cont(ARRAY[0.50, 0.95, 0.99]) WITHIN GROUP (ORDER BY response_ms) AS response_ms_percentiles FROM predictions;
-- p50=57.04 мс; p95=63.79 мс; p99=102.46 мс
```
99 % измеренных ответов были быстрее примерно 102,46 мс; измерение сделано до записи в БД.

Для проверки индекса он был удалён и восстановлен из миграции. Фильтр охватывает все 500 строк, поэтому планировщик обоснованно выбрал полное сканирование в обоих случаях:

```text
До индекса: Seq Scan on predictions (actual time=0.009..0.126 rows=500); Execution Time: 0.195 ms
После индекса: Seq Scan on predictions (actual time=0.008..0.117 rows=500); Execution Time: 0.185 ms
```

При остановленной БД `/predict` вернул HTTP 200 и предсказание `attack`, а в логе API появилось `Не удалось записать предсказание в PostgreSQL` и `psycopg.OperationalError: failed to resolve host 'db'`. Это подтверждает отсутствие жёсткой зависимости ответа от журнала.

## Ответы на контрольные вопросы
1. `WHERE` отбирает строки до группировки, `HAVING` — группы после неё. Условие `HAVING count(*) >= 10` нельзя заменить обычным `WHERE` с тем же агрегатом.
2. Именованный том сохраняет данные при удалении контейнера; без постоянного тома новый контейнер получит пустую БД.
3. Переменные окружения позволяют менять адрес и секрет без изменения исходного кода и не публиковать пароль в Git.
4. Версия модели позволяет связать строку журнала с конкретным алгоритмом и сравнивать поведение версий.
5. `EXPLAIN ANALYZE` показывает выбранный план и фактическое время. `Seq Scan` читает таблицу последовательно, `Index Scan` использует индекс для отбора строк.
6. Индекс требует хранения и обновления; если выборка охватывает почти всю маленькую таблицу, последовательное чтение дешевле.
7. В журнале нет истинных меток классов; для accuracy нужна разметка фактических исходов и сопоставление с предсказаниями.
8. Миграция версионируется, повторяется в других окружениях и поддаётся проверке; ручной `ALTER TABLE` не оставляет воспроизводимой процедуры.

## Возникшие затруднения и устранение
При остановке контейнера имя `db` перестало разрешаться внутри сети Compose. Исключение `psycopg.OperationalError` перехвачено в функции записи и оставлено в логе; API продолжил отвечать. Индекс не изменил тип плана на выборке из 500 строк, что объясняется малым объёмом и широким фильтром.
