"""Advisory CRAP proxy using exact-path LCOV and pinned crapper complexity."""

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
from pathlib import Path


def read_lcov(text):
    files = {}
    path = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            path = line[3:]
            if path in files or path.startswith("/") or ".." in Path(path).parts:
                raise ValueError("duplicate or nonrelative source path")
            files[path] = {"line": {}, "branch": {}}
        elif line == "end_of_record":
            path = None
        elif line.startswith(("DA:", "BRDA:")):
            if path is None:
                raise ValueError("coverage record outside source")
            parts = line.split(":", 1)[1].split(",")
            if line.startswith("DA:"):
                key = int(parts[0])
                hits = int(parts[1])
                kind = "line"
            else:
                key = (int(parts[0]), parts[1], parts[2])
                hits = 0 if parts[3] == "-" else int(parts[3])
                kind = "branch"
            records = files[path][kind]
            if key in records or hits < 0:
                raise ValueError("duplicate or invalid coverage record")
            records[key] = hits
    return files


def score(cc, start, end, coverage):
    if coverage is not None:
        for kind in ("branch", "line"):
            values = [
                v
                for k, v in coverage[kind].items()
                if start <= (k[0] if kind == "branch" else k) <= end
            ]
            if values:
                covered = sum(v > 0 for v in values)
                total = len(values)
                return covered, total, kind, cc**2 * (1 - covered / total) ** 3 + cc
    return 0, 0, "unknown", None


def report(root, python_lcov, js_lcov):
    from crapper.languages import functions_in_file

    py = read_lcov(python_lcov.read_text())
    js = read_lcov(js_lcov.read_text())
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    paths = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        .decode()
        .split("\x00")
    )
    entries = []
    sources = []
    for path in paths:
        p = Path(path)
        if (
            not p.parts
            or p.parts[0] not in ("scripts", "observatory_site", "experiments")
            or p.suffix not in (".py", ".mjs")
        ):
            continue
        if (
            "tests" in p.parts
            or p.name.startswith("test_")
            or p.name.endswith(".test.mjs")
            or p.parts[:2] == ("experiments", "crap")
        ):
            continue
        lang = "python" if p.suffix == ".py" else "typescript"
        sources.append(path)
        cov = (py if lang == "python" else js).get(path)
        for f in functions_in_file(lang, (root / p).read_text(), path, str(root)):
            hit, total, kind, risk = score(f.complexity, f.start_line, f.end_line, cov)
            entries.append(
                dict(
                    path=path,
                    name=f.name,
                    namespace=f.namespace,
                    language="python" if lang == "python" else "javascript",
                    start=f.start_line,
                    end=f.end_line,
                    cc=f.complexity,
                    covered=hit,
                    opportunities=total,
                    coverage_kind=kind,
                    crap=risk,
                )
            )
    entries.sort(
        key=lambda r: (r["crap"] is None, -(r["crap"] or 0), r["path"], r["start"])
    )
    return dict(
        source_sha=sha,
        scope=sources,
        threshold_advisory=30,
        entries=entries,
        analyzer_source="fdd0c01387e4211c74b23c2cdd11c06d90883838",
        versions={
            name: importlib.metadata.version(name)
            for name in ("coverage", "tree-sitter", "tree-sitter-language-pack")
        },
        coverage_sha256={
            "python": hashlib.sha256(python_lcov.read_bytes()).hexdigest(),
            "javascript": hashlib.sha256(js_lcov.read_bytes()).hexdigest(),
        },
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--python-lcov", type=Path, required=True)
    p.add_argument("--js-lcov", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = report(a.root.resolve(), a.python_lcov, a.js_lcov)
    with a.output.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
    for lang in ("python", "javascript"):
        rows = [r for r in result["entries"] if r["language"] == lang]
        print(
            lang,
            len(rows),
            "unknown",
            sum(r["crap"] is None for r in rows),
            ">30",
            sum((r["crap"] or 0) > 30 for r in rows),
        )
        for r in [r for r in rows if r["crap"] is not None][:10]:
            print(
                r["path"],
                r["start"],
                r["name"],
                r["cc"],
                r["coverage_kind"],
                f"{r['covered']}/{r['opportunities']}",
                round(r["crap"], 2),
            )


if __name__ == "__main__":
    main()
