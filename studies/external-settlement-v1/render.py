"""Readable complete action timelines from recorded evidence; no new execution."""
import argparse
import html
import json
from pathlib import Path


def esc(value):
    return html.escape(str(value))


def render(data):
    sections = []
    for record in data["records"]:
        grade = record["grade"]
        status = "处理中" if grade["termination"] is None else ("通过交付验收" if grade["success"] else "未完成交付")
        rows = []
        for i, event in enumerate(record["events"]):
            call = record["service_evidence"]["calls"][i]
            audit = call["response"]["audit"]
            excess = sum(max(0, m["external_cents"] - m["amount_cents"]) for m in audit["external_mismatches"])
            detail = esc(json.dumps({"action": event["action"], "observation": event["observation"]}, ensure_ascii=False, indent=2))
            action = event["action"] if isinstance(event["action"], dict) else {}
            command = action.get("command", "无效命令")
            target = action.get("target", "")
            short = target if isinstance(target, str) else json.dumps(target, ensure_ascii=False)
            result = event["observation"]["result"]
            outcome = "PASS" if result.get("passed") is True else "FAIL" if result.get("passed") is False else "错误" if "error" in result else "已执行"
            rows.append(f'<tr><td>{i+1}</td><td><b>{esc(command)}</b><span>{esc(short[:180])}</span></td><td>{outcome}</td><td>{len(audit["external_mismatches"])}</td><td>{audit["unsettled_messages"]}</td><td>{excess:,}</td></tr><tr class="detail"><td colspan="6"><details><summary>查看本步完整动作与模型实际收到的反馈</summary><pre>{detail}</pre></details></td></tr>')
        usage = record.get("usage")
        tokens = (f'{usage["input_tokens"]:,} / {usage["output_tokens"]:,}' if usage and usage["requests"] == usage["requests_with_usage"] else "不完整或未知")
        seconds = f'{record.get("elapsed_seconds", 0):.1f}'
        public_start = esc(json.dumps({"initial_observation": record["initial_observation"], "contract": record["contract"]}, ensure_ascii=False, indent=2))
        audit = record.get("request_audit", [])
        aliases = sum(a.get("reported_model_matches_request") is False for a in audit)
        identity = f"服务端模型名与请求名不一致：{aliases} / {len(audit)} 次。" if audit else "脚本对照，无模型请求。"
        error_view = ('<p><b>终止错误：</b>' + esc(record["error"]) + '。该接入错误不能作为任务认知难度的证据。</p>') if record.get("error") else ''
        final = next((s for s in data.get("fresh_final_states", []) if s["agent"] == record["agent"]["name"]), None)
        final_view = ('<details><summary>查看独立重执行的最终数据库（摘要与原始轨迹一致）</summary><pre>' + esc(json.dumps(final["tables"], ensure_ascii=False, indent=2)) + '</pre></details>') if final else ''
        sections.append(f'''<section><div class="title"><h2>{esc(record['agent']['name'])}</h2><strong class="{'pass' if grade['success'] else 'other'}">{status}</strong></div>
<div class="stats"><div><small>动作</small><b>{grade['steps']} / {grade['budget']}</b></div><div><small>模型与环境总耗时</small><b>{seconds} 秒</b></div><div><small>输入 / 输出 token</small><b>{tokens}</b></div><div><small>新增不可逆多付款</small><b>{grade['additional_excess_settled_cents']:,} 分</b></div></div>
<p>最终本地不一致订单：{grade['book_mismatches']}；外部不一致订单：{grade['external_mismatches']}；待终结操作：{grade['pending_operations']}；未完成消息：{grade['unsettled_messages']}；外部超额扣款暴露：{grade['external_excess_cent_ticks']} 分·tick；终止原因：{esc(grade['termination'])}。</p>
<p>{identity} 名称核对不能认证实际权重。</p>
{error_view}
<details><summary>模型最初收到的事故目标和操作契约</summary><pre>{public_start}</pre></details>
<div class="scroll"><table><thead><tr><th>步骤</th><th>模型动作</th><th>反馈</th><th>外部不一致订单</th><th>未完成消息</th><th>当前超额扣款 / 分</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>{final_view}</section>''')
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>外部结算完整轨迹</title><style>
body{font:16px/1.65 system-ui,sans-serif;background:#f3f5f8;color:#172336;margin:0}main{max-width:1200px;margin:50px auto;padding:0 24px}h1{font-size:34px;letter-spacing:-1px;margin-bottom:12px}h2{font-size:22px}p{max-width:960px;color:#42536b}.eyebrow{font-weight:700;color:#2266aa;letter-spacing:2px;font-size:13px}.intro{padding-bottom:24px;border-bottom:2px solid #173656}section{background:white;border:1px solid #dbe2eb;border-radius:12px;padding:28px;margin:30px 0}.title{display:flex;align-items:center;justify-content:space-between;gap:20px}.pass{color:#16704a}.other{color:#8f5413}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;background:#f4f7fb;padding:18px;border-radius:8px}.stats small,.stats b{display:block}.stats small{font-size:12px;color:#526680}.stats b{font-size:18px}table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}th,td{padding:12px 9px;border-bottom:1px solid #e3e8f0;vertical-align:top}th{color:#536982;white-space:nowrap}td span{display:block;max-width:450px;overflow-wrap:anywhere;color:#536982}td b{color:#173656}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:16px;font:12px/1.55 ui-monospace,monospace;max-height:500px;overflow:auto}.detail td{padding:4px 9px 10px}summary{cursor:pointer;color:#285f97}.scroll{overflow:auto}@media(max-width:750px){main{margin:25px auto;padding:0 12px}section{padding:16px}.stats{grid-template-columns:repeat(2,1fr)}.title{display:block}h1{font-size:28px}}
</style><main><div class="intro"><div class="eyebrow">POMDP · EXTERNAL SETTLEMENT</div><h1>外部付款必须真正完成</h1><p>操作方通过真实 HTTP 服务和两个独立 SQLite 数据库调查、处置与恢复。本地账本改动无法撤销外部付款；退款需要实际结算。下方完整保留每一步行动和反馈；表格中的业务后果由评测器记录，未提前提供给模型。最终修复不会抹去之前造成的损害。</p><p>这是构造的本地结算系统，不涉及真实资金。tick 是固定业务时钟；模型名称是请求路由，token 用量按服务端报告。单场景不构成模型排名或高难度证明。</p></div>''' + ''.join(sections) + '<footer>来源提交：' + esc(data["git_revision"]) + ' · 完整证据（包括失败）在同目录 JSON；该表可能包含脚本对照，身份以每段请求信息为准。</footer></main></html>'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    data = json.loads(args.evidence.read_text(encoding="utf-8"))
    args.out.write_text(render(data), encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
