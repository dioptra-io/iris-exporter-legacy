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
    files = destination.glob("*.json")
    metas = []
    for file in files:
        meta = json.loads(file.read_text())
        nodes = wc(file.with_suffix(".nodes"))
        links = wc(file.with_suffix(".links"))
        metas.append((meta, nodes, links))
    metas = sorted(metas, key=lambda x: datetime.fromisoformat(x[0]["start_time"]))

    md = ""
    template = "{:<10} | {:<20} | {:<20} | {:<16} | {:<10} | {:<10}"
    md += template.format("UUID", "Start", "End", "Duration", "Nodes", "Links") + "\n"
    md += template.format("--", "--", "--", "--", "--", "--") + "\n"
    for meta, nodes, links in metas:
        md += template.format(
            meta["uuid"].split("-")[0],
            meta["start_time"],
            meta["end_time"],
            str(end_time(meta) - start_time(meta)),
            nodes,
            links,
        )
        md += "\n"

    (destination / "INDEX.md").write_text(md)
    print(md)


if __name__ == "__main__":
    typer.run(main)
