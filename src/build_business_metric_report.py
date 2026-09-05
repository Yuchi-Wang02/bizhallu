"""Build the canonical portable-report payload from reviewed Stage A artifacts."""
from __future__ import annotations

import csv
import json
import sqlite3

from business_metric_audit import ROOT, REPORT, ROWS, load, write_json
from build_metric_amendment import REPORT as AMENDMENT


def main():
    audit, amendment = load(REPORT), load(AMENDMENT)
    local = load(ROOT / "reports/bizhallu_metric_amendment_v1_1_local_validation.json")
    if local["num_failures"] or local["local_validation"] != "96_questions_48_contexts_and_source_arithmetic_replayed":
        raise ValueError("Local Stage A verification required before the reader-facing report")
    names = {"wording_only": "仅修正业务措辞", "merchandise_scope": "全部交易改为商品范围",
             "stock_code_grain": "商品统一按货号汇总", "merchandise_scope_and_stock_code_grain": "商品范围与货号粒度同时变更",
             "exclude_documented_candidate_pairs": "剔除四条指定候选抵消记录（情景）"}
    summary = [{"scenario": names[r["scenario"]], "questions": r["question_count"], "changed": r["answer_changed"],
                "numeric": r["numeric_changed"], "rank": r["entity_rank_or_direction_changed"]} for r in audit["scenario_summary"]]
    profiles = []
    categories = []
    for key, label in [("historical_eligible_ledger", "历史 Online Retail"), ("strict_prior_window_eligible_ledger", "新研究严格前期窗口")]:
        item = audit[key]
        profiles.append({"dataset": label, "positive": f"{item['positive_transaction_value_gbp']:,.2f}",
                         "negative": f"{item['negative_transaction_value_gbp']:,.2f}", "net": f"{item['net_transaction_value_gbp']:,.2f}",
                         "share": f"{item['non_merchandise_share_of_negative_value_percentage']:.2f}%"})
        for row in item["categories"]:
            categories.append({"dataset": label, "category": row["category"], "lines": row["row_count"],
                               "negative": f"{row['negative_value_gbp']:,.2f}", "net": f"{row['net_value_gbp']:,.2f}"})
    with ROWS.open(encoding="utf-8", newline="") as handle:
        sensitivity = list(csv.DictReader(handle))
    examples = []
    for row in sensitivity:
        if (row["question_id"], row["scenario"]) in {("q_0011", "merchandise_scope"), ("q_0023", "stock_code_grain"),
                ("q_0090", "exclude_documented_candidate_pairs"), ("q_0023", "exclude_documented_candidate_pairs")}:
            examples.append({"question": row["question_id"], "scenario": names[row["scenario"]],
                             "change": "; ".join(f"{x['field']}: {x['old']} -> {x['new']}" for x in json.loads(row["changed_fields"]))})
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    sources = [{"id": "audit", "label": "BizHallu Stage A 源数据与历史问题重算", "path": "reports/bizhallu_business_metric_audit_report.json",
                "query": {"engine": "Python / Decimal and pandas", "description": "src/business_metric_audit.py; original filters and explicit scenario changes; no model inference",
                          "tables_used": ["data/processed/retail_net_revenue_lines.csv", "data/processed/business_questions_gold.jsonl", "data/processed/confirmation_online_retail_ii/strict_window_lines.csv.gz"]}},
               {"id": "amendment", "label": "新研究 v1.1 outcome-blind amendment 与本地重算", "path": "reports/bizhallu_metric_amendment_v1_1_report.json",
                "query": {"engine": "Python", "description": "src/build_metric_amendment.py; src/validate_metric_amendment.py --require-local",
                          "tables_used": ["configs/confirmation_metric_amendment_v1_1.json", "configs/business_metric_contract_v1_1.json"]}}]
    def md(name, text, source="audit"):
        return {"id": name, "type": "markdown", "body": text, "sourceId": source}
    def table(name, title, fields, source="audit"):
        return {"id": name, "title": title, "dataset": name, "sourceId": source, "layout": "full",
                "columns": [{"field": field, "label": label, "type": "text"} for field, label in fields]}
    artifact = {"surface": "report", "manifest": {"version": 1, "surface": "report", "title": "BizHallu 阶段 A：业务口径修订与证据核对",
        "description": "历史计算保留，新研究在生成回答前修订。业务定义检查不是模型性能结果。",
        "generatedAt": timestamp, "sources": sources, "cards": [],
        "charts": [{"id": "scope_changes", "title": "不同口径下，历史答案变化的题数", "type": "bar", "dataset": "changes", "sourceId": "audit", "layout": "full",
                    "encodings": {"x": {"field": "scenario", "type": "nominal", "label": "独立情景"},
                                  "y": {"field": "changed", "type": "quantitative", "label": "答案变化 / 100 题"}}, "valueFormat": "number"}],
        "tables": [table("summary", "五个独立情景，每个保留原来的 100 题", [("scenario", "情景"), ("changed", "答案改变"), ("numeric", "数值改变"), ("rank", "实体／排名／方向改变")]),
                   table("ledger", "正值 + 负值 = 净值（GBP）", [("dataset", "数据范围"), ("positive", "正交易金额"), ("negative", "负交易金额"), ("net", "净交易金额"), ("share", "负金额中的非商品占比")]),
                   table("categories", "非商品行单列，不自动分配至商品", [("dataset", "数据范围"), ("category", "分类规则"), ("lines", "行数"), ("negative", "负交易金额 GBP"), ("net", "净交易金额 GBP")]),
                   table("examples", "历史案例：数值变化不等于原模型答错", [("question", "问题"), ("scenario", "情景"), ("change", "具体变化")])],
        "blocks": [
            md("summary_intro", "## 结论：先把业务含义说清楚，再继续检测研究\n\n阶段 A 已完成历史 100 题重放、五个口径情景和新研究 v1.1 生成。历史 gold、205 个临时 span 标签和检测结果未改动，也没有运行 Qwen。**新研究 96 题的数值和实体答案不变，48 个 contexts 与 split 不变。**\n\n最重要的修订：全部负交易金额不能直接叫作‘退货金额’；商品口径与账目整体口径必须分开。当前可验收的是业务定义与生成链，而不是研究结论已经成立。"),
            md("scope_findings", "## 商品范围改变 58 题，不能仅当作改名\n\n图中的每个情景都独立与原 v1 gold 对比，分母固定为原来 100 题；各柱不能相加。‘仅修正措辞’不改变数值。改为商品范围改变 58 题，合并货号粒度再影响 4 题。四条候选记录的排除只是回顾性 what-if，不是清洗后的新真值。"),
            {"id": "change_chart", "type": "chart", "chartId": "scope_changes", "layout": "full"},
            {"id": "change_table", "type": "table", "tableId": "summary", "layout": "full"},
            md("definitions", "## 分清符号、范围和业务事件\n\n金额采用 GBP；行金额是 quantity × unit price。正／负金额仅按符号划分。沿用原来的去重、单价和描述缺失过滤，缺失客户 ID 不插补，商品范围继续使用已有货号规则。货号规则不是经外部核准的商品主数据。\n\nUCI 将 C 开头发票描述为 cancellation 标记；它与金额符号分开保存，不能据此确定实物退货、原始销售、现金流或利润。新窗口存在一条 C 标记但金额为正的有效行，按正金额保留并披露，不静默删除。"),
            {"id": "ledger_table", "type": "table", "tableId": "ledger", "layout": "full"},
            md("composition", "历史负金额中 46.77% 来自项目分类下的非商品行；新研究完整严格前期窗口为 57.67%。这里的分母是有效行的全部负金额绝对值，不是发票数、行数或确认退货额。新窗口仅披露整体汇总，不泄露封存 contexts 的具体时期。"),
            {"id": "category_table", "type": "table", "tableId": "categories", "layout": "full"},
            md("examples_intro", "## 两类变化分别保留证据\n\nq_0011 在全部交易口径下领先国家为 France，商品范围下变为 EIRE。q_0023 的货号 22502 在按名称拆分与按货号汇总时金额不同；这不是自动证明哪个名称是真正的商品定义。所有历史案例均是开发／敏感性材料，不参与新研究封存评价。"),
            {"id": "examples_table", "type": "table", "tableId": "examples", "layout": "full"},
            md("method", "## 验证不只检查文件是否存在\n\n1. 用原生成函数从保存的有效行重新构造 100 条 gold，逐条比对。\n2. 以原 question filters 重新计算五个情景，不重新抽题。\n3. 用 Decimal 独立从数量与单价聚合账目，不依赖保存的 revenue 列。\n4. 重建并核对全部 48 个 context evidence hashes，重放原 96 题；核验新旧版本字段逆映射、数值、实体、行顺序和归一化证据一致性。\n5. 新研究完成 **798 项源数据算术检查**，并通过独立的 gold/evidence 公式校验。\n6. 公开 CI 只检查 committed artifacts；私有原始数据重算另存 local validation，不把两者混为一谈。", "amendment"),
            md("amendment", f"## Gate 3 已重新核验，其余四个门槛仍未完成\n\n新版本使用明确的 positive / negative transaction value 和 negative-to-positive unit ratio；商品风险问题采用 merchandise net transaction value。旧 v1 保留为历史版本，新的输入由 study protocol 的 active_business_definition 指定。\n\n96 题分配仍为 pilot 12、development 30、confirmation 54。改动前没有新模型回答，因此修订不是依据检测结果调参。新 commitment：`{amendment['amended_question_commitment']}`。\n\n**这不是生成许可。** 模型与 prompt 冻结、独立双人复核、关系抽取／verifier 和封存执行授权仍待完成。", "amendment"),
            md("limits", "## 当前边界与尚未解决的问题\n\n- 历史 0.835073 AUPRC／0.779412 F1 仍是不同信号的探索性最大值，未因本次检查变成确认性结果。\n- 商品／非商品分类存在不确定性；负商品数量也不能自动解释成有原始销售链接的实物退货。\n- 四条抵消候选记录按明确记录组合分析；相近时间和相同金额不足以证实跨货号冲销。原始数据不删，历史 gold 不改。\n- 商品名称可能变化，货号合并仅是敏感性检查；排名结论需要结合粒度解释。\n- 关系标注、标准 AP／置信区间与独立 verifier 尚未在这一批实现。"),
            md("next", "## 下一步：先修统计核心，再校准关系标签\n\n阶段 B：标准并列分数 AP、全正／全负参照、dev-only fact-type prior、MCC、balanced accuracy 与配对聚类区间。重算作为独立版本附表，不覆盖历史指标。随后在阶段 C 用 5 条历史回答校准业务关系标注，开展隐藏旧标签与 scores 的本人复核。\n\n需要你确认的业务选择：账目整体问题采用中性的交易金额口径；商品风险问题明确商品范围。需要后续合作者帮助判断：商品主数据、跨货号调整是否能可靠链接，以及什么关系粒度适合人工评审。", "amendment")
        ]},
        "snapshot": {"version": 1, "generatedAt": timestamp, "status": "ready", "datasets": {
            "summary": summary, "changes": [{"scenario": x["scenario"], "changed": x["changed"]} for x in summary],
            "ledger": profiles, "categories": categories, "examples": examples}},
        "sources": sources, "package_info": {"root": "reports", "manifestPath": "bizhallu_stage_a_artifact.json", "snapshotPath": "bizhallu_stage_a_artifact.json"}}
    # The portable reader requires query-backed provenance. This is an actual
    # presentation-only SQLite projection; the source analysis above stays Python.
    datasets = artifact["snapshot"]["datasets"]
    datasets["amendment_status"] = [{k: amendment[k] for k in ["question_count", "context_count", "independent_source_arithmetic_checks", "amended_question_commitment"]}]
    query = "SELECT dataset, row_json FROM stage_a_report_rows ORDER BY ordinal"
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE stage_a_report_rows (ordinal INTEGER PRIMARY KEY, dataset TEXT, row_json TEXT)")
        connection.executemany("INSERT INTO stage_a_report_rows (dataset, row_json) VALUES (?, ?)",
            [(name, json.dumps(row, ensure_ascii=True, allow_nan=False)) for name, data in datasets.items() for row in data])
        projected = {}
        for name, row in connection.execute(query):
            projected.setdefault(name, []).append(json.loads(row))
    if projected != datasets:
        raise ValueError("Report projection changed reviewed values")
    artifact["snapshot"]["datasets"] = projected
    for source in sources:
        source["query"].update(engine="SQLite (in-memory report projection)", sql=query,
            tables_used=["stage_a_report_rows", *source["query"]["tables_used"]])
        source["query"]["description"] += "; SELECT copies reviewed report rows unchanged; it does not recalculate the underlying business metrics."
    write_json(ROOT / "reports/bizhallu_stage_a_artifact.json", artifact)
    print("Canonical technical report payload generated; render with the portable report builder.")


if __name__ == "__main__":
    main()
