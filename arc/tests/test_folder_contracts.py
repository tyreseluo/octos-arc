"""Rules stated on FOLDER nodes are part of every requirement beneath them.

The hackathon trees put their cross-cutting UI contracts on FOLDER nodes (the
sheet task's REQ-1 says worksheet tabs use the ARIA tab role with
aria-selected="true"; 95 of its 100 evaluation tests open a workbook through
exactly that contract). atomic_nodes() keeps FOLDERs as grouping only, so the
implement prompt must still carry every ancestor's description.
"""
import unittest

import main

POLICY = dict(name="arc_build", repairs=5, repair_window=1800, node_timeout=1200, verify_timeout=900,
              max_iterations=40, run_timeout=3600, tools="read_file,write_file",
              reasoning="none", max_output_tokens=65536, node_budget=600,
              min_node_seconds=120, final_reserve_seconds=600, final_repairs=2,
              context_window=0, llm_timeout=900, node_max_output_tokens=32768,
              group_requirements=0, group_max_chars=2600)


def folder(node_id, description, children):
    return {"id": node_id, "name": f"{node_id} name", "type": "FOLDER",
            "description": description, "children": children}


def atomic(node_id, deps=()):
    return {"id": node_id, "type": "ATOMIC", "name": node_id,
            "description": f"build {node_id}", "dependencies": list(deps)}


TREE = folder("ROOT", "Every quoted name is the exact accessible name.", [
    folder("REQ-1", "Worksheet tabs use the ARIA tab role.", [
        folder("REQ-1-1", "", [atomic("REQ-1-1-1")]),
        atomic("REQ-1-2"),
    ]),
    folder("REQ-2", "Grid cells use the gridcell role.", [atomic("REQ-2-1")]),
])


def prompt_of(dot, node_id):
    impl = "impl_" + main.sanitize(node_id)
    line = next(l for l in dot.splitlines() if l.strip().startswith(impl + " ["))
    return line.split('prompt="', 1)[1]


class FolderContracts(unittest.TestCase):
    def setUp(self):
        self.nodes = main.atomic_nodes(TREE)
        self.dot = main.build_pipeline(self.nodes, "/tmp/out", POLICY, [43100], 1e10)

    def test_should_carry_every_ancestor_rule_when_requirement_is_nested(self):
        body = prompt_of(self.dot, "REQ-1-1-1")
        self.assertIn("Every quoted name is the exact accessible name.", body)
        self.assertIn("Worksheet tabs use the ARIA tab role.", body)

    def test_should_not_carry_a_sibling_branch_rule_when_requirement_is_elsewhere(self):
        self.assertNotIn("gridcell role", prompt_of(self.dot, "REQ-1-2"))
        self.assertIn("gridcell role", prompt_of(self.dot, "REQ-2-1"))

    def test_should_put_ancestor_rules_before_the_requirement_text(self):
        body = prompt_of(self.dot, "REQ-1-2")
        self.assertLess(body.index("ARIA tab role"), body.index("build REQ-1-2"))

    def test_should_state_each_shared_rule_once_when_siblings_are_grouped(self):
        grouped = dict(POLICY, group_requirements=1, group_max_chars=6000)
        tree = folder("ROOT", "Root rule.", [folder("REQ-1", "Tab rule.", [atomic("A"), atomic("B")])])
        dot = main.build_pipeline(main.atomic_nodes(tree), "/tmp/out", grouped, [43100], 1e10)
        body = prompt_of(dot, "A+B")
        self.assertEqual(body.count("Tab rule."), 1)
        self.assertEqual(body.count("Root rule."), 1)

    def test_should_leave_the_stored_requirement_tree_untouched(self):
        import copy
        tree = copy.deepcopy(TREE)
        before = copy.deepcopy(tree)
        main.atomic_nodes(tree)
        self.assertEqual(tree, before)

    def test_should_not_count_ancestor_rules_against_the_group_size_cap(self):
        big = folder("ROOT", "x" * 9000, [atomic("A"), atomic("B")])
        groups = main.group_nodes(main.atomic_nodes(big), 6000, 3)
        self.assertEqual([[n["id"] for n in g] for g in groups], [["A", "B"]])


if __name__ == "__main__":
    unittest.main()
