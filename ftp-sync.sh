#!/bin/bash
set -euo pipefail

src=exports/
dst=venus.planet-lab.eu:/srv/icg-ftp/snapshots_2021

find "${src}" -name '*.clickhouse' -exec lz4 -f --rm "{}" \;
rsync --archive --delete --progress "${src}" "${dst}"
