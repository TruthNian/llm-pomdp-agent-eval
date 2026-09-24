"""Verify and render the retained native-runtime GLM max incident attempt."""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
from collections import Counter
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


def availability_diagnostic(trace: dict) -> dict:
    """Report refused live requests separately from accepted-work grading."""
    traffic = trace["service_evidence"]["calls"][-1]["response"]["audit"]["traffic"]
    windows = []
    current = None
    errors = Counter()
    accepted = failed = 0
    for batch in traffic:
        refused = [item["response"] for item in batch["commands"]
                   if item["response"].get("status") not in (200, 201)]
        accepted += len(batch["commands"]) - len(refused)
        failed += len(refused)
        for response in refused:
            errors[response.get("error", str(response.get("status")))] += 1
        if refused:
            if current is None:
                current = {"first_elapsed": batch["elapsed"], "last_elapsed": batch["elapsed"],
                           "batches": 0, "failed_commands": 0}
            current["last_elapsed"] = batch["elapsed"]
            current["batches"] += 1
            current["failed_commands"] += len(refused)
        elif current is not None:
            windows.append(current)
            current = None
    if current is not None:
        windows.append(current)
    return {"traffic_batches": len(traffic), "accepted_commands": accepted,
            "failed_commands": failed, "failed_batches": sum(w["batches"] for w in windows),
            "failure_response_errors": dict(sorted(errors.items())), "failure_windows": windows}


def load() -> tuple[dict, dict]:
    # Git stores the frozen JSON with LF; Windows checkout may convert it to CRLF.
    plan_bytes = (ROOT / "plan.json").read_bytes().replace(b"\r\n", b"\n")
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
    if availability_diagnostic(trace) != receipt["availability_diagnostic"]:
        raise ValueError("Live customer write-failure accounting differs")
    if trace["grade"]["traffic_write_failures"] != receipt["availability_diagnostic"]["failed_commands"]:
        raise ValueError("The grade and live customer failure count differ")
    with tempfile.TemporaryDirectory(prefix="pomdp-glm-replay-") as temp:
        path = Path(temp) / "trace.json"
        path.write_bytes(raw)
        if replay(path) != receipt["grade"]:
            raise ValueError("Independent business replay differs")
    return trace, receipt


def render(trace: dict, receipt: dict) -> None:
    def esc(value):
        escaped = html.escape(str(value).replace("\r\n", "\n"), quote=True)
        # Keep terminal spacing visible in <pre> without adding Git whitespace errors.
        return re.sub(r"[ \t]+(?=\n|$)",
                      lambda match: "".join("&#32;" if char == " " else "&#9;"
                                            for char in match.group()), escaped)
    contract = trace["contract"]
    sections = [
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>GLM-5.3 max 原生代理事故轨迹</title>",
        "<style>body{font:16px/1.55 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18212b}"
        "h1,h2{line-height:1.25}details{border:1px solid #cbd5e1;border-radius:8px;margin:1rem 0;padding:.6rem 1rem}"
        "summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6fa;padding:1rem;border-radius:6px}"
        "table{border-collapse:collapse}td,th{border:1px solid #cbd5e1;padding:.4rem .7rem;text-align:left}"
        ".fail{color:#a11919}.pass{color:#087647}.muted{color:#526173}</style>",
        "<h1>GLM-5.3 max 正常代理运行时：完整事故轨迹</h1>",
        "<p class='muted'>模型只收到下方交接信息与每步工具输出。末尾业务评分由评测器独立产生，未返给模型。</p>",
        "<h2>公开交接</h2><pre>" + esc("\n".join((trace["initial_observation"]["result"]["alert"],
                                                contract["task"], contract["workspace"], contract["limits"]))) + "</pre>",
        "<h2>结果</h2><table><tr><th>动作</th><th>交接</th><th>已接受工作验收</th><th>订单错误</th><th>漏发</th><th>运行期间写失败</th></tr>",
        "<tr><td>" + str(receipt["actions"]) + "/200</td><td>主动 finish</td><td class='" +
        ("pass'>通过" if trace["grade"]["success"] else "fail'>失败") + "</td><td>" +
        str(trace["grade"]["phases"][-1]["order_errors"]) + "</td><td>" +
        str(trace["grade"]["phases"][-1]["missing_bookings"]) + "</td><td class='fail'>" +
        str(trace["grade"]["traffic_write_failures"]) + "</td></tr></table>",
        "<p>通过只覆盖收到成功收据的客户指令；维护期间失败请求按原样保留，不能称作零中断交付。</p>",
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
    (ROOT / "trajectories.html").write_bytes("\n".join(sections).replace("\r\n", "\n").encode("utf-8"))


if __name__ == "__main__":
    episode, summary = load()
    if len(sys.argv) > 1 and sys.argv[1] == "render":
        render(episode, summary)
    elif len(sys.argv) > 1:
        raise SystemExit("Use no argument to verify, or render to rebuild the HTML trajectory")
    print(json.dumps({"verified": True, "actions": summary["actions"],
                      "success": summary["grade"]["success"],
                      "order_errors": summary["grade"]["phases"][-1]["order_errors"],
                      "missing_bookings": summary["grade"]["phases"][-1]["missing_bookings"],
                      "traffic_write_failures": summary["availability_diagnostic"]["failed_commands"]},
                     ensure_ascii=False))
