#!/usr/bin/env python3
import asyncio
import json
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional

import typer
from diamond_miner.queries import GetLinks, GetNodes, results_table
from iris_client import AsyncIrisClient

README = """
# Iris data dumps

File                                                   | Description
------------------------------------------------------ | -----------
`measurement-uuid.json`                                | Measurement information (`GET /measurements/{measurement-uuid}`)
`measurement-uuid__agent-uuid.nodes`                   | Nodes (one per line)
`measurement-uuid__agent-uuid.links`                   | Links (one per line)
`results__measurement-uuid__agent-uuid.sql`            | Table schema (`SHOW CREATE TABLE ...`)
`results__measurement-uuid__agent-uuid.clickhouse.zst` | Raw ClickHouse dump (`SELECT * FROM ... INTO OUTFILE ... FORMAT Native`)

## Schema

Column              | Type          | Comments
--------------------|---------------|---------
`probe_src_addr`    | IPv6          |
`probe_dst_addr`    | IPv6          |
`probe_src_port`    | UInt16        | For ICMP the "source port" is encoded in the checksum field
`probe_dst_port`    | UInt16        |
`probe_ttl_l3`      | UInt8         | Always 0 since 08/05/2021. Removed since 04/06/2021.
`probe_ttl_l4`      | UInt8         | Renamed to `probe_ttl` since 04/06/2021.
`quoted_ttl`        | UInt8         | New since 04/06/2021.
`probe_protocol`    | UInt8         | 1 for ICMP, 58 for ICMPv6, 17 for UDP (since 30/04/2021).
`reply_src_addr`    | IPv6          |
`reply_protocol`    | UInt8         | 1 for ICMP, 58 for ICMPv6
`reply_icmp_type`   | UInt8         | 11 for ICMP Time Exceed, 3 for ICMPv6 Time Exceeded
`reply_icmp_code`   | UInt8         |
`reply_ttl`         | UInt8         |
`reply_size`        | UInt16        |
`reply_mpls_labels` | Array(UInt32) |
`rtt`               | Float64       | Float32 since 16/05/2021
`round`             | UInt8         |

## Changelog

### 04/06/2021

The `probe_ttl_l4` column has been renamed to `probe_ttl` and the `probe_ttl_l3` column has been removed.
We now store `quoted_ttl`, the TTL of the probe packet as seen by the host who generated the ICMP reply.

### 16/05/2021

The RTT column precision is reduced to 32 bits as its maximum value is 6553.5 ms.

### 08/05/2021

We now encode `checkum(caracal_id, probe_dst_addr, probe_src_port, probe_ttl_l4)` in the IP header ID field, instead of the probe TTL (previously, `probe_ttl_l3`).
This allows us to drop invalid replies. As such the number of anomalous values in the database should be greatly reduced (TTLs > 32, probe_src_port < 24000, private probe_dst_addr, etc.).

### 30/04/2021

The `probe_protocol` column is added, to allow for multi-protocol measurements.
"""

IRIS_URL = "https://api.iris.dioptra.io"

app = typer.Typer()


