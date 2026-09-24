"""Verify and render the retained native-runtime GLM incident attempt."""
from __future__ import annotations

import gzip
import hashlib
import html
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))

from tools.native_codex_stream import verify as replay  # noqa: E402
from pomdp_bench.stream_runtime import initial_batches, matches, obligations  # noqa: E402


def error_attribution(trace: dict) -> list[dict]:
    audit = trace["service_evidence"]["calls"][-1]["response"]["audit"]
    alpha = initial_batches(audit["seed"])[1]
    alpha_references = {item["reference"] for item in alpha}
    alpha_requests = {item["request_id"] for item in alpha}
    records = list(audit["initial"]) + [item for batch in audit["traffic"] for item in batch["commands"]]
    result = []
    for phase in audit["phases"]:
        records += phase["commands"]
        orders, releases, _ = obligations(records)
        wrong = [item["reference"] for item in phase["reads"]
                 if item["response"].get("status") != 200 or
                 not matches(orders[item["reference"]], item["response"].get("body"))]
        booked = {item["client_reference"] for item in phase["bookings"]}
        missing = [request for request in releases if request not in booked]
        result.append({"wrong_orders": len(wrong),
                       "wrong_orders_from_initial_alpha": sum(ref in alpha_references for ref in wrong),
                       "missing_bookings": len(missing),
                       "missing_bookings_from_initial_alpha": sum(request in alpha_requests for request in missing)})
    return result


def load() -> tuple[dict, dict]:
    plan_bytes = (ROOT / "plan.json").read_bytes()
    receipt = json.loads((ROOT / "receipt.json").read_text(encoding="utf-8"))
    compressed = (ROOT / "trace.json.gz").read_bytes()
    raw = gzip.decompress(compressed)
    for label, value, expected in (
        ("plan", plan_bytes, receipt["plan_sha256"]),
        ("compressed trace", compressed, receipt["trace_gzip_sha256"]),
        ("trace", raw, receipt["trace_json_sha256"]),
    ):
        if hashlib.sha256(value).hexdigest() != expected:
            raise ValueError(f"{label} fingerprint changed")
    plan = json.loads(plan_bytes)
    trace = json.loads(raw)
    if (trace["model"] != plan["model"]["requested"] or
            trace["provider"] != plan["model"]["provider"] or
            trace["effort"] != plan["model"]["reasoning_effort"] or
            trace["runtime_image"] != plan["runtime"]["image"] or
            trace["case"] != plan["case"] or
            trace["session"]["instruction_sources"] != [] or
            trace["session"]["fallback_allowed"] is not False):
        raise ValueError("Frozen plan and observed runtime differ")
    if (len(trace["events"]) != receipt["actions"] or
            trace["events"][-1]["action"] != {"command": "finish"} or
            trace["grade"] != receipt["grade"] or
            trace["usage"] != receipt["observed_usage_through_handover"] or
            trace["error"] != receipt["local_error"]):
        raise ValueError("Receipt and retained episode differ")
    if error_attribution(trace) != receipt["error_attribution"]:
        raise ValueError("Accepted-branch error attribution differs")
    with tempfile.TemporaryDirectory(prefix="pomdp-glm-replay-") as temp:
        path = Path(temp) / "trace.json"
        path.write_bytes(raw)
        if replay(path) != receipt["grade"]:
            raise ValueError("Independent business replay differs")
    return trace, receipt


def render(trace: dict, receipt: dict) -> None:
    esc = lambda value: html.escape(str(value), quote=True)
    contract = trace["contract"]
    sections = [
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>GLM-5.3 原生代理事故轨迹</title>",
        "<style>body{font:16px/1.55 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18212b}"
        "h1,h2{line-height:1.25}details{border:1px solid #cbd5e1;border-radius:8px;margin:1rem 0;padding:.6rem 1rem}"
        "summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6fa;padding:1rem;border-radius:6px}"
        "table{border-collapse:collapse}td,th{border:1px solid #cbd5e1;padding:.4rem .7rem;text-align:left}"
        ".fail{color:#a11919}.muted{color:#526173}</style>",
        "<h1>GLM-5.3 正常代理运行时：完整事故轨迹</h1>",
        "<p class='muted'>模型只收到下方交接信息与每步工具输出。末尾业务评分由评测器独立产生，未返给模型。</p>",
        "<h2>公开交接</h2><pre>" + esc("\n".join((trace["initial_observation"]["result"]["alert"],
                                                contract["task"], contract["workspace"], contract["limits"]))) + "</pre>",
        "<h2>结果</h2><table><tr><th>动作</th><th>交接</th><th>业务通过</th><th>订单错误</th><th>漏发</th></tr>",
        "<tr><td>" + str(receipt["actions"]) + "/200</td><td>主动 finish</td><td class='fail'>否</td><td>" +
        str(trace["grade"]["phases"][-1]["order_errors"]) + "</td><td>" +
        str(trace["grade"]["phases"][-1]["missing_bookings"]) + "</td></tr></table>",
        "<h2>逐步动作与返回</h2>",
    ]
    for index, event in enumerate(trace["events"], 1):
        action = event["action"]
        result = event["observation"]["result"]
        code = result.get("exit_code")
        label = f"第 {index} 步 · {action['command']}" + (f" · 退出码 {code}" if code is not None else "")
        output = result.get("output") if "output" in result else json.dumps(result, ensure_ascii=False, indent=2)
        sections.append("<details><summary>" + esc(label) + "</summary><h3>命令</h3><pre>" +
                        esc(action.get("target", action["command"])) + "</pre><h3>环境返回</h3><pre>" +
                        esc(output) + "</pre></details>")
    sections += ["<h2>交接后独立评分</h2><pre>" + esc(json.dumps(trace["grade"], ensure_ascii=False, indent=2)) +
                 "</pre></html>"]
    (ROOT / "trajectories.html").write_text("\n".join(sections), encoding="utf-8")


if __name__ == "__main__":
    episode, summary = load()
    if len(sys.argv) > 1 and sys.argv[1] == "render":
        render(episode, summary)
    elif len(sys.argv) > 1:
        raise SystemExit("Use no argument to verify, or render to rebuild the HTML trajectory")
    print(json.dumps({"verified": True, "actions": summary["actions"],
                      "success": summary["grade"]["success"],
                      "order_errors": summary["grade"]["phases"][-1]["order_errors"],
                      "missing_bookings": summary["grade"]["phases"][-1]["missing_bookings"]}, ensure_ascii=False))
