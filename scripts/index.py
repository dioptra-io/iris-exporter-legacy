#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from subprocess import run
from typing import Optional

import typer


def start_time(measurement):
    return datetime.fromisoformat(measurement["start_time"])


def end_time(measurement):
    return datetime.fromisoformat(measurement["end_time"])


def wc(file):
    res = run(["wc", "-l", str(file)], capture_output=True, check=True)
    return int(res.stdout.split()[0])


def main(destination: Optional[Path] = typer.Option("exports", metavar="DESTINATION")):
    measurements = []

    for file in destination.glob("*.json"):
        meta = json.loads(file.read_text())
        measurement_uuid = meta["uuid"]
        agents = {}

        for file_ in destination.glob(f"{measurement_uuid}*.nodes"):
            agent_uuid = file_.stem.split("__")[1]
            agents.setdefault(agent_uuid, {})["nodes"] = wc(file_)

        for file_ in destination.glob(f"{measurement_uuid}*.links"):
            agent_uuid = file_.stem.split("__")[1]
            agents.setdefault(agent_uuid, {})["links"] = wc(file_)

        measurements.append({"meta": meta, "agents": agents})

    measurements = sorted(
        measurements, key=lambda x: datetime.fromisoformat(x["meta"]["start_time"])
    )

    print(measurements)

    # md = ""
    # template = "{:<10} | {:<10} | {:<20} | {:<20} | {:<16} | {:<10} | {:<10}"
    # md += template.format(
    #     "Measurement", "Agent", "Start", "End", "Duration", "Nodes", "Links"
    # )
    # md += "\n"
    # md += template.format("--", "--", "--", "--", "--", "--", "--") + "\n"
    # for meta, nodes, links in metas:
    #     md += template.format(
    #         meta["uuid"].split("-")[0],
    #         meta["start_time"],
    #         meta["end_time"],
    #         str(end_time(meta) - start_time(meta)),
    #         nodes,
    #         links,
    #     )
    #     md += "\n"
    #
    # (destination / "INDEX.md").write_text(md)
    # print(md)


if __name__ == "__main__":
    typer.run(main)
