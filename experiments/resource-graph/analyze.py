"""Bounded, read-only resource graph; generate KQL inline and check BFS parity."""

import argparse
import json
from collections import deque
from pathlib import Path

GRAPH = Path(__file__).with_name("graph.json")
ROOTS = (
    "collection",
    "agent_live",
    "agent_history",
    "recovery",
    "heavy_analysis",
    "fast_probe",
    "projection_sync",
    "repo_search",
    "dreaming",
)
MAX_DEPTH = 6


def load():
    data = json.loads(GRAPH.read_text(encoding="utf-8"))
    ids = {n["id"] for n in data["nodes"]}
    assert len(ids) == len(data["nodes"])
    for name, edges in data["scenarios"].items():
        all_edges = data["shared_edges"] + edges
        assert len({tuple(e) for e in all_edges}) == len(all_edges), name
        assert all(len(e) == 2 and set(e) <= ids for e in all_edges), name
    return data


def reach(edges, roots=ROOTS, depth=MAX_DEPTH):
    adjacency = {}
    for a, b in edges:
        adjacency.setdefault(a, set()).add(b)
    rows = []
    for root in roots:
        seen = {root: 0}
        queue = deque([root])
        while queue:
            a = queue.popleft()
            if seen[a] == depth:
                continue
            for b in sorted(adjacency.get(a, ())):
                if b not in seen:
                    seen[b] = seen[a] + 1
                    queue.append(b)
        rows.extend([root, n, d] for n, d in seen.items() if n != root)
    return sorted(rows)


def kql(edges):
    literals = ",\n".join(", ".join(json.dumps(x) for x in e) for e in edges)
    roots = ", ".join(json.dumps(x) for x in ROOTS)
    return (
        f"datatable(source_id:string,target_id:string)[\n{literals}\n]\n"
        "| make-graph source_id --> target_id with_node_id=key\n"
        f"| graph-match (a)-[e*1..{MAX_DEPTH}]->(b) where a.key in ({roots}) and a.key != b.key\n"
        "project root=a.key,node=b.key,depth=array_length(map(e, source_id))\n"
        "| summarize depth=min(depth) by root,node | project root,node,depth | order by root asc,node asc"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=list(load()["scenarios"]))
    parser.add_argument("--kql", action="store_true")
    args = parser.parse_args()
    data = load()
    edges = data["shared_edges"] + data["scenarios"][args.scenario]
    if args.kql:
        print(kql(edges))
    else:
        print(json.dumps(reach(edges), indent=2))


if __name__ == "__main__":
    main()