def run_in_loop(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


async def clickhouse(
    host: str, database: str, user: str, password: str, statement: str
) -> None:
    cmd = f'clickhouse-client --host={host} --database={database} --user={user} --password={password} --query="{statement}"'
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()


async def wc(file: Path) -> int:
    logging.info("wc file=%s", file)
    proc = await asyncio.create_subprocess_shell(
        f"wc -l {file}", stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return int(stdout.split()[0])


async def do_export_links(
    host: str,
    database: str,
    user: str,
    password: str,
    destination: Path,
    measurement_id: str,
) -> None:
    logging.info(
        "export_links host=%s database=%s destination=%s measurement_id=%s",
        host,
        database,
        destination,
        measurement_id,
    )
    file = (destination / measurement_id).with_suffix(".links")
    query = f"""
    {GetLinks().statement(measurement_id)}
    INTO OUTFILE '{file}'
    FORMAT CSV
    """
    if not file.exists():
        await clickhouse(host, database, user, password, query)


async def do_export_nodes(
    host: str,
    database: str,
    user: str,
    password: str,
    destination: Path,
    measurement_id: str,
) -> None:
    logging.info(
        "export_nodes host=%s database=%s destination=%s measurement_id=%s",
        host,
        database,
        destination,
        measurement_id,
    )
    file = (destination / measurement_id).with_suffix(".nodes")
    query = f"""
    {GetNodes().statement(measurement_id)}
    INTO OUTFILE '{file}'
    FORMAT CSV
    """
    if not file.exists():
        await clickhouse(host, database, user, password, query)


async def do_export_schema(
    host: str,
    database: str,
    user: str,
    password: str,
    destination: Path,
    measurement_id: str,
) -> None:
    logging.info(
        "export_schema host=%s database=%s destination=%s measurement_id=%s",
        host,
        database,
        destination,
        measurement_id,
    )
    file = (destination / results_table(measurement_id)).with_suffix(".sql")
    query = f"""
    SHOW CREATE TABLE {results_table(measurement_id)}
    INTO OUTFILE '{file}'
    FORMAT TabSeparatedRaw
    """
    if not file.exists():
        await clickhouse(host, database, user, password, query)


async def do_export_table(
    host: str,
    database: str,
    user: str,
    password: str,
    destination: Path,
    measurement_id: str,
) -> None:
    logging.info(
        "export_table host=%s database=%s destination=%s measurement_id=%s",
        host,
        database,
        destination,
        measurement_id,
    )
    file = (destination / results_table(measurement_id)).with_suffix(".clickhouse.zst")
    query = f"""
    SELECT * FROM {results_table(measurement_id)}
    INTO OUTFILE '{file}'
    FORMAT Native
    """
    if not file.exists():
        await clickhouse(host, database, user, password, query)


async def find_uuid(client: AsyncIrisClient, tag: str) -> str:
    logging.info("Listing measurements with tag %s...", tag)
    measurements = await client.all(
        "/measurements/", params=dict(only_mine=False, tag=tag)
    )
    res = [x for x in measurements if x.get("end_time")]
    return sorted(res, key=end_time)[-1]["uuid"]


def start_time(measurement: dict) -> datetime:
    if s := measurement["start_time"]:
        return datetime.fromisoformat(s).replace(microsecond=0)


def end_time(measurement: dict) -> datetime:
    if s := measurement["end_time"]:
        return datetime.fromisoformat(s).replace(microsecond=0)


@app.command()
@run_in_loop
async def export(
    tag: Optional[str] = typer.Option(
        None,
        metavar="TAG",
        help="Export the latest (finished) measurement with the specified tag.",
    ),
    uuid: Optional[str] = typer.Option(
        None, metavar="UUID", help="Export the measurement with the specified UUID."
    ),
    export_links: bool = typer.Option(
        True,
        "--export-links",
        "--no-export-links",
        help="Export links (default: enabled)."
    ),
    export_nodes: bool = typer.Option(
        True,
        "--export-nodes",
        "--no-export-nodes",
        help="Export nodes (default: enabled)."
    ),
    export_tables: bool = typer.Option(
        True,
        "--export-tables",
        "--no-export-tables",
        help="Export tables (default: enabled)."
    ),
    host: str = typer.Option("localhost", metavar="HOST"),
    database: str = typer.Option("default", metavar="DATABASE"),
    user: str = typer.Option("default", metavar="USER"),
    password: str = typer.Option("", metavar="PASSWORD"),
    destination: Path = typer.Option("exports", metavar="DESTINATION"),
):
    assert tag or uuid, "One of --tag or --uuid must be specified."
    logging.basicConfig(level=logging.INFO)

    async with AsyncIrisClient() as client:
        if tag:
            uuid = await find_uuid(client, tag)

        logging.info("Getting measurement information...")
        measurement = (await client.get(f"/measurements/{uuid}")).json()
        Path(f"{destination}/{uuid}.json").write_text(json.dumps(measurement, indent=4))

        measurement_ids = [
            f"{uuid}__{agent['agent_uuid']}" for agent in measurement["agents"]
        ]
        futures = []

        if export_links:
            for measurement_id in measurement_ids:
                futures.append(
                    do_export_links(
                        host, database, user, password, destination, measurement_id
                    )
                )

        if export_nodes:
            for measurement_id in measurement_ids:
                futures.append(
                    do_export_nodes(
                        host, database, user, password, destination, measurement_id
                    )
                )

        if export_tables:
            for measurement_id in measurement_ids:
                futures.append(
                    do_export_schema(
                        host, database, user, password, destination, measurement_id
                    )
                )
                futures.append(
                    do_export_table(
                        host, database, user, password, destination, measurement_id
                    )
                )

        await asyncio.gather(*futures)


@app.command()
@run_in_loop
async def index(destination: Path = typer.Option("exports", metavar="DESTINATION")):
    measurements = []

    for file in destination.glob("*.json"):
        meta = json.loads(file.read_text())
        measurement_uuid = meta["uuid"]
        agents = {}

        for file_ in destination.glob(f"{measurement_uuid}*.nodes"):
            agent_uuid = file_.stem.split("__")[1]
            agents.setdefault(agent_uuid, {})["nodes"] = await wc(file_)

        for file_ in destination.glob(f"{measurement_uuid}*.links"):
            agent_uuid = file_.stem.split("__")[1]
            agents.setdefault(agent_uuid, {})["links"] = await wc(file_)

        measurements.append({"meta": meta, "agents": agents})

    measurements = sorted(
        measurements, key=lambda x: datetime.fromisoformat(x["meta"]["start_time"])
    )

    md = ""
    template = "{:<12} | {:<10} | {:<20} | {:<20} | {:<16} | {:<10} | {:<10}"
    md += template.format(
        "Measurement", "Agent", "Start", "End", "Duration", "Nodes", "Links"
    )
    md += "\n"
    md += template.format("--", "--", "--", "--", "--", "--", "--") + "\n"
    for measurement in measurements:
        for agent_uuid, agent in measurement["agents"].items():
            md += template.format(
                measurement["meta"]["uuid"].split("-")[0],
                agent_uuid.split("-")[0],
                str(start_time(measurement["meta"])),
                str(end_time(measurement["meta"])),
                str(end_time(measurement["meta"]) - start_time(measurement["meta"])),
                agent["nodes"],
                agent["links"],
            )
            md += "\n"

    (destination / "README.md").write_text(README)
    (destination / "INDEX.md").write_text(md)
    print(md)


if __name__ == "__main__":
    app()
