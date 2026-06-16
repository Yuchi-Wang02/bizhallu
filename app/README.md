# App

This directory is reserved for an optional local demo.

Current public-demo priority:

- Use the static GitHub Pages bundle first.
- The public interactive path is `docs/portfolio_demo_v2.html`.
- The public data bundle is `docs/assets/bizhallu_demo_v2_data.json`.

Why static first:

- It runs directly from GitHub Pages without local setup.
- It is better for recruiters, interviewers, and portfolio visitors.
- It keeps raw data, model outputs, token traces, and model weights outside the
  public app surface.

Optional future entry point:

- `streamlit_demo.py`

The optional local app can add heavier inspection views, but it should reuse the
same public-safe case data shape: business question, evidence summary, Qwen
answer, span labels, detector scores, and detector outcome.
