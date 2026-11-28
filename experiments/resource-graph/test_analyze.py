import unittest

from analyze import MAX_DEPTH, kql, load, reach


class ResourceGraphTests(unittest.TestCase):
    def test_shortest_path_and_cycle(self):
        edges = [["a", "b"], ["b", "c"], ["a", "c"], ["c", "a"]]
        self.assertEqual(reach(edges, ["a"]), [["a", "b", 1], ["a", "c", 1]])
        self.assertEqual(reach([["a", "b"], ["b", "c"]], ["a"], 1), [["a", "b", 1]])

    def test_graph_scenarios_and_resource_isolation(self):
        graph = load()
        results = {
            name: {(a, b) for a, b, _ in reach(graph["shared_edges"] + edges)}
            for name, edges in graph["scenarios"].items()
        }
        for pairs in results.values():
            for root, target in pairs:
                if root != "repo_search":
                    self.assertNotIn(target, {"turso", "motherduck", "kusto"})
        candidate = results["d1_candidate"]
        self.assertIn(("agent_live", "d1_quota"), candidate)
        self.assertNotIn(("agent_live", "exe_pool"), candidate)
        self.assertNotIn(("agent_live", "workers_quota"), candidate)
        self.assertNotIn(("agent_live", "github_service"), candidate)
        self.assertIn(("projection_sync", "github_service"), candidate)
        self.assertIn(("recovery", "github_service"), candidate)
        self.assertIn(("collection", "workers_quota"), results["worker_candidate"])
        self.assertIn(("dreaming", "workers_quota"), results["worker_candidate"])
        self.assertIn(("agent_live", "r2"), results["worker_candidate"])

    def test_inline_read_only_query(self):
        query = kql([["a", "b"]])
        self.assertTrue(query.startswith("datatable("))
        self.assertIn(f"graph-match (a)-[e*1..{MAX_DEPTH}]->(b)", query)
        self.assertNotIn(".create", query)
        self.assertNotIn(".set", query)


if __name__ == "__main__":
    unittest.main()
