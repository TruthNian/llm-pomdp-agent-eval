"""Standalone readable full trajectories, including executable SQL patches."""
import argparse
import html
import json
from pathlib import Path


def esc(value):
    return html.escape(str(value))


def block(value):
    return '<pre>'+esc(json.dumps(value, ensure_ascii=False, indent=2))+'</pre>'


def render(data):
    overview, sections = [], []
    for i, record in enumerate(data["records"], 1):
        grade, agent = record["grade"], record["agent"]
        model = agent["kind"] in ("responses", "chat")
        status = "已交付" if grade["success"] else "未交付"
        duration = f'{record["elapsed_seconds"]:.1f} 秒' if model else "未测量（脚本）"
        usage = record.get("usage")
        tokens = f'{usage["input_tokens"]:,} / {usage["output_tokens"]:,}' if usage and usage["requests"] == usage["requests_with_usage"] else "未知或不完整" if model else "不适用"
        overview.append(f'<tr><td><a href="#e{i}">{esc(agent["name"])}</a><small>{esc(record["profile"])}</small></td><td>{status}</td><td>{grade["steps"]}</td><td>{duration}</td><td>{grade["position_errors"]} / {grade["report_errors"]}</td></tr>')
        steps = []
        for n, event in enumerate(record["events"], 1):
            action, observation = event["action"], event["observation"]
            audit = record["service_evidence"]["calls"][n-1]["response"]["audit"]
            result = observation["result"]
            outcome = "PASS" if result.get("passed") else "FAIL" if result.get("passed") is False else "错误" if "error" in result else "已执行"
            command = action.get("command", "无效动作") if isinstance(action, dict) else "无效动作"
            steps.append(f'<article><div class="step"><b>{n:02d} · {esc(command)}</b><span>{outcome}</span><small>逐笔差异 {audit["position_errors"]} · 汇总差异 {audit["report_errors"]} · 待收事件 {audit["pending_receipts"]}</small></div><details><summary>完整动作、SQL 与实际收到的反馈</summary>{block(event)}</details></article>')
        requests = record.get("request_audit", [])
        mismatches = sum(r.get("reported_model_matches_request") is False for r in requests)
        unknown = sum(r.get("reported_model_matches_request") is None for r in requests)
        identity = f'模型名称不匹配 {mismatches}/{len(requests)}；未知 {unknown}。服务端名称不是权重认证。' if model else '手写公共契约策略，不能代表模型能力。'
        state = next((s for s in data.get("fresh_final_states", []) if s["agent"] == agent["name"] and s["case_id"] == record["case_id"]), None)
        sections.append(f'<section id="e{i}"><h2>{esc(agent["name"])} · {esc(record["profile"])}</h2><p class="status">{status} · {grade["steps"]}/{grade["budget"]} 步 · {duration}</p><p>输入 / 输出 token：{tokens}；无效动作 {grade["invalid_actions"]}；终止原因 {esc(grade["termination"])}。</p><p>{identity}</p>'
                        + (f'<p class="warning">错误：{esc(record["error"])}。接入错误不证明认知难度。</p>' if record.get("error") else '')
                        + '<details><summary>最初的公共任务与观察</summary>'+block({"contract": record["contract"], "observation": record["initial_observation"]})+'</details>'
                        + ''.join(steps)
                        + ('<details><summary>'+('重新执行后的完整数据库（散列与原记录一致）' if record['events'] else '零动作：新建的初始数据库，仅供参考；原尝试未创建业务运行时')+'</summary>'+block(state["tables"])+ '</details>' if state else '')+'</section>')
    settings = data.get("settings_check")
    settings_view = ('<p class="warning">配置不变性检查未通过；以下仅作带有条件异常的集成证据。</p>' if settings and not settings["settings_and_auth_bytes_unchanged"] else '')
    if settings:
        settings_view += '<details><summary>采集前后配置与认证文件逐项不变性</summary>'+block(settings)+'</details>'
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>跨组件对账修复 · 完整轨迹</title><style>
body{margin:0;background:#eef2f5;color:#182c3c;font:16px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:40px auto;padding:0 22px}h1{font-size:32px}h2{font-size:21px;overflow-wrap:anywhere}section{background:#fff;padding:24px;border:1px solid #cdd9e2;border-radius:10px;margin:25px 0}p{max-width:960px;color:#42566a}.status{font-weight:700;color:#175f5c}table{width:100%;border-collapse:collapse;text-align:left}th,td{padding:12px;border-bottom:1px solid #dce4eb;font-size:14px}small{display:block;color:#637888}.step{display:flex;gap:20px;align-items:center;flex-wrap:wrap}article{padding:15px 0;border-bottom:1px solid #dce4eb}summary{cursor:pointer;color:#17608b;font-size:14px}pre{background:#f2f5f8;padding:16px;font:12px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:550px;overflow:auto}.warning{padding:12px;border:2px solid #a2681e}a{color:#17608b}.scroll{overflow:auto}@media(max-width:700px){main{padding:0 12px}section{padding:14px}.step{gap:8px}h1{font-size:26px}}
</style><main><header><small>POMDP · EXECUTABLE COMPONENT REPAIR</small><h1>修复处理规则，并交付正确账目</h1><p>两类构造的业务契约：支付快照与可更正流水。操作方读取代码和业务证据，实际修改 SQL，测试、部署、回填、验证并交付。这里完整保留每一步反馈。步骤旁的差异指标来自评测器，未预先提供给模型；逐笔差异按缺失行与多余行分别计数，并非错误对象数。</p><p>这是开发校准，不是生产事故或模型排名。通过验收不等于达到前沿难度；探针批次也不是独立任务。新增代码与测试数量不用于证明模型区分度。</p></header>''' + settings_view + '<section><h2>全部结果</h2><div class="scroll"><table><thead><tr><th>路由 / 对照与契约</th><th>交付</th><th>动作</th><th>耗时</th><th>逐笔 / 汇总差异</th></tr></thead><tbody>'+''.join(overview)+'</tbody></table></div></section>'+''.join(sections)+'<footer>冻结源码：'+esc(data["git_revision"])+'。原始记录包含失败、请求审计和缺失用量标记。</footer></main></html>'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(render(json.loads(args.input.read_text(encoding="utf-8"))), encoding="utf-8", newline="\n")
