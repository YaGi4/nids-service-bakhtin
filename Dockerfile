FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
RUN python -c 'import tomllib; p=tomllib.load(open("pyproject.toml", "rb")); print("\n".join(p["project"]["dependencies"]))' > /tmp/requirements.txt \
    && pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt
COPY src ./src
RUN pip install --no-cache-dir --no-deps --prefix=/install .

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY data/make_dataset.py ./data/make_dataset.py
RUN python data/make_dataset.py && python -m nids.train \
    && rm data/connections.csv \
    && useradd --create-home --uid 10001 nids \
    && chown -R nids:nids /app
USER nids
EXPOSE 8000
CMD ["uvicorn", "nids.api:app", "--host", "0.0.0.0", "--port", "8000"]
