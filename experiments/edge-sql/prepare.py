"""Generate identical, issue-31 public fixtures and native SQL answers."""

import json
import subprocess
import sys
from pathlib import Path

import duckdb

REVISION = "2b53406f741ae8e2d2b078d9233e1d2317a47185"
QUERIES = {
    "health": "SELECT usable, count(*) AS n FROM sources GROUP BY usable ORDER BY usable",
    "join": "SELECT s.id,count(p.measured_at) AS n,round(avg(p.value),8) AS mean_value FROM sources s LEFT JOIN samples p ON s.id=p.source_id GROUP BY s.id ORDER BY s.id",
    "window": "WITH lagged AS (SELECT source_id,value-lag(value) OVER(PARTITION BY source_id,window_start,window_end ORDER BY measured_at) AS delta FROM samples) SELECT source_id,count(delta) AS n,round(max(abs(delta)),8) AS max_delta FROM lagged GROUP BY source_id ORDER BY source_id",
}


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(
        subprocess.check_output(
            ["git", "show", REVISION + ":data/latest/public-status.json"]
        )
    )
    sources = [
        (s["id"], int(s["ok"]), s["http_status"], s["latency_ms"])
        for s in data["sources"]
    ]
    points = [
        (
            s["id"],
            p["measured_at"],
            p["value"],
            s["summary"]["window_start"],
            s["summary"]["window_end"],
        )
        for s in data["sources"]
        if s["id"].startswith("radar_") and s["ok"]
        for p in s["summary"]["points"]
    ]
    assert len(sources) == 16 and len(points) == 728
    with duckdb.connect(":memory:", config={"threads": 1}) as con:
        con.execute(
            "CREATE TABLE sources(id VARCHAR, usable INTEGER, http_status INTEGER, latency_ms INTEGER)"
        )
        con.execute(
            "CREATE TABLE samples(source_id VARCHAR, measured_at VARCHAR, value DOUBLE, window_start VARCHAR, window_end VARCHAR)"
        )
        con.executemany("INSERT INTO sources VALUES (?,?,?,?)", sources)
        con.executemany("INSERT INTO samples VALUES (?,?,?,?,?)", points)
        reference = {}
        for name, sql in QUERIES.items():
            result = con.execute(sql)
            keys = [c[0] for c in result.description]
            reference[name] = [dict(zip(keys, row)) for row in result.fetchall()]
        for table in ("sources", "samples"):
            con.table(table).write_parquet(
                str(out / f"{table}.parquet"), compression="zstd"
            )
    (out / "reference.json").write_text(
        json.dumps(
            {"revision": REVISION, "queries": QUERIES, "expected": reference},
            allow_nan=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
