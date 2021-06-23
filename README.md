# iris-exporter

Export Iris data.

## Installation

### Docker 🐳

```bash
docker build -t iris-exporter .
docker run iris-exporter --help
```

### Poetry 🐍

```bash
poetry install
poetry run iris-exporter --help
```

## Usage

```bash
docker run \
  -e IRIS_USERNAME=... \
  -e IRIS_PASSWORD=... \
  -v /srv/clones/iris-exporter/exports:/exports \
  --network iris_default \
  iris-exporter export --destination /exports --host clickhouse --tag mindef.saturday.json
```

```bash
docker run \
  -e IRIS_USERNAME=... \
  -e IRIS_PASSWORD=... \
  -v /srv/clones/iris-exporter/exports:/exports \
  --network iris_default \
  iris-exporter index --destination /exports
```
