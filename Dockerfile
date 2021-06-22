FROM python:3.9

RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv E0C56BD4 \
    && echo "deb https://repo.clickhouse.tech/deb/stable/ main/" > \
        /etc/apt/sources.list.d/clickhouse.list \
    && apt-get update \
    && apt-get install -y -q --no-install-recommends \
        clickhouse-client rsync zstd \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade poetry
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY diamond-miner/ diamond-miner/
COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml

RUN poetry install --no-dev --no-root \
    && rm -rf /root/.cache/*

COPY scripts/ scripts/
