-- 1. Число предсказаний и доля атак
SELECT count(*) AS total, round(100.0 * count(*) FILTER (WHERE prediction = 'attack') / nullif(count(*), 0), 2) AS attack_percent FROM predictions;

-- 2. Классы по протоколу
SELECT protocol_type, count(*) FILTER (WHERE prediction = 'attack') AS attacks, count(*) FILTER (WHERE prediction = 'normal') AS normals FROM predictions GROUP BY protocol_type ORDER BY protocol_type;

-- 3. Предсказания по часам за сутки
SELECT date_trunc('hour', created_at) AS hour, count(*) AS requests FROM predictions WHERE created_at >= now() - interval '1 day' GROUP BY hour ORDER BY hour;

-- 4. Вероятность по классам
SELECT prediction, round(avg(probability)::numeric, 4) AS mean_probability, min(probability), max(probability) FROM predictions GROUP BY prediction ORDER BY prediction;

-- 5. Сервисы с долей атак при 10 и более запросах
SELECT service, count(*) AS total, round(100.0 * count(*) FILTER (WHERE prediction = 'attack') / count(*), 2) AS attack_percent FROM predictions GROUP BY service HAVING count(*) >= 10 ORDER BY attack_percent DESC LIMIT 5;

-- 6. Перцентили времени ответа
SELECT percentile_cont(ARRAY[0.50, 0.95, 0.99]) WITHIN GROUP (ORDER BY response_ms) AS response_ms_percentiles FROM predictions;
