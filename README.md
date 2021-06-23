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
cd /srv/clones/iris-exporter
dioptra git pull
docker build -t iris-exporter .
```

### Automatic

```bash
sudo crontab -e
# 0 2 * * * /srv/clones/iris-exporter/cron.sh
```

### Manual

```bash
docker run \
  --env IRIS_USERNAME=... \
  --env IRIS_PASSWORD=... \
  --network iris_default \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter export --destination /exports --host clickhouse --tag mindef.saturday.json
```

```bash
docker run \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter index --destination /exports
```

```bash
docker run \
  --volume /home/dioptra-bot/.ssh:/root/.ssh \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter sync --source /exports --destination dioptra-bot@venus.planet-lab.eu:/srv/icg-ftp/snapshots_2021
```
