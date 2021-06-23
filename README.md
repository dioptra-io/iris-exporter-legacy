# iris-exporter
Scripts for exporting data from Iris.

```bash
docker build -t iris-exporter .
docker run -e IRIS_USERNAME=... -e IRIS_PASSWORD=... iris-exporter scripts/export.py --help
```

```bash
docker run \
  -e IRIS_USERNAME=... \
  -e IRIS_PASSWORD=... \
  -v /srv/clones/iris-exporter/exports:/exports \
  --network iris_default \
  iris-exporter scripts/export.py --destination /exports --host clickhouse --tag mindef.saturday.json
```
