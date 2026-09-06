# BizHallu

**A correct number can still support the wrong business claim.**

[Explore a case](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html?case=q_0064) ·
[Research brief](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html) ·
[Methods and results](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html)

[One-page PDF](https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_research_brief.pdf) ·
[Editable slides (PPTX)](https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_interview_v2.pptx) ·
[Slide overview](https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_interview_v2_overview.png)

BizHallu audits whether LLM-generated business analysis is grounded in transaction
evidence, at the level of individual business-fact spans. It connects accounting
and retail metric definitions with a practical AI reliability question: **does a
generated statement bind the right product, period, rank and amount together?**

## Start with one error

In an April 2011 product-ranking answer, Qwen3-0.6B places **WOODEN UNION JACK
BUNTING** third at **GBP 4,173.18**. The product and amount match the source row,
but the product ranks **seventh among the eight evidence rows shown to the
model**. Third place belongs to PAPER CHAIN KIT EMPIRE at GBP 6,619.51.

This is a curated evidence check, not an independent verifier prediction or an
estimate of how often models make this error. It shows why matching a number to
a source is insufficient to establish the complete relationship.

[Inspect the original answer and evidence](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html?case=q_0064) ·
[Compare the September case](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html?case=q_0069)

## What is available now

- **An inspectable workflow:** UCI Online Retail transactions → 100 deterministic
  questions across seven types → 100 local `Qwen/Qwen3-0.6B` answers →
  pre-identified spans → token alignment → uncertainty-signal evaluation.
- **A provisional annotation package:** 205 AI-assisted business-fact span labels
  across 35 of 36 dev/test answers; 15 selected presentation spans received an
  additional assistant review. No independent human annotation or inter-annotator
  agreement has been completed.
- **A retrospective statistical audit:** simple reference policies, tied-score
  average precision, paired uncertainty and a separate omission-sensitivity
  analysis. Original evidence and historical results remain intact.

The current contribution is the auditable workflow, explicit evaluation limits
and inspectable business errors. The project is exploratory; it does not establish
a production-ready detector, whole-answer accuracy or automatic extraction of
claims from new responses.

## What the results support

On **103 pre-identified test spans**, top-2 margin has AP **0.835**; entropy has
F1 **0.779**, compared with **0.744** for flagging every span. Entropy's paired
question-bootstrap F1 difference is **+0.0355**, with exploratory 95% interval
**[-0.0356, 0.1047]**. This does not establish stable superiority.

These spans belong to an outcome-informed, error-enriched annotation subset.
Dev and test share periods and exact evidence-row payloads. Thresholds were
selected on dev, but the headline signals were chosen after comparing test
results. The historical maxima **0.835073 AUPRC / 0.779412 F1** come from different
signals and remain exploratory. The B1 audit uses tied-score-aware AP.

The separate B2 sensitivity adds nine provisional q_0048 dev atoms. Dev-only
refitting changes entropy F1 to **0.752** on the same old test; margin is unchanged.
The original 205-span package and 103 test spans are preserved. This is not fresh
confirmation. [Read the comparison, controls and limitations](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html).

## Research question and next step

**How should complete entity–rank–amount relationships be annotated and checked
without counting one binding error several times?**

The immediate proposal is a small relation-annotation pilot: review one schema
and one worked case, then design a calibration exercise with a second reviewer.
This would inform an independent evidence-aware verifier whose predictions use
the question, answer, metric contract and evidence, without gold answers or
evaluation labels. Extraction coverage, abstention and error types would be
reported separately. The existing review schema derives its statuses from
presentation labels; it is not that verifier.

Token-time uncertainty and completed-answer verification have different available
information. The comparison must account for this difference; a low score on an
early list marker does not establish confidence in the completed relationship.
The longer-term **48-context / 96-question** study is estimation-focused,
design-only and not execution-ready. Confirmation remains sealed.

**Feedback sought:** a short discussion of the relation unit and the smallest
useful calibration study. The [research brief](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html)
contains the proposed pilot and its relationship to
[FActScore](https://aclanthology.org/2023.emnlp-main.741/),
[TabFact](https://openreview.net/pdf?id=rkeJRhNYDH) and
[Semantic Entropy](https://www.nature.com/articles/s41586-024-07421-0).
These are related work and future comparison context, not methods evaluated here.

## Project authorship and AI assistance

I am [Yuchi Wang](https://github.com/Yuchi-Wang02), currently an MS student in
[Business Analytics and Artificial Intelligence](https://carey.jhu.edu/programs/master-science/business-analytics-artificial-intelligence)
at Johns Hopkins Carey Business School. My background is in accounting and supply
management, and my research interests center on evidence-grounded business analytics.
BizHallu is my independent exploratory project.
I directed this project with AI-assisted implementation and review across the
data workflow, experiment code, provisional annotation, analysis and presentation.
The repository does not claim unaided implementation or independent human
validation. Label provenance is part of the results, not an endorsement by a
separate reviewer.

## Explore or reproduce

| Purpose | Start here |
| --- | --- |
| Understand the business error | [Interactive cases](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html) |
| Discuss a research direction | [Research brief](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html) |
| Inspect evaluation and evidence limits | [Methods and results](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html) |
| Present the project | [English interview deck v2](https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_interview_v2.pptx) |
| Review accounting and business scope | [Business risk lens](https://yuchi-wang02.github.io/bizhallu/business_risk_lens.html) |
| Check public artifacts or replay calculations | [Reproducibility guide](docs/reproducibility.md) |

Public calculations can be checked from committed lightweight artifacts; full
generation requires excluded raw data, model weights and traces. CI and Pages
checks establish artifact consistency and publication, not scientific validity.
[Documentation index](docs/README.md) · [Current audit and study history](docs/current_state_audit.md)

Code: [MIT License](LICENSE). Data: [UCI Online Retail, Chen (2015), CC BY 4.0](https://doi.org/10.24432/C5BW33).
Negative transaction value is not verified physical returns or audited revenue;
the project does not demonstrate savings, profit or inventory optimization.
