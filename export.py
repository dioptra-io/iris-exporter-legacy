import json
import logging
import os
import subprocess
from datetime import datetime
from ipaddress import ip_network
from pathlib import Path
from typing import Optional

import requests
import typer
from clickhouse_driver import Client
from diamond_miner.queries.get_links import GetLinks
from diamond_miner.queries.get_nodes import GetNodes
from tqdm import tqdm

IRIS_URL = "https://iris.dioptra.io/api"


def request(method, path, **kwargs):
    req = requests.request(method, IRIS_URL + path, **kwargs)
    req.raise_for_status()
    return req.json()


def start_time(measurement):
    return datetime.fromisoformat(measurement["start_time"])


def end_time(measurement):
    return datetime.fromisoformat(measurement["end_time"])


def find_tables(client, uuid):
    uuid = uuid.replace("-", "_")
    res = client.execute(
        f"""
    SELECT name FROM system.tables WHERE name LIKE 'results__%{uuid}%'
    """
    )
    return [x[0] for x in res]


def do_export_tables(database, host, tables):
    for table in tables:
        logging.info(f"Exporting {table}...")
        cmd = "clickhouse-client"
        cmd += f" --host={host}"
        cmd += f" --database={database}"
        cmd += f" --query=\"SELECT * FROM {table} INTO OUTFILE 'exports/{table}.clickhouse' FORMAT Native\""  # noqa
        logging.info(cmd)
        subprocess.run(cmd, check=True, shell=True)


def do_export_nodes(client, tables, subsets, uuid):
    q = GetNodes(filter_destination=True, filter_private=True, time_exceeded_only=True)
    nodes = set()
    for table in tables:
        it = q.execute_iter(client, table, subsets)
        for row in tqdm(it, desc="Query"):
            nodes.add(row[0].ipv4_mapped or row[0])
    with Path(f"exports/nodes_{uuid}.txt").open("w") as f:
        f.writelines(str(x) + "\n" for x in tqdm(nodes, desc="Write"))


def do_export_links(client, tables, subsets, uuid):
    q = GetLinks(filter_destination=True, filter_private=True, time_exceeded_only=True)
    links = set()
    for table in tables:
        it = q.execute_iter(client, table, subsets)
        for row in tqdm(it, desc="Query"):
            a = row[0].ipv4_mapped or row[0]
            b = row[1].ipv4_mapped or row[1]
            links.add((a, b))
    with Path(f"exports/links_{uuid}.txt").open("w") as f:
        f.writelines(f"{str(a)},{str(b)}\n" for a, b in tqdm(links, desc="Write"))


def main(
    tag: Optional[str] = typer.Option(
        None,
        metavar="TAG",
        help="Export the latest (finished) measurement with the specified tag.",
    ),
    uuid: Optional[str] = typer.Option(
        None, metavar="UUID", help="Export the measurement with the specified UUID."
    ),
    export_nodes: bool = typer.Option(True, is_flag=True),
    export_links: bool = typer.Option(True, is_flag=True),
    export_tables: bool = typer.Option(
        True,
        is_flag=True,
        help="Dump the tables in native format (requires clickhouse-client).",
    ),
    database: Optional[str] = typer.Option("iris", metavar="DATABASE"),
    host: Optional[str] = typer.Option(
        "127.0.0.1", metavar="HOST", help="ClickHouse host"
    ),
):
    if tag == uuid:
        print("One of --tag or --uuid must be specified.")
        return

    if uuid:
        uuid = uuid.replace("_", "-")

    logging.basicConfig(level=logging.INFO)

    logging.info("Authenticating...")
    data = {
        "username": os.environ["IRIS_USERNAME"],
        "password": os.environ["IRIS_PASSWORD"],
    }
    res = request("POST", "/profile/token", data=data)
    headers = {"Authorization": f"Bearer {res['access_token']}"}

    if tag:
        logging.info(f"Listing measurements with tag {tag}...")
        res = request(
            "GET",
            "/measurements/",
            params={"limit": 200, "tag": tag},
            headers=headers,
        )
        res = [x for x in res["results"] if x.get("end_time")]
        if not res:
            logging.error("Measurement not found")
            return
        last = sorted(res, key=end_time)[-1]
        uuid = last["uuid"]

    logging.info("Getting measurement information...")
    res = request("GET", f"/measurements/{uuid}", headers=headers)
    Path(f"exports/{uuid}.json").write_text(json.dumps(res, indent=4))

    logging.info(f"Listing tables with uuid {uuid}...")
    client = Client(host, database=database)
    tables = find_tables(client, uuid)
    for table in tables:
        logging.info(table)

    subsets = list(ip_network("0.0.0.0/0").subnets(new_prefix=4))

    if export_tables:
        do_export_tables(database, host, tables)

    if export_nodes:
        do_export_nodes(client, tables, subsets, uuid)

    if export_links:
        do_export_links(client, tables, subsets, uuid)


if __name__ == "__main__":
    typer.run(main)
