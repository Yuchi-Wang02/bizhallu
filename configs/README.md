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

`detector_baseline_suite.json` defines the score fields used by the
split-safe evaluator. Thresholds are selected on dev spans and reused on test
spans.
