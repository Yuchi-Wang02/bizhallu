# Docs

This directory has two roles:

- project design notes and audit documents
- GitHub Pages-ready public pages

Recommended GitHub Pages entry point:

- `index.html`

Public pages:

- `portfolio_demo.html`
- `portfolio_narrative.html`
- `detector_interpretation.html`
- `label_lock_report.html`
- `label_confirmation_packet.html`

Public assets:

- `assets/bizhallu_ai_reliability_deck.pptx`
- `assets/bizhallu_ai_reliability_deck_contact_sheet.png`
- `assets/full100_draft_detector_error_review_examples.csv`

Upload support:

- `github_upload_checklist.md`
- `github_upload_dry_run.md`

Refresh command:

```powershell
python src\build_github_pages_bundle.py
python src\validate_github_pages_bundle.py
python src\build_full100_preflight_report.py
```

The public pages are generated from validated report artifacts. Edit the source
builders in `src/` rather than hand-editing generated HTML pages.
