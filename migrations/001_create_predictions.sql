CREATE TABLE IF NOT EXISTS predictions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    model_version text NOT NULL,
    protocol_type text NOT NULL,
    service text NOT NULL,
    flag text NOT NULL,
    duration double precision NOT NULL,
    src_bytes bigint NOT NULL,
    dst_bytes bigint NOT NULL,
    prediction text NOT NULL CHECK (prediction IN ('normal', 'attack')),
    probability double precision NOT NULL CHECK (probability BETWEEN 0 AND 1),
    response_ms double precision NOT NULL CHECK (response_ms >= 0)
);
