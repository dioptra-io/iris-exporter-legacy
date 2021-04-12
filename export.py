import logging
import os
from datetime import datetime
from ipaddress import ip_network
from pathlib import Path

import requests
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
    SELECT name FROM system.tables WHERE name LIKE 'results%{uuid}%'
    """
    )
    return [x[0] for x in res]


def main():
    logging.basicConfig(level=logging.INFO)

    logging.info("Authenticating...")
    data = {
        "username": os.environ["IRIS_USERNAME"],
        "password": os.environ["IRIS_PASSWORD"],
    }
    res = request("POST", "/profile/token", data=data)
    headers = {"Authorization": f"Bearer {res['access_token']}"}

    res = request(
        "GET",
        "/measurements/",
        params={"limit": 200, "tag": "1slash16.json"},
        headers=headers,
    )
    res = [x for x in res["results"] if x.get("end_time")]
    last = sorted(res, key=end_time)[-1]
    print(last)

    client = Client("127.0.0.1", database="iris")
    tables = find_tables(client, "46b45b0a-72fc-4a94-86e7-1efcd8bdb2c2")
    print(tables)

    subsets = ip_network("0.0.0.0/0").subnets(new_prefix=4)

    logging.info("Processing nodes...")
    q = GetNodes(filter_destination=True, filter_private=True, time_exceeded_only=True)
    nodes = set()

    for table in tables:
        it = q.execute_iter(client, table, subsets)
        for row in tqdm(it, desc="GetNodes"):
            nodes.add(row[0].ipv4_mapped or row[0])

    with Path("nodes.txt").open("w") as f:
        f.writelines(str(x) + "\n" for x in sorted(nodes))

    del nodes

    logging.info("Processing links...")
    q = GetLinks(filter_destination=True, filter_private=True, time_exceeded_only=True)
    links = set()

    for table in tables:
        it = q.execute_iter(client, table, subsets)
        for row in tqdm(it, desc="GetLinks"):
            a = row[0].ipv4_mapped or row[0]
            b = row[1].ipv4_mapped or row[1]
            links.add((a, b))

    with Path("links.txt").open("w") as f:
        f.writelines(f"{str(a)},{str(b)}\n" for a, b in sorted(links))

    del links


if __name__ == "__main__":
    main()
