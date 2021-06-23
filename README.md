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
# 0 2 * * 1 /srv/clones/iris-exporter/iris-cron.sh
```

### Manual

See [iris-cron.sh](/iris-cron.sh)
