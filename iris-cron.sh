#!/usr/bin/env bash
set -euo pipefail

LOCAL=/srv/clones/iris-exporter/exports
REMOTE=dioptra-bot@venus.planet-lab.eu:/srv/icg-ftp/snapshots_2021

docker run \
  --rm \
  --env IRIS_USERNAME=admin \
  --env IRIS_PASSWORD=randompassword \
  --network iris_default \
  --volume "${LOCAL}":/exports \
  iris-exporter export --host clickhouse --database iris --destination /exports --tag mindef.saturday.json

docker run \
  --rm \
  --volume "${LOCAL}":/exports \
  iris-exporter index --destination /exports

rsync --rsh='ssh -i /home/dioptra-bot/.ssh/id_rsa' --archive --delete --progress "${LOCAL}/" "${REMOTE}/"
