FROM python:3.10

# Install base deps and ClickHouse key securely
# Install base deps and ClickHouse key securely
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget gpg ca-certificates \
    && mkdir -p /etc/apt/keyrings \
    && wget -qO- https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key \
        | gpg --dearmor -o /etc/apt/keyrings/clickhouse-keyring.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/clickhouse-keyring.gpg] https://packages.clickhouse.com/deb stable main" \
        > /etc/apt/sources.list.d/clickhouse.list

# Install ClickHouse client and rsync
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        clickhouse-client rsync \
    && rm -rf /var/lib/apt/lists/*

# Install ClickHouse client and rsync
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        clickhouse-client rsync \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade poetry
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml

RUN poetry install --without dev --no-root \
    && rm -rf /root/.cache/*

COPY iris_exporter.py iris_exporter.py

ENTRYPOINT ["./iris_exporter.py"]
