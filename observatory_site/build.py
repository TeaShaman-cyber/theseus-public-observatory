from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

import markdown

from .content import load_experiments, load_latest_snapshot, load_reports
from .render import render_experiment, render_experiments, render_home, render_markdown_page, render_observations

FRESHNESS_BUDGET_SECONDS = 2 * 3600


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_site(repo_root: Path, output: Path, base_path: str, now: datetime) -> None:
    if output.exists():
        shutil.rmtree(output)
    snapshot = load_latest_snapshot(repo_root, now=now, freshness_budget_seconds=FRESHNESS_BUDGET_SECONDS)
    reports = load_reports(repo_root)
    experiments = load_experiments(repo_root)
    _write(output / "index.html", render_home(snapshot, reports, experiments, base_path=base_path))
    _write(output / "observations/index.html", render_observations(snapshot, base_path=base_path))
    _write(output / "experiments/index.html", render_experiments(experiments, base_path=base_path))
    for exp in experiments:
        _write(output / f"experiments/{exp.slug}/index.html", render_experiment(exp, base_path=base_path))
    method_path = repo_root / "docs/methodology.md"
    method_html = markdown.markdown(method_path.read_text(encoding="utf-8"), extensions=["fenced_code"])
    _write(output / "method/index.html", render_markdown_page("Method", method_html, base_path=base_path))
    about = '<p>Theseus Public Observatory is a public-data laboratory. Observation comes before interpretation.</p><p>Created collaboratively by Semyon Poklad and Jester — an AI co-author and engineering research collaborator powered by ChatGPT/OpenAI.</p>'
    _write(output / "about/index.html", render_markdown_page("About / collaboration", about, base_path=base_path))
    static_src = Path(__file__).parent / "static"
    shutil.copytree(static_src, output / "static")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path, default=Path("public"))
    ap.add_argument("--base-path", default="/")
    args = ap.parse_args()
    build_site(args.repo_root.resolve(), args.output.resolve(), args.base_path, datetime.now(timezone.utc))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
