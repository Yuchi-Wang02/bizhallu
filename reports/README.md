# Reports

This directory is reserved for portfolio-ready written outputs:

- experiment report
- result figures
- presentation-ready tables
- screenshots from the demo

Current report-ready drafts:

- `full100_detector_interpretation.html`
- `full100_detector_interpretation_summary.json`
- `full100_detector_interpretation_validation.json`
- `full100_label_confirmation_packet.html`
- `full100_label_confirmation_packet.csv`
- `full100_label_confirmation_packet.jsonl`
- `full100_label_confirmation_packet_summary.json`
- `full100_label_confirmation_packet_validation.json`
- `full100_label_confirmation_review_notes.html`
- `full100_label_confirmation_review_notes.csv`
- `full100_label_confirmation_review_notes.jsonl`
- `full100_label_confirmation_review_notes_summary.json`
- `full100_label_confirmation_review_notes_validation.json`
- `full100_label_lock_report.html`
- `full100_label_lock_decisions.csv`
- `full100_label_lock_decisions.jsonl`
- `full100_label_lock_summary.json`
- `full100_label_lock_validation.json`
- `bizhallu_portfolio_demo.html`
- `bizhallu_portfolio_demo_summary.json`
- `bizhallu_portfolio_demo_validation.json`
- `bizhallu_portfolio_narrative.html`
- `bizhallu_portfolio_narrative_summary.json`
- `bizhallu_portfolio_narrative_validation.json`
- `bizhallu_portfolio_demo_v2.html`
- `bizhallu_demo_v2_data.json`
- `bizhallu_portfolio_demo_v2_summary.json`
- `bizhallu_portfolio_demo_v2_validation.json`
- `bizhallu_career_package.html`
- `bizhallu_career_package.md`
- `bizhallu_career_package_summary.json`
- `bizhallu_career_package_validation.json`
- `bizhallu_business_risk_lens.html`
- `bizhallu_business_risk_lens_summary.json`
- `bizhallu_business_risk_lens_validation.json`
- `bizhallu_research_one_pager.html`
- `bizhallu_research_one_pager_summary.json`
- `bizhallu_research_one_pager_validation.json`
- `public_path_hygiene_validation.json`
- `bizhallu_ai_reliability_deck.pptx`
- `bizhallu_ai_reliability_deck_contact_sheet.png`

GitHub Pages copies of the public-facing HTML reports are generated under
`docs/` by `src/build_github_pages_bundle.py`. Keep `reports/` as the
experiment-native report archive and use `docs/index.html` as the public entry
point.

Intermediate validation JSON files should stay next to the artifacts they
validate, usually in `data/processed/` or `outputs/`.
