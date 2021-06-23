#!/usr/bin/env bash
set -euo pipefail

docker run \
  --rm \
  --env IRIS_USERNAME=admin \
  --env IRIS_PASSWORD=randompassword \
  --network iris_default \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter export --host clickhouse --database iris --destination /exports --tag mindef.saturday.json

docker run \
  --rm \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter index --destination /exports

docker run \
  --rm \
  --volume /home/dioptra-bot/.ssh:/root/.ssh \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter sync --source /exports --destination dioptra-bot@venus.planet-lab.eu:/srv/icg-ftp/snapshots_2021
