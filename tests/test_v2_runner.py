from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from pomdp_bench.agents import AdapterError, ChatAgent, ScriptedAgent, strict_json, validate_config
from pomdp_bench.cli import main
from pomdp_bench.collection import run_suite
from pomdp_bench.evaluation import run_episode
from pomdp_bench.generator import generate, suite
from pomdp_bench.reporting import paired, summarize, validate_run


class RunnerTestsV2(unittest.TestCase):
    def test_arbitrary_names_all_conditions_replays_and_includes_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            data = suite([0, 1])
            configs = [{"name": "future-model", "kind": "reference"}, {"name": "gaming", "kind": "proxy"}]
            report = run_suite(data, configs, ["open", "principles", "procedural"], 2, out)
            self.assertEqual(report["episodes"], 48)
            self.assertTrue(report["complete"])
            _, records = validate_run(out)
            self.assertEqual(len(records), 48)
            for group in report["overall"]:
                self.assertEqual(group["seed_clusters"], 2)
                self.assertEqual(group["success_rate"], float(group["agent"] == "future-model"))
            with self.assertRaises(ValueError):
                run_suite(data, configs, ["open"], 1, out)
            path = next((out / "private" / "traces").glob("*.json"))
            path.unlink()
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                validate_run(out)

    def test_failed_adapter_is_a_recorded_failure_and_usage_unknown(self):
        config = {"name": "offline-model", "kind": "chat", "model": "example", "endpoint_env": "ABSENT_ENDPOINT",
                  "api_key_env": "ABSENT_KEY"}
        with patch.dict(os.environ, {}, clear=True):
            record = run_episode(generate(1), config, "open", 0)
        self.assertFalse(record["grade"]["success"])
        report = summarize([record])
        group = report["overall"][0]
        self.assertEqual(group["episodes"], 1)
        self.assertEqual(group["adapter_failures"], 1)
        self.assertIsNone(group["total_input_tokens"])
        self.assertIsNone(group["action_cost_per_accepted_completion"])

    def test_unmatched_comparison_and_duplicates_are_rejected(self):
        a = run_episode(generate(1), {"name": "a", "kind": "reference"}, "open", 0)
        b = run_episode(generate(2), {"name": "b", "kind": "reference"}, "open", 0)
        self.assertFalse(paired([a], [b])["comparable"])
        with self.assertRaises(ValueError):
            summarize([a, a])

    def test_bad_configuration_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            with self.assertRaises(ValueError):
                run_suite(suite([0]), [{"name": "bad", "kind": "unknown"}], ["open"], 1, out)
            self.assertFalse(out.exists())

    def test_cli_suite_and_run_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            spec, out = Path(temp) / "suite.json", Path(temp) / "run"
            self.assertEqual(main(["generate", "--count", "2", "--fresh", "--out", str(spec)]), 0)
            self.assertEqual(main(["run", "--suite", str(spec), "--out", str(out)]), 0)
            self.assertEqual(main(["validate", str(out)]), 0)
            self.assertEqual(main(["summarize", str(out)]), 0)

    def test_sampling_options_cannot_replace_task_or_inject_credentials(self):
        base = {"name": "a", "kind": "chat", "model": "m", "endpoint_env": "E", "api_key_env": "K"}
        for options in ({"messages": []}, {"api_key": "secret"}, {"temperature": float("nan")}):
            with self.assertRaises(ValueError):
                validate_config({**base, "options": options})

    def test_nonfinite_provider_action_is_rejected_before_recording(self):
        with self.assertRaises(ValueError):
            strict_json('{"command":"inspect","target":NaN}')


class HttpAdapterTests(unittest.TestCase):
    def test_live_local_http_conversation_has_only_public_projection(self):
        received = []
        scripted = ScriptedAgent("reference", 1)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                request = json.loads(body["messages"][1]["content"])
                received.append(request)
                action = scripted.act(request, 10)
                self.server.received_bodies.append(body)
                payload = {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(action)}}],
                           "usage": {"prompt_tokens": 10, "completion_tokens": 4}}
                raw = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.received_bodies = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = {"name": "http-fixture", "kind": "chat", "model": "fixture", "endpoint_env": "TEST_ENDPOINT", "api_key_env": "TEST_KEY"}
        try:
            with patch.dict(os.environ, {"TEST_ENDPOINT": f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                                         "TEST_KEY": "test-only-not-a-real-credential"}):
                trace = run_episode(generate(4, "cascade"), config, "open", 0)
            self.assertTrue(trace["grade"]["success"], trace)
            self.assertGreater(len(received), 3)
            self.assertTrue(all(b["tools"] == [] and b["tool_choice"] == "none" for b in server.received_bodies))
            self.assertEqual(trace["usage"]["input_tokens"], 10 * len(received))
            serialized = json.dumps(received)
            self.assertNotIn('"truths"', serialized)
            self.assertNotIn('"seed"', serialized)
            self.assertNotIn("test-only-not-a-real-credential", json.dumps(trace))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_url_embedded_credentials_rejected(self):
        config = {"name": "a", "kind": "chat", "model": "m", "endpoint_env": "E", "api_key_env": "K"}
        for url in ("https://user:password@example.org/chat", "https://example.org/chat?key=x", "http://example.org/chat"):
            with patch.dict(os.environ, {"E": url, "K": "dummy"}):
                with self.assertRaises(AdapterError):
                    ChatAgent(config)


if __name__ == "__main__":
    unittest.main()
