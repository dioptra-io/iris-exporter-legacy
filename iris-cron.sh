#!/usr/bin/env bash
set -euo pipefail

docker run \
  --env IRIS_USERNAME=admin \
  --env IRIS_PASSWORD=randompassword \
  --network iris_default \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter export --destination /exports --host clickhouse --tag mindef.saturday.json

docker run \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter index --destination /exports

docker run \
  --volume /home/dioptra-bot/.ssh:/root/.ssh \
  --volume /srv/clones/iris-exporter/exports:/exports \
  iris-exporter sync --source /exports --destination dioptra-bot@venus.planet-lab.eu:/srv/icg-ftp/snapshots_2021
