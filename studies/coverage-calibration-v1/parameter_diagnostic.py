"""Two fixed public constant-action probes; no scores and no outcome-dependent retry."""
import http.client
import json
import os
from pathlib import Path
import time

from pomdp_bench.model_io import ResponseStream
from pomdp_bench.storage import write_json


def main():
    codex_path = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    auth = json.loads((codex_path / "auth.json").read_text(encoding="utf-8"))["tokens"]
    protected = (codex_path / "auth.json", codex_path / "config.toml",
                 codex_path / "codex-router/native-session-consent.json")
    before = [p.read_bytes() if p.exists() else None for p in protected]
    rows = []
    for cap in (16384, None):
        body = {"model": "gpt-5.6-sol", "instructions": 'Return exactly {"command":"status"}.',
                "input": [{"role": "user", "content": "Public constant-output transport diagnostic."}],
                "reasoning": {"effort": "high"}, "tools": [], "tool_choice": "none", "store": False, "stream": True}
        if cap is not None:
            body["max_output_tokens"] = cap
        connection = http.client.HTTPConnection("127.0.0.1", 4202, timeout=60)
        started = time.monotonic()
        row = {"max_output_tokens": cap}
        try:
            connection.request("POST", "/v1/responses", body=json.dumps(body), headers={
                "Content-Type": "application/json", "Authorization": "Bearer " + auth["access_token"],
                "ChatGPT-Account-Id": auth["account_id"], "x-codex-router-exact-route": "1"})
            response = connection.getresponse()
            row["http_status"] = response.status
            raw = response.read(131073)
            if len(raw) > 131072:
                row["bounded_response_exceeded"] = True
            elif response.status >= 400:
                data = json.loads(raw)
                error = data.get("error", {})
                text = json.dumps(error).lower()
                row["mentions_max_output_tokens"] = "max_output_tokens" in text
                row["mentions_unsupported"] = "unsupported" in text or "not supported" in text
                # No provider text, headers, credentials or reasoning is persisted.
            else:
                stream = ResponseStream()
                stream.feed(raw, final=True)
                row["complete_response"] = bool(stream.result)
        except Exception as exc:
            row["local_exception_type"] = type(exc).__name__
        finally:
            connection.close()
        row["elapsed_seconds"] = round(time.monotonic() - started, 3)
        rows.append(row)
    unchanged = [p.read_bytes() if p.exists() else None for p in protected] == before
    result = {"purpose": "Separate fixed two-request constant-output diagnostic; not evaluation or replacement runs",
              "rows": rows, "settings_and_auth_bytes_unchanged": unchanged}
    write_json(Path("artifacts/coverage-parameter-diagnostic.json"), result, replace=False)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
