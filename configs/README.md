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
- `confirmation_context_manifest_v1.json`
- `confirmation_question_design_v1.json`
- `confirmation_precision_review_v1.json`
- `confirmation_precision_scope_amendment_v1.json`
- `confirmation_set_v1_protocol.json`
- `jev_battery_v1.json` (typed-question wording of the first battery draft; authored
  but never executed, kept unchanged)
- `decision_battery_v2.json` (question wording, state contract, label mappings,
  span-kind rules, checker policy and analysis policy of the decision battery)
- `decision_battery_arms_v1.json` (decision-model arms: endpoint, pinned model,
  repeats and environment notes)
- `heldout_slice_v1.json` (question ids of the label-held-out slice and their
  SHA-256)

`decision_battery_v2.json`, `decision_battery_arms_v1.json` and
`heldout_slice_v1.json` are read by `src/bizhallu/decision_battery.py`. The
battery's freeze record, `decision_battery_v2_freeze.json`, is written once by
its `freeze` subcommand and never by hand; later corrections go into numbered
`decision_battery_v2_freeze_amendment_N.json` files. A change to the question
wording or the state contract also updates the hashes pinned in
`tests/test_decision_battery.py`.

`detector_baseline_suite.json` defines the score fields used by the
split-safe evaluator. Thresholds are selected on dev spans and reused on test
spans.

`confirmation_precision_review_v1.json` freezes the synthetic, outcome-blind
cluster-precision scenarios and decision thresholds used before any context
manifest is selected. No candidate passed every strong-comparison rule.
`confirmation_precision_scope_amendment_v1.json` records the resulting
estimation-focused claim boundary and the revised 6/15/27 context plan; it does
not contain confirmation outcomes.

`confirmation_context_manifest_v1.json` freezes the seeded family matching,
6/15/27 split, reserve, evidence-pool, and privacy rules. The selected periods
and entities remain in a Git-ignored private manifest; the public report stores
only aggregate counts and a canonical SHA-256 commitment.

`confirmation_question_design_v1.json` freezes two deterministic questions per
context across six templates, the gold calculation and rounding rules, seeded
entity selection, evidence ordering, payload fingerprinting, and the public/private
boundary. Question text, gold answers, selected entities, and evidence rows remain
in a Git-ignored private manifest.
