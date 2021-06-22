import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import typer
from diamond_miner.queries import GetLinks, GetNodes, results_table

IRIS_URL = "https://iris.dioptra.io/api"


async def execute(host: str, database: str, statement: str) -> None:
    cmd = f'clickhouse-client --host={host} --database={database} --query="{statement}"'
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()


async def do_export_links(
    host: str, database: str, measurement_id: str, path: str
) -> None:
    logging.info(
        "export_links host=%s database=%s measurement_id=%s path=%s",
        host,
        database,
        measurement_id,
        path,
    )
    query = f"""
    {GetLinks().statement(measurement_id)}
    INTO OUTFILE '{path}'
    FORMAT CSV
    """
    await execute(host, database, query)


async def do_export_nodes(
    host: str, database: str, measurement_id: str, path: str
) -> None:
    logging.info(
        "export_nodes host=%s database=%s measurement_id=%s path=%s",
        host,
        database,
        measurement_id,
        path,
    )
    query = f"""
    {GetNodes().statement(measurement_id)}
    INTO OUTFILE '{path}'
    FORMAT CSV
    """
    await execute(host, database, query)


async def do_export_table(
    host: str, database: str, measurement_id: str, path: str
) -> None:
    logging.info(
        "export_table host=%s database=%s measurement_id=%s path=%s",
        host,
        database,
        measurement_id,
        path,
    )
    query = f"""
    SELECT * FROM {results_table(measurement_id)}
    INTO OUTFILE '{path}'
    FORMAT Native
    """
    await execute(host, database, query)


def find_uuid(headers: dict, tag: str) -> str:
    logging.info(f"Listing measurements with tag {tag}...")
    res = request(
        "GET",
        "/measurements/",
        params={"limit": 200, "tag": tag},
        headers=headers,
    )
    res = [x for x in res["results"] if x.get("end_time")]
    return sorted(res, key=end_time)[-1]["uuid"]


def request(method, path, **kwargs):
    req = requests.request(method, IRIS_URL + path, **kwargs)
    req.raise_for_status()
    return req.json()


def start_time(measurement):
    return datetime.fromisoformat(measurement["start_time"])


def end_time(measurement):
    return datetime.fromisoformat(measurement["end_time"])


def main(
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
    destination: Optional[Path] = typer.Option("exports", metavar="DESTINATION"),
    database: Optional[str] = typer.Option("iris", metavar="DATABASE"),
    host: Optional[str] = typer.Option("127.0.0.1", metavar="HOST"),
):
    assert tag or uuid, "One of --tag or --uuid must be specified."
    logging.basicConfig(level=logging.INFO)

    logging.info("Authenticating...")
    data = {
        "username": os.environ["IRIS_USERNAME"],
        "password": os.environ["IRIS_PASSWORD"],
    }
    res = request("POST", "/profile/token", data=data)
    headers = {"Authorization": f"Bearer {res['access_token']}"}

    if tag:
        uuid = find_uuid(headers, tag)

    logging.info("Getting measurement information...")
    info = request("GET", f"/measurements/{uuid}", headers=headers)
    (destination / f"{uuid}.json").write_text(json.dumps(info, indent=4))

    measurement_ids = [f"{uuid}__{agent['uuid']}" for agent in info["agents"]]
    futures = []

    if export_links:
        for measurement_id in measurement_ids:
            path = (destination / measurement_id).with_suffix(".links")
            futures.append(do_export_links(host, database, measurement_id, str(path)))

    if export_nodes:
        for measurement_id in measurement_ids:
            path = (destination / measurement_id).with_suffix(".nodes")
            futures.append(do_export_nodes(host, database, measurement_id, str(path)))

    if export_tables:
        for measurement_id in measurement_ids:
            path = (destination / measurement_id).with_suffix(".clickhouse")
            futures.append(do_export_table(host, database, measurement_id, str(path)))

    async def _do():
        await asyncio.gather(*futures)

    asyncio.run(_do())


if __name__ == "__main__":
    typer.run(main)
