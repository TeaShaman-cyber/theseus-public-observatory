from __future__ import annotations

from html import escape
from typing import Iterable

from .model import ExperimentSummary, ObservationSnapshot, ReportSummary

CREDIT = "Created collaboratively by Semyon Poklad and Jester — an AI co-author and engineering research collaborator powered by ChatGPT/OpenAI."


def _url(base_path: str, path: str = "") -> str:
    base = "/" + base_path.strip("/") + "/" if base_path.strip("/") else "/"
    if not path:
        return base
    return base + path.strip("/") + "/"


def _page(title: str, body: str, base_path: str) -> str:
    css = _url(base_path, "static/style.css").rstrip("/")
    nav = " · ".join(
        [
            f'<a href="{_url(base_path)}">Observatory</a>',
            f'<a href="{_url(base_path, "observations")}">Observations</a>',
            f'<a href="{_url(base_path, "experiments")}">Experiments</a>',
            f'<a href="{_url(base_path, "method")}">Method</a>',
            f'<a href="{_url(base_path, "about")}">About</a>',
        ]
    )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><link rel="stylesheet" href="{css}"></head><body><header class="site-header"><a class="site-mark" href="{_url(base_path)}">Theseus Public Observatory</a><nav>{nav}</nav></header><main class="page-shell">{body}</main><footer class="site-footer"><p>{escape(CREDIT)}</p></footer></body></html>'''


def _iso_z(dt) -> str:
    text = dt.astimezone().isoformat()
    if text.endswith("+00:00"):
        text = text[:-6] + "Z"
    if "." in text and text.endswith("Z"):
        head, frac = text[:-1].split(".", 1)
        frac = frac.rstrip("0")
        text = head + (("." + frac) if frac else "") + "Z"
    return text


def _badge(text: str) -> str:
    return f'<span class="badge">{escape(text)}</span>'


def render_home(
    snapshot: ObservationSnapshot,
    reports: Iterable[ReportSummary],
    experiments: Iterable[ExperimentSummary],
    *,
    base_path: str,
) -> str:
    src_ok = sum(1 for s in snapshot.sources if s.collector_ok)
    source_cards = "".join(
        f'<article class="card"><h3>{escape(s.label)}</h3><p>{_badge("collector OK" if s.collector_ok else "collector DEGRADED")} {_badge(s.source_status)}</p><p>{escape(s.url)}</p></article>'
        for s in snapshot.sources
    )
    exp_cards = "".join(
        f'<article class="card"><p>{_badge(e.stage)} {_badge(e.epistemic_status)}</p><h3><a href="{_url(base_path, "experiments/" + e.slug)}">{escape(e.title)}</a></h3><p>{escape(e.result_summary)}</p></article>'
        for e in experiments
    )
    report_links = "".join(
        f"<li><code>{escape(r.slug)}</code> {escape(r.title)}</li>" for r in reports[:5]
    )
    body = f"""<section class="hero"><p class="eyebrow">OBSERVE → PRESERVE → TEST</p><h1>Theseus Public Observatory</h1><p>Public systems and physical data, observed before they are interpreted.</p></section><section><h2>Current state</h2><p>{_badge(snapshot.freshness)} collected {escape(_iso_z(snapshot.collected_at))}; {src_ok}/{len(snapshot.sources)} collectors returned usable data.</p></section><section><h2>Observation streams</h2><div class="grid">{source_cards}</div></section><section><h2>Experiments</h2><div class="grid">{exp_cards}</div></section><section><h2>Latest laboratory notes</h2><ul>{report_links}</ul></section><section><h2>Collaboration</h2><p>{escape(CREDIT)}</p></section>"""
    return _page("Theseus Public Observatory", body, base_path)


def render_observations(snapshot: ObservationSnapshot, *, base_path: str) -> str:
    cards = []
    for s in snapshot.sources:
        status = (
            "collector OK"
            if s.collector_ok
            else f"collector DEGRADED: {s.error or 'unknown error'}"
        )
        cards.append(
            f'<article class="card"><h2>{escape(s.label)}</h2><p>{_badge(status)} {_badge(s.source_status)}</p><p><a href="{escape(s.url)}">canonical public source</a></p><p>HTTP {escape(str(s.http_status))}; {escape(str(s.latency_ms))} ms</p></article>'
        )
    body = f'<h1>Observations</h1><p>{_badge(snapshot.freshness)} snapshot {escape(_iso_z(snapshot.collected_at))}</p><p>Collector health is not the same thing as source status.</p><div class="grid">{"".join(cards)}</div>'
    return _page("Observations", body, base_path)


def render_experiments(
    experiments: Iterable[ExperimentSummary], *, base_path: str
) -> str:
    cards = "".join(
        f'<article class="card"><p>{_badge(e.stage)} {_badge(e.epistemic_status)}</p><h2><a href="{_url(base_path, "experiments/" + e.slug)}">{escape(e.title)}</a></h2><p>{escape(e.question)}</p><p>{escape(e.result_summary)}</p></article>'
        for e in experiments
    )
    return _page(
        "Experiments",
        f'<h1>Experiments</h1><p>Null and negative results are first-class results.</p><div class="grid">{cards}</div>',
        base_path,
    )


def render_experiment(exp: ExperimentSummary, *, base_path: str) -> str:
    sources = "".join(
        f'<li><a href="{escape(u)}">{escape(u)}</a></li>' for u in exp.source_urls
    )
    hashes = "".join(
        f"<li><code>{escape(k)}</code>: <code>{escape(v)}</code></li>"
        for k, v in {**exp.source_hashes, **exp.artifact_hashes}.items()
    )
    evidence = ""
    if exp.workflow_url:
        evidence += (
            f'<li><a href="{escape(exp.workflow_url)}">workflow evidence</a></li>'
        )
    if exp.code_url:
        evidence += f'<li><a href="{escape(exp.code_url)}">source code</a></li>'
    body = f"""<p>{_badge(exp.stage)} {_badge(exp.epistemic_status)}</p><h1>{escape(exp.title)}</h1><h2>Question</h2><p>{escape(exp.question)}</p><h2>Result</h2><p>{escape(exp.result_summary)}</p><h2>What this result does not establish</h2><p>{escape(exp.does_not_establish)}</p><h2>Public source and provenance</h2><ul>{sources}</ul><h2>Durable hashes</h2><ul>{hashes}</ul><h2>Reproducibility evidence</h2><ul>{evidence}</ul><h2>Next gate</h2><p>{escape(exp.next_gate or "UNKNOWN")}</p>"""
    return _page(exp.title, body, base_path)


def render_markdown_page(title: str, html_body: str, *, base_path: str) -> str:
    return _page(
        title,
        f'<article class="prose"><h1>{escape(title)}</h1>{html_body}</article>',
        base_path,
    )
