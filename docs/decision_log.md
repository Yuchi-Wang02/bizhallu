# Decision log

Owner decisions for the decision-battery research line, one row per decision: date, decision,
reason. Only decisions made by the project owner are listed. Designs proposed by an AI assistant
count as decisions only after the owner approves them, and the approval is recorded here.
Entries are appended, never edited.

## Before gate G0

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-09-29 | Work proceeds one step at a time, without a deadline. | Owner instruction. |
| 2026-09-29 | Two human raters label the spans. The owner is not one of them. | Owner instruction. |
| 2026-09-29 | The project direction is approved: an audit method for AI-generated business analysis that compares verification approaches on business-fact spans. | Owner approval of the proposed direction. |
| 2026-09-29 | A higher-capability model reviews and plans; routine task cards may be executed by a lower-cost model. | Owner instruction. |

## Gate G0 (2026-09-29)

The owner approved every G0 proposal in a single reply after reading the G0 request and the
literature-search summary. Later changes are appended below.

### Questions

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-09-29 | Q1. Labels have two axes: `slot_label` (is this span correct in its role as an answer) and `value_label` (where the value comes from and whether it is copied correctly). | A single axis cannot separate a correctly copied value in the wrong role from a wrong value. |
| 2026-09-29 | Q2. Raters see the gold short answer. | Evidence tables alone are slower to judge and raise the risk of arithmetic mistakes. |
| 2026-09-29 | Q3. The primary decision-model arm is the local open model `ZefanCai/Open-Jev-2B`; the hosted Jev model is the comparison arm. | Reproducibility should not depend on a vendor. |
| 2026-09-29 | Q4. The owner takes no part in labelling or adjudication. | Keeps the labels separate from the person who designed the study. |
| 2026-09-29 | Q5. A local forward pass of the generator for the optional information-timing experiment is allowed in principle; the owner confirms again before it runs. | The experiment is optional and comes late in the plan. |
| 2026-09-29 | Q6. The API key is replaced before the first hosted run; the owner does this. | Rotating the key before any hosted run is standard hygiene. |
| 2026-09-29 | Q7. The annotation protocol of this line replaces the earlier relabel procedure, including its fallback of using a language model as a second rater. | No model acts as a rater or adjudicator. |
| 2026-09-29 | Q8. Thresholds: every arm uses the same false-flag budget of 0.20, fitted on the dev main set, with separate fit sets for the test role and the held-out role. | One budget makes the arms comparable; maximum dev F1 favours flag-everything thresholds on error-enriched data. |
| 2026-09-29 | Q9. Spans that the extractor finds only in dev and test answers join the formal annotation package, so held-out thresholds can be fitted on spans of the same origin. | The held-out spans come from the extractor, the 205 spans were selected by hand. |
| 2026-09-29 | Q10. In a package that contains extractor spans, `not_a_claim` is available for every span. | Offering it only for extractor spans would tell raters which spans the extractor added. |
| 2026-09-29 | Q11. A deterministic baseline arm, `evidence_lookup` (the value or name appears somewhere in the evidence), is added. | It represents a common grounding check and shows which errors such a check leaves unflagged. |

### Designs

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-09-29 | D1 to D10 approved: two-axis labels and exclusion rules; five mechanism codes assigned by raters; evaluation roles and span sets; verification arms and baselines; primary analysis on the held-out role with test as supportive and in-sample; freeze timing (freeze point A); code locations; what raters see; output layout; span file format. | Owner approval of the execution plan's design section. |

### AGENTS.md amendments

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-09-29 | A1 to A8 approved. A1, A2, A3, A6 and A7 are applied at task card T1.12; A4 at T2.2; A5 before T3.2; A8 after T4.5. | Several AGENTS.md sentences were written for the September presentation batch and the B1/B2 appendices and would otherwise stop or confuse work on this line. |

### Preregistration

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-09-29 | Preregistration v1 approved and sealed. It holds the primary hypotheses and their decision conditions; the calculation rules sit in the battery config. It stays private until the analysis gate, and its SHA-256 is recorded in the freeze record at freeze point A. | Fixing the hypotheses before any decision-model result keeps the later reading of results honest. |
