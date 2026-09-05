"""Canonical technical-report payload for the Stage B1 retrospective appendix."""
from datetime import datetime, timezone
import json
import sqlite3

from build_retrospective_statistics import ROOT, REPORT, digest, load, write_json


def main():
    report = load(REPORT)
    verified = load(ROOT/'reports/bizhallu_statistics_v2_local_validation.json')
    if (verified['num_failures'] or not verified['local_checks'].startswith('100_answers_205_spans')
            or verified.get('validated_report_text_sha256') != digest(REPORT)):
        raise ValueError('A successful local replay is required before building the report')
    names = {'one_minus_min_top2_margin':'Top-2 margin', 'mean_token_entropy':'Token entropy',
             'dev_fact_type_prior':'Dev fact-type prior', 'all_positive':'All positive', 'all_negative':'All negative'}
    selected = {r['signal']:r for r in report['metrics'] if r['arm']=='saved_trace_precision' and r['split']=='test' and r['signal'] in names}
    metrics = [{'method':names[s], **{k:f"{selected[s][k]:.4f}" for k in ['average_precision','f1','balanced_accuracy','mcc']},
                'confusion':' / '.join(str(selected[s][k]) for k in ['tp','fp','tn','fn'])} for s in names]
    differences = [{'method':names[r['signal']], 'reference':names[r['reference']], 'metric':r['metric'],
                    'difference':f"{r['point_difference']:+.4f}", 'interval':f"[{r['lower_95']:+.4f}, {r['upper_95']:+.4f}]"}
                   for r in report['paired_intervals'][0]['intervals'] if r['metric'] in ['f1','average_precision']]
    precision = []
    for s in ['mean_token_entropy','one_minus_min_top2_margin','mean_spilled_probability_mass_after_top2']:
        old = next(r for r in report['legacy_comparison'] if r['signal']==s and r['split']=='test')
        raw = next(r for r in report['metrics'] if r['signal']==s and r['split']=='test' and r['arm']=='saved_trace_precision')
        precision.append({'signal':names.get(s,'Non-top2 probability mass'), 'legacy':f"{old['published_legacy_auprc']:.6f}",
            'tied':f"{old['tied_score_average_precision']:.6f}", 'trace':f"{raw['average_precision']:.6f}"})
    timestamp = datetime.now(timezone.utc).isoformat()
    query = 'SELECT dataset, row_json FROM stage_b1_report_rows ORDER BY ordinal'
    sources = [{'id':'statistics','label':'BizHallu B1 source replay and retrospective statistics',
                'path':'reports/bizhallu_statistics_v2_report.json',
                'query':{'engine':'SQLite (report projection only)', 'sql':query,
                    'description':'Python statistical calculations from build_retrospective_statistics.py; this SELECT copies reviewed rows unchanged, not a SQL metric calculation.',
                    'tables_used':['stage_b1_report_rows','results/full100_statistics_v2_scores.csv','results/full100_statistics_v2_metrics.csv']}}]
    def md(key, text):
        return {'id':key,'type':'markdown','body':text,'sourceId':'statistics'}
    def table(key, title, columns):
        return {'id':key,'title':title,'dataset':key,'sourceId':'statistics','layout':'full',
                'columns':[{'field':field,'label':label,'type':'text'} for field,label in columns]}
    artifact = {'surface':'report','manifest':{'version':1,'surface':'report',
        'title':'BizHallu B1：从最好分数转向可检验的比较',
        'description':'历史 205 个临时 spans 的统计修订；非确认性研究、非新模型结果。',
        'generatedAt':timestamp,'sources':sources,'cards':[],
        'charts':[{'id':'f1','title':'103 个 test spans 的 F1 点估计','type':'bar','dataset':'f1','sourceId':'statistics','layout':'full',
                   'encodings':{'x':{'field':'method','type':'nominal','label':'检测信号与参照'},'y':{'field':'value','type':'quantitative','label':'F1'}},'valueFormat':'number'}],
        'tables':[table('metrics','同一批事实片段，不同评估角度',[('method','方法'),('average_precision','AP'),('f1','F1'),('balanced_accuracy','Balanced accuracy'),('mcc','MCC'),('confusion','TP / FP / TN / FN')]),
                  table('differences','18 个问题的配对 bootstrap 差值',[('method','信号'),('reference','参照'),('metric','指标'),('difference','差值'),('interval','探索性 95% 区间')]),
                  table('precision','公式修正与分数精度分开比较',[('signal','信号'),('legacy','历史 AP'),('tied','原分数 + tied AP'),('trace','trace 精度 + tied AP')])],
        'blocks':[
            md('summary','## 核心结论：内部信号有信息，但原 F1 不足以证明优势\n\n在相同的 103 个 test spans 上，仅从 dev 学习的事实类型参照 F1 为 **0.8356**，高于 entropy 的 **0.7794**；top-2 margin 的 AP 为 **0.8351**，仍高于该参照的 **0.7598**。两种结果回答不同问题，不能合成“某方法全面更好”。\n\n这是一份保留旧结果的回顾性附表，不是新的确认性实验。没有运行 Qwen，也没有改变 205 个临时标签。'),
            md('comparison','## 事实类型构成影响了固定阈值结果\n\n图中 F1 是点估计，不包含显著性结论。事实类型参照使用已有的 fact_type，不读取 test 标签来拟合；其主要收益是将 18 个正确的 month spans 判为负类。在当前 test 上，其二分类预测恰好等同于“month 判负，其余判正”。因此它是检验样本构成的参照，不是自动识别任意商业错误的新系统。\n\n现有类型还包括 malformed_number、unsupported_business_claim 等带有正确性提示的名称。其输入条件不同于单纯 logits 检测器；不能把这个较高的 F1 说成公平算法对比的胜出。'),
            {'id':'f1_chart','type':'chart','chartId':'f1','layout':'full'},
            md('metric_reading','AP 衡量排序质量；F1 结合正类 precision 和 recall；balanced accuracy 对两类召回等权；MCC 同时利用四格混淆矩阵。正类沿用历史定义：hallucinated_key_fact 或 unsupported_claim。全正预测的 F1 已达到 0.7439，不能只看 detector 的 F1 绝对值。'),
            {'id':'metrics_table','type':'table','tableId':'metrics','layout':'full'},
            md('uncertainty','## 相对全正参照的 F1 改善仍不确定\n\n每次对 18 个问题整组重采样，在同一份样本上同时重算 detector 和参照，再求差值，共 5,000 次。dev 阈值保持固定。Entropy 的 F1 差值为 +0.0355，95% 区间为 [-0.0356, +0.1047]，跨过零。它没有证明优于全正参照；也不能反过来证明两者等效。下表 AP 与 F1 分列，不把排序与分类混为一谈。'),
            {'id':'differences_table','type':'table','tableId':'differences','layout':'full'},
            md('scope','## 范围与分母\n\n历史 Online Retail、Qwen3-0.6B、100 个生成回答。标注覆盖 35 题：dev 为 17 题／102 spans，test 为完整 18 题／103 spans。缺失的 q_0048 属于 dev。全部 205 spans 包含 83 correct、121 hallucinated、1 unsupported。仅 15 个展示 spans 有额外 assistant review，没有独立人类一致性结果。\n\n当前分析依赖已识别的 spans，不代表整段回答正确率、自动事实抽取能力或真实业务错误率。历史业务定义按 v1 保留；阶段 A 的新口径敏感性不用于偷偷修改本表标签。'),
            md('method','## 公式修复不覆盖历史\n\nAP 先按相同分数分组再计算累计 precision，不再随并列样本的输入顺序改变；采用非插值 average precision，而非 PR 曲线梯形面积。方法与 scikit-learn 定义对照。新模块拒绝 NaN/Inf、重复 ID、混入非 dev/test 的输入。所有阈值和事实类型错误率只由 dev 拟合。\n\n保存的 traces 重建了 100 条完整回答，并重放 205 个 spans 的字符覆盖和 12 组原六位小数分数。新计算用保存值的可用精度聚合，不在中途舍入。下表分开展示公式和精度的影响；12 个信号的 test 混淆矩阵均没有变化。'),
            {'id':'precision_table','type':'table','tableId':'precision','layout':'full'},
            md('signals','## 不能把数学等价信号当作独立发现\n\n`logsumexp(logits) − selected_logit` 就是该 token 的 NLL；span mean 两者相关系数约 0.999999999978，细微差异来自数值计算。`1 − top1 probability` 是普通置信度变换。原能量列仅为历史诊断保留，不能把它们与 NLL 的一致性当成独立方法的相互验证。真正 adjacent-step Spilled Energy 的论文公式与时间索引复核留在阶段 F。\n\n这些概率来自生成完成后的 raw teacher-forced logits，不是温度、top-p、top-k 处理后的采样分布。“不提前舍入”也不等于恢复保存前的高精度 logits。'),
            md('limits','## 依赖性与标签仍限制研究结论\n\n- 按不同证据内容重采样有 15 组；按共享月份及跨月问题连通后仅剩 2 组。后者还包含 35 题中 dev 的连接关系，因此是保守的依赖性诊断，不能当作可靠的月份级置信区间。\n- bootstrap 不消除挑选 test 最好信号、临时标签错误、事实漏标和已知跨 split 证据重复。其区间条件于现有 dev 阈值，并未包含重新拟合的变异。\n- 所有来源标签、业务定义和原生成保持原样；完整产品—排名—金额关系尚未重新标注。\n- q_0048 仍未标注，不能假定它全部正确来补齐。\n- 保留原 Unicode fallback 规则并逐条对照完整回答，不声称已解决通用 tokenizer 对齐。'),
            md('validation','## 验证范围明确分层\n\n公共校验从轻量 CSV 重算全部 60 行指标、dev 拟合和 15,000 次配对 cluster draws，并核对来源与输出 hash。`--require-local` 另行检查未上传的原 traces；两者均不运行模型。独立测试包含并列样本换序、恒定预测、单类别、非有限值、dev/test 隔离和配对重采样；本地还与 scikit-learn 做数值交叉检查。\n\nHTML 采用规范化报告数据构建；当前浏览器安全限制阻止视觉验收，所以交互和移动端显示仍需人工打开确认，不能把结构检查等同于视觉检查。'),
            md('next','## 下一批：先完善事实单位，再补 dev 敏感性\n\nB1 到这里验收。B2/C 用 5 条历史回答校准“实体—排名—金额—时期”关系规则，制作隐藏旧标签和 detector scores 的复核材料；q_0048 纳入该流程。完成版本化标签后，再单独分析 dev 阈值变化，不覆写当前结果。之后才实现与 labels 隔离的 top3 verifier。'),
            md('questions','## 需要继续回答的问题\n\n1. 相对于事实类型参照，内部信号在同类业务事实中还增加了多少信息？\n2. 一个业务关系错绑产生多个错误 spans 时，怎样避免重复计数和不公平的信息时点比较？\n3. 独立复核及新的 context-separated 数据会怎样改变区间？\n\n保留 internal uncertainty、语义一致性、attention 方法和显式证据核验的学术比较路线；当前结果不预设任何一类一定获胜。')
        ]}, 'snapshot':{'version':1,'generatedAt':timestamp,'status':'ready','datasets':{
            'metrics':metrics,'differences':differences,'precision':precision,
            'f1':[{'method':names[s],'value':selected[s]['f1']} for s in names]}},'sources':sources,
        'package_info':{'root':'reports','manifestPath':'bizhallu_statistics_v2_artifact.json','snapshotPath':'bizhallu_statistics_v2_artifact.json'}}
    datasets = artifact['snapshot']['datasets']
    with sqlite3.connect(':memory:') as conn:
        conn.execute('CREATE TABLE stage_b1_report_rows (ordinal INTEGER PRIMARY KEY, dataset TEXT, row_json TEXT)')
        conn.executemany('INSERT INTO stage_b1_report_rows (dataset,row_json) VALUES (?,?)',[(k,json.dumps(r,ensure_ascii=True,allow_nan=False)) for k,rows in datasets.items() for r in rows])
        projected = {}
        for name,row in conn.execute(query):
            projected.setdefault(name,[]).append(json.loads(row))
    if projected != datasets:
        raise ValueError('Report projection altered reviewed data')
    write_json(ROOT/'reports/bizhallu_statistics_v2_artifact.json',artifact)


if __name__ == '__main__':
    main()
