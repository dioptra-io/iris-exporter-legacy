FROM python:3.9

RUN pip install --no-cache-dir --upgrade poetry
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY diamond-miner/ diamond-miner/
COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml

RUN poetry install --no-dev --no-root \
    && rm -rf /root/.cache/*

COPY scripts/ scripts/
