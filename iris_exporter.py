#!/usr/bin/env python3
import asyncio
import json
import logging
import os
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional

import httpx
import typer
from diamond_miner.queries import GetLinks, GetNodes, results_table

IRIS_URL = "https://iris.dioptra.io/api"

app = typer.Typer()


def run_in_loop(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


async def clickhouse(host: str, database: str, statement: str) -> None:
    cmd = f'clickhouse-client --host={host} --database={database} --query="{statement}"'
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()


async def wc(file: Path) -> int:
    logging.info("wc file=%s", file)
    proc = await asyncio.create_subprocess_shell(
        f"wc -l {file}", stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return int(stdout.split()[0])


async def zstd(file: Path) -> None:
    logging.info("zstd file=%s", file)
    proc = await asyncio.create_subprocess_shell(f"zstd -T0 --fast=1 -f --rm {file}")
    await proc.communicate()


async def do_export_links(
    host: str, database: str, destination: Path, measurement_id: str
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
        await clickhouse(host, database, query)


async def do_export_nodes(
    host: str, database: str, destination: Path, measurement_id: str
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
        await clickhouse(host, database, query)


async def do_export_table(
    host: str, database: str, destination: Path, measurement_id: str
) -> None:
    logging.info(
        "export_table host=%s database=%s destination=%s measurement_id=%s",
        host,
        database,
        destination,
        measurement_id,
    )
    file = (destination / results_table(measurement_id)).with_suffix(".clickhouse")
    query = f"""
    SELECT * FROM {results_table(measurement_id)}
    INTO OUTFILE '{file}'
    FORMAT Native
    """
    if not file.with_suffix(".clickhouse.zst").exists():
        await clickhouse(host, database, query)
        await zstd(file)


async def request(method, path, **kwargs):
    async with httpx.AsyncClient() as client:
        req = await client.request(method, IRIS_URL + path, **kwargs)
        req.raise_for_status()
        return req.json()


async def find_uuid(headers: dict, tag: str) -> str:
    logging.info(f"Listing measurements with tag {tag}...")
    res = await request(
        "GET",
        "/measurements/",
        params={"limit": 200, "tag": tag},
        headers=headers,
    )
    res = [x for x in res["results"] if x.get("end_time")]
    return sorted(res, key=end_time)[-1]["uuid"]


def start_time(measurement: dict) -> datetime:
    return datetime.fromisoformat(measurement["start_time"])


def end_time(measurement: dict) -> datetime:
    return datetime.fromisoformat(measurement["end_time"])


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
    export_links: bool = typer.Option(True, is_flag=True),
    export_nodes: bool = typer.Option(True, is_flag=True),
    export_tables: bool = typer.Option(True, is_flag=True),
    host: str = typer.Option("localhost", metavar="HOST"),
    database: str = typer.Option("default", metavar="DATABASE"),
    destination: Path = typer.Option("exports", metavar="DESTINATION"),
):
    assert tag or uuid, "One of --tag or --uuid must be specified."
    logging.basicConfig(level=logging.INFO)

    logging.info("Authenticating...")
    data = {
        "username": os.environ["IRIS_USERNAME"],
        "password": os.environ["IRIS_PASSWORD"],
    }
    res = await request("POST", "/profile/token", data=data)
    headers = {"Authorization": f"Bearer {res['access_token']}"}

    if tag:
        uuid = await find_uuid(headers, tag)

    logging.info("Getting measurement information...")
    info = await request("GET", f"/measurements/{uuid}", headers=headers)
    Path(f"{destination}/{uuid}.json").write_text(json.dumps(info, indent=4))

    measurement_ids = [f"{uuid}__{agent['uuid']}" for agent in info["agents"]]
    futures = []

    if export_links:
        for measurement_id in measurement_ids:
            futures.append(do_export_links(host, database, destination, measurement_id))

    if export_nodes:
        for measurement_id in measurement_ids:
            futures.append(do_export_nodes(host, database, destination, measurement_id))

    if export_tables:
        for measurement_id in measurement_ids:
            futures.append(do_export_table(host, database, destination, measurement_id))

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
                measurement["meta"]["start_time"],
                measurement["meta"]["end_time"],
                str(end_time(measurement["meta"]) - start_time(measurement["meta"])),
                agent["nodes"],
                agent["links"],
            )
            md += "\n"

    (destination / "INDEX.md").write_text(md)
    print(md)


if __name__ == "__main__":
    app()
