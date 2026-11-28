"""Import a frozen Git journal day through the attached Supabase REST proxy."""

import argparse
import hashlib
import json
import subprocess
from datetime import date, datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://supabase.int.exe.xyz/rest/v1/"


def records(raw, day, commit):
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("invalid day")
    result = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        receipt = json.loads(line)
        stamp = datetime.fromisoformat(receipt["collected_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None or not isinstance(receipt["sources"], list):
            raise ValueError("invalid receipt")
        result.append(
            {
                "journal_path": f"data/{day}/public-status.jsonl",
                "journal_line": line_number,
                "line_sha256": hashlib.sha256(line).hexdigest(),
                "source_commit": commit,
                "receipt": receipt,
            }
        )
    return result


def verify(expected, actual):
    # A later Git ref may contain the identical original line.
    for key in ("journal_path", "journal_line", "line_sha256", "receipt"):
        if expected[key] != actual.get(key):
            raise ValueError(f"projection mismatch: {key}")


def request(path, body=None, prefer=None):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    req = Request(
        BASE + path,
        data=None if body is None else json.dumps(body, allow_nan=False).encode(),
        headers=headers,
    )
    with urlopen(req, timeout=30) as response:
        data = response.read()
        return json.loads(data) if data else None


def sync(rows):
    for row in rows:
        request(
            "observatory_journal?on_conflict=journal_path,journal_line",
            row,
            "resolution=ignore-duplicates,return=minimal",
        )
        query = urlencode(
            {
                "journal_path": "eq." + row["journal_path"],
                "journal_line": "eq." + str(row["journal_line"]),
                "select": "*",
            }
        )
        existing = request("observatory_journal?" + query)
        if len(existing) != 1:
            raise ValueError("missing projection readback")
        verify(row, existing[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", required=True, type=date.fromisoformat)
    parser.add_argument("--ref", default="origin/main")
    args = parser.parse_args()
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", args.ref + "^{commit}"], text=True
    ).strip()
    day = args.day.isoformat()
    raw = subprocess.check_output(
        ["git", "show", f"{commit}:data/{day}/public-status.jsonl"]
    )
    rows = records(raw, day, commit)
    sync(rows)
    print(json.dumps({"verified": len(rows), "source_commit": commit, "day": day}))


if __name__ == "__main__":
    main()
