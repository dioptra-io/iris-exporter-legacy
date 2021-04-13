# iris-exporter
Scripts for exporting data from Iris.

```bash
poetry install
export IRIS_USERNAME=... IRIS_PASSWORD=...
poetry run python export.py --help
```

```
Usage: export.py [OPTIONS]

Options:
  --tag TAG                       Export the latest (finished) measurement
                                  with the specified tag.

  --uuid UUID                     Export the measurement with the specified
                                  UUID.

  --export-nodes / --no-export-nodes
                                  [default: True]
  --export-links / --no-export-links
                                  [default: True]
  --export-tables / --no-export-tables
                                  Dump the tables in native format (requires
                                  clickhouse-client).  [default: True]

  --database DATABASE             [default: iris]
  --host HOST                     ClickHouse host  [default: 127.0.0.1]
  --help                          Show this message and exit.
```
