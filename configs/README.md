# Configs

This directory is reserved for reusable run configurations.

Planned files:

- generation configs
- pilot selection configs
- annotation configs
- baseline configs
- evaluation configs

The current MVP scripts still use command-line arguments. Add config files when
the same run needs to be repeated or reported.

Current config files:

- `pilot20_questions.json`
- `top3_structured_pilot3_questions.json`
- `top3_sorted_control_pilot3_questions.json`
- `full100_questions.json`
- `detector_baseline_suite.json`
- `methodology_protocol_v1.json`
- `confirmation_dataset_source_audit_v1.json`
- `confirmation_context_feasibility_v1.json`
- `confirmation_precision_review_v1.json`
- `confirmation_precision_scope_amendment_v1.json`
- `confirmation_set_v1_protocol.json`

`detector_baseline_suite.json` defines the score fields used by the
split-safe evaluator. Thresholds are selected on dev spans and reused on test
spans.

`confirmation_precision_review_v1.json` freezes the synthetic, outcome-blind
cluster-precision scenarios and decision thresholds used before any context
manifest is selected. No candidate passed every strong-comparison rule.
`confirmation_precision_scope_amendment_v1.json` records the resulting
estimation-focused claim boundary and the revised 6/15/27 context plan; it does
not contain confirmation outcomes.
