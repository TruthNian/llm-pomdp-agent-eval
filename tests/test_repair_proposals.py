"""Proposal boundary checks; no network calls or candidate execution."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/repository-portfolio-v1"
spec = importlib.util.spec_from_file_location("repair_proposals", STUDY / "proposals.py")
proposals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proposals)


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((STUDY / "proposal_plan.json").read_text())

    def test_public_baseline_context_contains_no_upstream_fix_or_oracle(self):
        for task, paths in self.plan["context_paths"].items():
            request = proposals.public_request(self.plan, task)
            self.assertEqual(set(request["observation"]["files"]), set(paths))
            serialized = json.dumps(request)
            for hidden in ("upstream-actions", "fix_commit", "file_sha256", "check_version",
                           "image_id", "source_task_id"):
                self.assertNotIn(hidden, serialized)
            self.assertEqual(request["history"], [])

    def test_real_artifact_edits_validate_and_malformed_edits_are_not_repaired(self):
        for task in self.plan["context_paths"]:
            fixed = json.loads((ROOT / "pomdp_bench/repair_data" / task / "upstream-actions.json").read_text())
            action = {"command": "submit_patch", "target": [a["target"] for a in fixed[:-2]]}
            edits, patch = proposals.proposal_edits(self.plan, task, action)
            self.assertEqual(edits, fixed[:-2])
            self.assertIn("--- a/src/", patch)
            for malformed in ({"command": "submit_patch", "target": []},
                              {"command": "verify"},
                              {"command": "submit_patch", "target": [{"path": "tests/test.py", "old": "a", "new": "b"}]},
                              {"command": "submit_patch", "target": [dict(action["target"][0], old="not existing source")]}):
                with self.assertRaises(ValueError):
                    proposals.proposal_edits(self.plan, task, malformed)


if __name__ == "__main__":
    unittest.main()
