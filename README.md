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

### Manual

```bash
LOCAL=/srv/clones/iris-exporter/exports
REMOTE=dioptra-bot@venus.planet-lab.eu:/srv/icg-ftp/snapshots_2021

docker run \
  --rm \
  --env IRIS_USERNAME=admin \
  --env IRIS_PASSWORD=randompassword \
  --network iris-production_default \
  --volume "${LOCAL}":/exports \
  iris-exporter export --host clickhouse --database iris --destination /exports --tag exhaustive.saturday.json

docker run \
  --rm \
  --volume "${LOCAL}":/exports \
  iris-exporter index --destination /exports

rsync --rsh='ssh -i /home/dioptra-bot/.ssh/id_rsa' --archive --delete --progress "${LOCAL}/" "${REMOTE}/"
```
