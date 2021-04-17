import json
from datetime import datetime
from pathlib import Path


def main():
    files = Path("exports/").glob("*.json")
    metas = [json.loads(f.read_text()) for f in files]
    metas = sorted(metas, key=lambda x: datetime.fromisoformat(x["start_time"]))

    md = ""
    template = "{:10} | {:15} | {:8} | {:20} | {:20}"
    md += template.format("uuid", "tool", "agents", "start", "end") + "\n"
    md += template.format("--", "--", "--", "--", "--") + "\n"
    for m in metas:
        md += template.format(
            m["uuid"].split("-")[0],
            m["tool"],
            len(m["agents"]),
            m["start_time"],
            m["end_time"],
        )
        md += "\n"

    Path("exports/INDEX.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
