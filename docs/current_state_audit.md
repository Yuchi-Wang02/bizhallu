# BizHallu Current State Audit

Date: 2026-09-05

## Public Browser Acceptance and Mobile Fixes: 2026-09-05

This entry supersedes the public-browser-pending status below, within the tested
scope only. Actual browser work used the published HTTPS site in the Codex
in-app browser, not a local-file workaround. The earlier blocked local review
reports and private calibration packet were not opened. Viewport overrides were
reset and the temporary browser tab was closed after testing.

Two scoped fixes were published: `c019a1a` moves the unchanged Qwen answer before
interpretive context and fixes narrow methods-page overflow; `51caaa1` keeps
business-table columns readable in named, keyboard-focusable scroll regions.
[CI](https://github.com/Yuchi-Wang02/bizhallu/actions/runs/33992918952) and
[Pages](https://github.com/Yuchi-Wang02/bizhallu/actions/runs/33992917864) passed
for `51caaa156fbbd0309623cf04ec36502d229d599f`. Browser refreshes were necessary
to replace cached earlier pages; no content was repushed as a cache workaround.

| Check | Observed evidence |
| --- | --- |
| Homepage and research brief | Desktop 1280 x 800 and narrow 320 x 740 viewport inspection; the concrete business case is visible and text stays within the page |
| Demo reading order | At 390 x 844, the original answer starts about 290 CSS pixels earlier (1003 to 713); desktop columns remain separate; the source answer and three April relationship highlights are preserved |
| Nine-case navigation | Final narrow-viewport pass checks all nine question IDs, one answer block per case and evidence row counts 8/8/4/2/2/8/8/1/1; no whole-page horizontal overflow |
| Historical filters | Percentage produces the expected empty April selection; restoring filters recovers rows; Supported returns two rows; all three detector choices support outcome filtering without replacing the relationship walkthrough |
| Methods overflow | Before the fix, 305 CSS pixels of available width produced a 409-pixel page; afterward the page is 305 pixels wide and each error panel is 277 pixels wide |
| Appendix navigation | B2 target starts about 82 pixels below the viewport top; its heading is below the 62-pixel sticky header |
| Table readability and keyboard access | Tables retain 720-pixel column space within the narrow container; ArrowRight moves each named region; the ranking region reaches its right boundary without scrolling the whole page horizontally |
| Runtime errors | No warning/error entries were returned by the tab console-log check during the exercised workflows |

The table-width fix followed a second visual finding: avoiding page overflow
alone had still allowed product names and headers to collapse into individual
letters. The bounded scrolling layout fixes that readability problem without
shrinking text or removing source columns. The Node suite now has 25 passing
tests, including new reading-order and focus-region guards. A Python CSS-contract
regression also passes; those tests are not substitutes for the observations above.

No public data bundle, label, score, statistical appendix or deck changed in this
batch. Generic validators intentionally retain `visual_review_verified=false`:
they do not themselves perform browser inspection. This dated acceptance record
is separate evidence, not permission to make their validation scope broader.
Physical phones, other browser engines, printing and native desktop PowerPoint
remain unverified. The private workbench has logic tests but no completed user
trial. Owner calibration, independent annotation and speaking mastery remain
deferred/unverified, not inferred from these assistant actions.

## English Portfolio Published: 2026-09-05

This entry supersedes the publication-pending status in the release-candidate
record below. The reviewed candidate was committed in English as
`24c7f5ac28097e8c1189bee0b2b14df3db9cc53c` and pushed once to `main`.
The remote branch was independently checked against that exact commit.
[Public CI](https://github.com/Yuchi-Wang02/bizhallu/actions/runs/33992015667)
and [Pages deployment](https://github.com/Yuchi-Wang02/bizhallu/actions/runs/33992015366)
both completed successfully for that revision. CI runs the 27 reviewed commands
on Ubuntu with Python 3.11 and Node 24; it does not replay private traces or run a model.

After deployment, the homepage, current and historical cases, methods, research
brief, career package, business risk lens, narrative and both deck assets all
returned HTTP 200. Each HTML response matched the local committed content after
newline normalization; both PPTX files matched byte-for-byte SHA-256 hashes.
The current deck remains
`89cd8c99832e4abd8ce5156ebf3e82d6f73d58992a3f67523a5778e900dca1bb`.
Initial checks during deployment saw stale HTML and a temporary new-deck 404;
waiting for the same deployment resolved them without another content push.

The release contains 386 public files, including 63 reviewed additions. Raw data,
full generations, token traces, model weights and private review/confirmation
packets remain excluded. Three unrelated untracked Claude files remain untouched;
their presence is not a reason to add them or claim the entire workspace is clean.
Original 205-span labels, historical split reports and the original deck were not
overwritten. The q_0048 supplement remains a separate assistant-provisional
sensitivity appendix, not nine independent human judgments or new test evidence.

Stage 1's assistant-led source checks, English materials and controlled publication
are now complete. Actual browser/mobile/print and desktop PowerPoint acceptance
remain unverified. Owner review is deferred with zero completed submissions;
neither deployment nor prepared speaker notes establishes owner mastery.
Next, keep the public experiment scope stable. Use the existing cases and notes
for a later explanation trial and external feedback; do not add a new detector,
rerun Qwen or open confirmation outcomes to fill these remaining acceptance gaps.

## English Release Candidate and Isolated Clone: 2026-09-05

This entry supersedes the pending B2 presentation synchronization below.
The homepage, current and historical case readouts, methods, research brief,
career package and narrative now expose the separate B2 sensitivity alongside
the preserved B1 results. The short pitch is 191 words; the ten-part walkthrough
is 669 words with a 300-second planning budget, not measured owner performance.
No labels, token scores or model generations changed in this release batch.

The unpublished English interview deck v2 was revised in its existing ten-slide
structure. Slide 5 distinguishes original B1 coverage from the separate B2
supplement. Slide 6 retains its original native B1 chart and interval, with a
visible note that B2 refitting yields entropy F1 0.752 on the same old test.
Speaker notes identify both source hashes and do not call the B1 interval a B2
interval. The final current deck SHA-256 is
`89cd8c99832e4abd8ce5156ebf3e82d6f73d58992a3f67523a5778e900dca1bb`.
The prior unpublished revision remains in ignored local build output; the
original historical public PPTX remains unchanged. All ten final slides were
rendered. Slides 5 and 6 were inspected at full size; the other eight renders
are byte-identical to the previously inspected revision. The complete contact
sheet was also checked. There were no package/layout warnings. Native desktop
PowerPoint and browser/mobile/print layout remain unverified.

Four copied historical Pages reports now carry explicit archive notices:
methodology hardening, label-lock report, label-confirmation packet and the
label-derived verifier schema. Their experiment-native source HTML remains
unchanged. Tests check that removing only the notice recovers the original
link-rewritten page, and that current reader paths include the source-backed
B2 caveat. A schema status is not a prediction; a presentation lock is not
independent annotation or completed owner review.

Release preparation uses an explicit inventory: 323 tracked files plus 63
reviewed additions, totaling about 8.6 MB. The three unrelated untracked Claude
files stay excluded and untouched. Raw transactions, full generations, token
traces, model weights and private C1/confirmation artifacts are not copied.
A temporary local repository was created from the candidate and freshly cloned;
the original repository HEAD and index were preserved. The dry-run script,
inventories, command logs and receipts remain Git-ignored under
`outputs/release_stage1/`. This is not a commit or push to the real repository.

The isolated clone uses Windows, Python 3.13.5 in a new virtual environment without
pip or third-party packages, and Node 24.19.0. All 27 current workflow commands
pass: 25 validators plus Python and Node test suites. Two additional commands
rebuild and validate Pages entirely from the cloned public artifacts; resulting
HTML and asset hashes match the source candidate. The Python suite discovers
111 tests: 109 pass and two optional scikit-learn cross-checks skip because that
package is absent. All 111 pass in the original environment, including those
cross-checks. All 23 Node tests pass. Public B1/B2 calculation replay passes;
private trace replay is explicitly not performed in the isolated clone.

The first clone attempt found two stale heading assertions in public validators.
They were updated to the new Historical B1 headings, without removing source,
numeric, claim-boundary or B2 checks. A second complete clone run passed. This
shows why a content edit and its validator must be reviewed together; it does
not establish research validity. GitHub's Ubuntu/Python 3.11 runner and a new
deployment have not yet been tested for this candidate.

Remote main was checked and remains `4c6f72e227406d40235e9a9478a2180a072ddfa3`.
Stage 1 now has a source-backed English release candidate with independent
algorithm checks and public-only clone evidence. Remaining work is controlled
publication and actual browser/owner acceptance, not more experimental scope.
Owner review stays deferred with zero completed submissions. Do not count this
release work as independent annotation, speaking practice or owner mastery.

## B2 Omitted-Dev Sensitivity: 2026-09-05

This entry supersedes earlier B2-pending notes below. B2 computation is now
complete locally with assistant-provisional labels, not independent annotation
or owner calibration. It does not replace the historical B1 or full100 packages.

Nine q_0048 atomic facts were saved under
`data/annotations/span_annotations_q0048_b2_assistant_v1.jsonl` and checked for
schema, exact character offsets and source arithmetic before this batch read
their token scores. The fixed recipe and prepared public-safe source projection
retain hashes and the sequencing disclosure. Historical familiarity remains;
this is not blind annotation or prospective preregistration. All nine judgments
are correct-key-fact. Approximately GBP 27,508 is whole-pound rounding of the
GBP 27,507.89 difference, not a new hallucination. Repeated entities/comparisons
are correlated facts, not independent observations.

`src/q0048_dev_sensitivity.py` aligns these nine spans to the saved q_0048 trace
and generates two precision arms. The original 205 labels, original detector
reports, B1 scores/report, 15 presentation judgments and private C1 reviewer
packet/template remain unchanged. Only the new sensitivity uses 214 spans:
dev grows from 17 questions / 102 spans to 18 / 111; test remains 18 / 103.
No Qwen inference, confirmation execution or owner submission occurred.

All 12 existing signals and three references are refitted with the unchanged
B1 dev-only rule. The 120-row metric table includes both conditions, precision
arms and splits, not 120 independent experiments. Original-condition calculations
exactly reproduce all 60 B1 metric rows. Saved-trace precision results include:

| Signal / reference | Original dev threshold | Supplemented dev threshold | Old-test F1 before / after | Changed test decisions |
| --- | ---: | ---: | ---: | ---: |
| Mean entropy | 0.004817123346 | 0.081865905043 | 0.779412 / 0.752000 | 11 |
| Minimum top-2 margin risk | 0.334332823753 | 0.334332823753 | 0.752294 / 0.752294 | 0 |
| All-positive | 0.5 | 0.5 | 0.743902 / 0.743902 | 0 |
| Dev fact-type prior | 0.575 | 0.5 | 0.835616 / 0.814286 | 6 |

Entropy's TP / FP / TN / FN changes from 53 / 22 / 20 / 8 to 47 / 17 / 25 / 14:
five fewer false alarms and six additional missed provisional errors. Fixed
internal-score AP is unchanged by threshold refitting; the prior's AP changes
because dev refitting changes its scores. The prior remains an annotation-type
composition control with correctness hints, not an independent detector.
Both arms have five changed thresholds and 30 changed signal-span predictions;
these are repeated analysis rows, not 60 unique errors or new observations.
No new method winner, interval, significance or generalization claim is made.

The existing English methods page now contains an expandable B2 appendix,
all candidates/both precision arms, the q_0048 answer and nine boundaries. No
new top-level page was created. README, annotation notes, agent instructions
and semester milestones distinguish original results from B2. The earlier
English deck and shared B1 presentation remain an explicitly historical view;
the release audit must add a concise B2 pointer where needed, not silently
replace their metric/chart data or describe the old threshold as newly validated.

Verification: 105 Python tests and 23 Node tests pass. Twelve new tests include
independent rational-arithmetic threshold enumeration, independent test confusion
counts, changed-prediction membership, invalid offsets/IDs/splits/non-finite
scores, all-correct single-answer limits and preserved source commitments.
All 25 public-tier workflow validation commands pass locally, including B1's
15,000 paired draws and B2 calculation replay. q_0048 local token replay and
legacy annotation-schema validation also pass. Full100 preflight passes and
the Pages bundle remains 27 required assets / 19 HTML files. C1 local replay
again confirms zero completed reviews and the unchanged private projection.
These checks do not establish browser rendering, independent labels, owner
mastery, clean-clone execution or a successful new GitHub deployment.

Plan versus reality: q_0048 was not just administrative cleanup. A single
all-correct dev answer changes entropy's operating threshold materially, while
margin is unchanged in this particular sensitivity. The omission check is now
available for discussion; independent review and broader stability remain open.
Stage 1 still needs a cumulative release audit, archived-content signposting and
browser/owner acceptance. No commit or push was made in this batch. Next batch
should audit and consolidate the existing release, not expand experiments,
rerun Qwen, add baselines or open confirmation outcomes.

## Business Scope and Remaining Calibration Sources: 2026-09-05

This batch completes source-led explanations for the three remaining calibration
examples without completing owner calibration or creating evaluation labels.
`src/audit_calibration_sources.py` independently aggregates quantity times unit
price from the local historical eligible-line CSV for seven evidence scopes.
All seven agree with the displayed evidence and their relevant gold arithmetic.
Exact answer quote ranges and calculations are recorded only in the ignored
`outputs/relation_calibration_admin_v2/source_checks.json`, outside the blinded
reviewer packet. This is a curated assistant calculation note, not a verifier.

- q_0048: Netherlands exceeds EIRE by GBP 27,507.89. The answer's approximately
  GBP 27,508 is correct whole-pound rounding, with GBP 0.11 display difference.
  This does not supply the missing v1 atomic labels or complete B2.
- q_0053: April/May amounts and GBP 229,726.26 difference are correct; using April
  as the denominator gives 46.66%, not the answer's 48.97%. Absence of an explicit
  increase keyword is not evidence of a reversed-direction claim. The cause of
  the model's percentage error remains unknown.
- q_0092: the correct negative-value magnitude is GBP 34,201.28, not
  GBP 342,012.88. Its final net GBP 682,013.98 is copied correctly but does not
  reconcile with the generated reduction. The positive-magnitude sign explanation
  is reasonable; the historical question's physical-returns wording is not
  established by the source. A percentage was not requested.

The existing business risk lens is now an English, source-backed ledger view:
positive GBP 10,642,110.80 plus negative GBP -893,979.73 equals net
GBP 9,748,131.07. Merchandise net GBP 9,771,708.99 has a different scope.
The four category subtotals and their row counts reconcile; 46.77% of absolute
negative value is non-merchandise under the stock-code heuristic. This is not a
physical-return rate or a finding that those rows are erroneous. No avoided
loss, analyst time saving or inventory benefit is claimed. The old unconditional
10-20-question expansion advice is removed; no new public page was added.

The original case page now retains its seven selected spans and all original
outcomes while separating product-amount fidelity from completed ranking.
The source evidence order, values, label offsets and three dev thresholds are
preserved. Its readout is explicitly atomic/historical; it cannot establish
confidence in a completed relationship or detector superiority. The B1 reference
table and timing limitation are visible. Public threshold checks now read the
original split reports, preventing two regenerated summaries from corroborating
each other's drift. Existing legacy report values are not overwritten.

Verification: 93 Python tests and 23 Node tests pass, including 15 new tests for
rounding, percentage denominators, reconciliation, non-finite values, duplicate
rows/quotes, quantity-price replay, altered display values, threshold drift and
exact model-whitespace preservation through HTML serialization.
Twenty-one public artifact validators and full100 preflight pass locally. The
Pages bundle remains 27 required assets and 19 HTML files. C1 local validation
again confirms the unchanged five-case projection and zero completed reviews.
No Qwen inference, confirmation execution, label promotion, commit, push or
new deployment occurred. Browser/owner acceptance remains unverified.

Next: prepare q_0048's separate v1 atomic supplement and dev-threshold sensitivity
without translating these relation notes into labels automatically; explicitly
retain assistant-provisional provenance if personal review stays deferred.
Then audit the cumulative release and remaining archived-content signposting.
Stage 1 is not complete, but five-case source preparation and the current English
business/case explanations no longer depend on waiting for an owner submission.

## English Interview Materials: 2026-09-05

This entry supersedes the pending career/narrative/deck synchronization in the
earlier entry below. The existing career package and portfolio narrative now
share `src/presentation_story.py`, which links their English content to the
curated evidence checks and the B1 statistical appendix. There is a 185-word
90-second introduction and a 665-word, ten-segment walkthrough budgeted for 300
seconds. These are planned speaking times, not measured owner performance.
Five resume bullets, ten interview questions and explicit role/annotation limits
are included. No owner's review or independent mastery is inferred.

`reports/bizhallu_interview_v2.pptx` is a separate ten-slide English presentation;
the historical `bizhallu_ai_reliability_deck.pptx` remains unchanged. Two editable
evidence tables show the April and September cases, and an editable F1 chart
compares entropy, all-positive and margin on a full 0-to-1 scale. The chart and
notes disclose the paired uncertainty interval, retrospective signal selection,
provisional annotations and shared-period dependence. The chart workbook stores
six-decimal presentation values, not rounded replacements for analysis inputs.
The April display is explicitly sorted for explanation; original model input
order remains intact in the demo. Speaker notes contain the shared script and
source references. This is local packaging, not a new model/verifier result.

The final PPTX SHA-256 is
`33312a344e95f65196c86c7338412632fec232d6243840d67d97f269858a0459`.
Artifact Tool finalization reported zero warnings/findings. All ten final-slide
renders were visually inspected; after the final April-caption revision, that
slide was rechecked and the other nine renders were byte-identical to the
previous inspected revision. Native PowerPoint opening, browser page layout,
mobile/print behavior and actual speaking time are not verified. Temporary
chart-workbook materialization files are kept in ignored local build output,
not treated as public assets.

Local checks: 78 Python tests and 23 Node tests pass, including source/notes
agreement and mutations of deck amounts and chart axes. Twenty public artifact
validators and full100 preflight pass. The Pages bundle validates 27 required
files and 19 HTML files. B1 local replay again verifies 100 saved answers, 205
spans, 12 signals and 15,000 paired cluster draws without inference, with the
unchanged source commitment
`096bae57edec06e74c6f4e029419b844adb421d252a1f8c60335ae1859dc0727`.
The five-case calibration packet validates with zero completed reviews; it is
not ready for new metrics. Original annotations, historical scores, locked
judgments and the original deck were not changed.

Status: Stage 1 presentation preparation has advanced; Stage 1 itself is not
complete. The other calibration cases and B2 q_0048 need separate source-led
review, older case-demo/business-risk explanations still need a consistency
audit, and browser/owner acceptance remains open. The owner has deferred personal
review, so assistant-led preparation can continue without inventing reviews.
Release requires a separate audit of the cumulative A/B1/C1 and presentation
diff. No commit, push, deployment, Qwen run, confirmation execution or new
baseline is asserted for this batch. No plugin installation was needed.

## English Evidence Review: 2026-09-05

This update supersedes the owner-first blocking sequence below. The owner has
deferred personal review and asked for English presentation progress. No review
has been filled in on the owner's behalf, and zero independent reviews remains
the status. This is a local content revision, not a deployed GitHub release.

The existing homepage, Demo v2, methods interpretation and research brief now
lead with business evidence and preserve the original experiment. A shared
source checker confirms six explicitly curated ranked statements: q_0064's
products rank 1/2/7 in the eight shown rows, and q_0069's rank 3/8/2. All six
product-amount pairs match their own rows; the wrong relation is ranking, not
necessarily copying the amount onto another product. Requested stock codes are
omitted. This walkthrough does not create new labels or perform automatic claim
extraction. Early list-marker uncertainty cannot establish confidence in the
later completed relation.

The four primary pages now display B1 reference results and uncertainty rather
than relying on historical maxima. Entropy F1 is 0.779412 versus all-positive
0.743902; the paired question-bootstrap difference interval crosses zero. The
dev fact-type prior remains a composition diagnostic, not a fair automatic
detector competitor. Same-step energy gap is NLL, and residual probability mass
is not independent replication of adjacent-step Spilled Energy.

The demo puts complete relations before its collapsible historical span table,
preserves evidence order, and uses codepoint-aware highlighting. The compact
research brief includes one concrete case, three open questions and a specific
request for annotation-unit/comparison-design feedback. Older deck, career
package, narrative and original case demo remain historical and need wording
synchronization; they should not be treated as newly reviewed presentation.

Verification includes source-row arithmetic, exact quote ranges, historical
score/threshold/label preservation, embedded/downloadable JSON equality and
generated-script tests for navigation, all detector filters, empty states,
escaping and Unicode. These are content and logic tests, not browser layout,
print pagination, independent human review or evidence of owner mastery.
The methods validator no longer calls a content-only pass locked presentation.
Next: synchronize the English 90-second/five-minute scripts and deck, then review
the other calibration examples separately from owner labels and B2 q_0048.
No new Qwen run, confirmation execution, baseline expansion or plugin is needed.

Local verification receipt: 70 Python tests (including installed scikit-learn
cross-checks) and 23 Node tests pass; all 18 public validators and historical
full100 preflight pass. Stage A local replay verifies 96 questions/48 contexts
and source arithmetic. B1 local replay verifies 100 answers, 205 spans, 12 signals
and 15,000 paired cluster draws. The B1 report commitment remains
`096bae57edec06e74c6f4e029419b844adb421d252a1f8c60335ae1859dc0727`.
The primary pages and README are local changes; neither a commit/push nor a new
deployment is asserted. Browser layout/print pagination and owner review remain
explicitly unverified, regardless of a green local artifact result.

## Semester Plan and First Owner Trial: 2026-09-05

The adopted priority is employment-facing business/data/operations analysis with
a research option and 7-10 hours of owner participation per week. The detailed
milestone table and first-session procedure live in `app/README.md`; there is no
new public progress page. README now starts with cases, methods and research,
with supporting study history retained in a secondary section.

The current batch improves the existing local workbench, not the labels:
Chinese display labels retain the frozen protocol values; a one-case draft check
and scoped CLI submission check allow B01 to precede the other four cases.
Annotation/note edits clear the previous coverage attestation, and switching
relation editors warns before discarding an unsaved edit. Download requests are
not reported as verified saves. Four neutral oral-review questions use the
existing notes field; no answers, labels or identities are filled in.

The generated packet/template remain unchanged and contain zero completed
reviews. Validation means schema and declared coverage, not verified human work,
semantic correctness or mastery. Real browser layout and owner selection,
download/import and spoken explanation remain pending. B2 q_0048 sensitivity,
five-case owner calibration and public HTML/deck synchronization are not complete.
These local changes are not a GitHub deployment; publication needs a separate
review of the accumulated A/B1/C1 changes. Next: owner tries B01 and provides an
export or a specific usability issue; inspect it before expanding calibration.

Verification for this batch: 55 Python tests and 15 Node tests pass. The 17
existing public validators and full100 preflight pass locally. Stage A replays
the 96-question/48-context amendment against source arithmetic; B1 replays 100
answers, 205 aligned spans, 12 signals and 15,000 paired cluster draws without
inference. A 34-file before/after hash comparison shows no changes to the
protected inputs, packet/template or full100 result files. A blank B01 passes
draft structure checks and is rejected as a completed submission. No review is
invented to make a gate green. Browser and human-review gates remain open.

## Stage C1 Calibration Preparation: 2026-09-04

Five historical cases are prepared, with zero completed reviews and zero new
labels. Selection includes missing dev q_0048, the first dev monthly-change and
negative-value questions, and the two already-public top3 examples. This is
purposive protocol calibration, not new held-out evaluation. The reviewer page
uses B01-B05 aliases without gold, old boundaries/labels, split or detector scores;
aliases do not erase prior familiarity. Original prompt wording and evidence
order are preserved. A separate warning distinguishes transaction signs from
confirmed physical returns and forbids retroactive gold changes.

Neutral atom types, format checks, row fidelity, full-relation verdicts, evidence
references, claim groups and character information endpoints are defined. The
offline form supports partial JSON export/import. Python and Node enforce schema,
Unicode offsets, no bare-rank decisive judgment, complete-scope unmatched rules,
and explicit coverage attestation. These checks do not adjudicate correctness or
verify that a human worked independently. Reviewer exports stay Git-ignored.

The packet is prepared for an owner trial; visual acceptance remains pending
because browser security prevented local-file inspection in prior work. Existing
Python/Node runtimes suffice; no plugin, model or new dependency was installed.
Next: owner tests one case, then calibrates all five; revise protocol if necessary,
prepare a separate second-reviewer pass, and only then consider 36-answer coverage.
B2 q_0048 atomic-label completion and threshold sensitivity are still pending;
v2 relation judgments must not be automatically substituted for v1 span labels.

## Stage B1 Statistical Appendix: 2026-09-04

This update supersedes earlier statements about the next stage and relative
detector strength. Original full100 result files and labels remain unchanged.
The separate `reports/bizhallu_statistics_v2_review.html` is the current
reader-facing statistical appendix, not a new Pages entry or confirmation result.

- Standard non-interpolated AP now groups tied scores; NaN/Inf and split/ID
  mismatches are rejected. Independent tests include randomized sklearn checks.
- All 100 saved answers reconstruct, and all 205 span alignments and 12 original
  six-decimal scores replay. A second arm aggregates saved float32 values without
  extra rounding. All 12 signals retain the same test confusion matrices.
- Test has 103 spans from all 18 test questions. Dev has 102 spans from 17
  questions; only dev q_0048 is missing. Positive labels include one unsupported
  claim along with 121 hallucinated spans across dev/test, not 122 hallucinations.
- The dev-only fact-type prior has test F1 0.835616, above entropy's 0.779412.
  It mainly removes correct month spans; it uses supplied annotation types and
  is not an automatic detector. Types include outcome-hinting names such as
  malformed_number; this is not an information-matched detector comparison.
  Its test binary predictions equal non-month = positive. Margin AP remains
  0.835073 versus prior 0.759838.
- Entropy versus all-positive F1 difference is 0.035509; a 5,000-draw paired
  question-bootstrap 95% interval is [-0.035604, 0.104732]. This is conditional on
  fixed dev policies and provisional labels, not selection-adjusted inference.
- Test resampling units are 18 questions, 15 normalized evidence contents, or
  two overlapping-month components built from the 35 evaluated questions.
  The two-component interval is a dependency diagnostic, not a reliable CI.
  Three normalized contents cross dev/test in this annotated subset; historical
  full100 overlap counts below use different populations/fingerprints.
- Same-step selected energy gap is mathematically NLL, and non-top1 mass is
  1 minus top1 probability. These are controls/aliases, not independent families.
- Raw teacher-forced logits are distinct from the generation sampling
  distribution. Additional decimal precision does not restore pre-float32 logits.

Public validation recomputes every new metric, dev fit and 15,000 paired draws.
The separate `--require-local` tier also reconstructs excluded traces. CI never
runs Qwen. Next is B2/C: calibrate relation annotations on five historical answers,
review q_0048 without detector scores, then version its dev-threshold sensitivity.
Independent human review is still required; no confirmation outcome is available.

## Stage A Business-Definition Amendment: 2026-09-04

This update supersedes the business wording in the original confirmation v1
question design, not its source periods, split or numeric evidence. The active
version is `configs/confirmation_metric_amendment_v1_1.json`; the study protocol
contains the active private-manifest path and commitment. Original v1 files are
retained for historical replay.

- Historical 100-question gold replay passed. Five explicitly separated
  scenarios produce a 500-row sensitivity table, not new model results.
- Switching all-ledger questions to merchandise scope changes 58 answers and
  one country leader. Stock-code grouping changes four product answers without
  changing their leading stock codes. Neither scenario overwrites the old gold.
- Non-merchandise lines account for 46.77% of historical negative value and
  57.67% of strict-prior-window negative value. Sign-based negative amounts are
  not confirmed physical-return amounts.
- v1.1 preserves all 48 contexts and all 96 numeric/entity gold answers, with
  revised wording/fields and new commitments. Source replay includes 798
  independent arithmetic checks. Gate 3 is revalidated; four other gates remain
  pending. No Qwen generation, annotation or detector scoring was performed.
- Public validators do not replay excluded private source data. The separate
  `--require-local` check is mandatory before calling this source-reproduced.

The next authorized batch is Stage B statistical hardening, not model
generation. Relation-level annotation, independent human review and a true
verifier follow; they are not complete because Stage A passed.

## Integrity Update: 2026-08-31

This update supersedes older public-facing wording later in this historical
audit. The underlying numeric artifacts are unchanged, but their interpretation
is now more precise:

- The 205-span package is an AI-assisted provisional annotation set across 35
  dev/test answers. Only 15 selected presentation spans received an additional
  assistant review. No independent human annotation or inter-annotator
  agreement has been completed.
- The 0.835 test AUPRC and 0.779 test F1 values are exploratory maxima from
  different candidate signals. Thresholds were selected on dev spans, but the
  winning signal for each headline metric was chosen after comparing test
  results. They are not confirmatory held-out model-selection estimates.
- Detector scores are computed for pre-identified business-fact spans. The
  current system does not automatically extract claims from unseen answers.
- `evidence_verifier_pilot.html` is retained as a stable URL, but its public
  artifact is now called Claim-Evidence Review Schema v0. Its statuses are
  direct mappings from selected presentation labels, not independent verifier
  predictions.

Older sections remain as an execution history and may use the earlier
"held-out" or "verifier pilot" shorthand. Use this update, `README.md`, and the
current generated Pages bundle for public claims.

## Methodology Hardening Update: 2026-08-31

A source-backed audit now adds four boundaries that were not explicit enough
in the earlier project narrative:

- The detector score package covers 35 of 36 dev/test questions. The 35-question
  batch was selected through a high-priority queue conditioned on generated-
  answer auto-status, so the 205-span evaluation is outcome-informed and likely
  error-enriched.
- The question split is deterministic and periodic within question type. It is
  not randomized or grouped by business month/evidence context.
- Dev and test share five business periods. Nine exact gold evidence-row
  fingerprint groups cross splits and involve 28 questions, so this experiment
  does not establish generalization to unseen evidence contexts.
- Dev-only threshold selection remains a valid implementation detail, but the
  headline detector for AUPRC and F1 was chosen after test comparison. The
  public numbers remain exploratory maxima.

`configs/methodology_protocol_v1.json` now separates this retrospective study
from a future confirmation study. The generated Methodology Hardening v1 report
recomputes these counts from committed artifacts, and its validator fails if
the sample, overlap, or locked-result facts drift.

## Confirmation Set v1 Design Update: 2026-09-01

The next study now has a prospective, machine-readable design, but execution has
not started. `configs/confirmation_set_v1_protocol.json` fixes the intended
sampling, context separation, annotation, evaluation-track, metric, and claim
policies before new model answers are viewed.

- The post-review planning target is 96 generations: a 12-question protocol
  pilot, 30 development questions, and 54 sealed confirmation questions. The
  protocol pilot is permanently excluded from confirmation metrics, so the
  main study contains 84 questions.
- Sampling is outcome-blind at the `evidence_context_id` level. The design does
  not force a 50/50 correct-error balance and does not replace outputs after
  answer quality is observed.
- All new-study splits must use disjoint business periods and canonical
  evidence fingerprints. Exact evidence fingerprints from the historical
  full100 exploratory study are also excluded.
- Two independent human reviewers are required. Assistant support may prepare
  packets and validate offsets but does not count as an independent reviewer.
- Every in-scope business-fact claim in every selected answer is annotated; no
  high-priority or error-enriched span subset is allowed. In the binary oracle
  task, both `contradicted` and `unmatched` are positive unsupported claims.
- Oracle-span diagnostics, automatic claim extraction, evidence verification,
  and end-to-end auditing are reported as four separate evaluation tracks.
- AUPRC is the primary oracle-span metric. Thresholded F1 is secondary and must
  reuse a development-frozen threshold; uncertainty intervals use a cluster
  bootstrap by evidence context.
- Internal uncertainty, literature-grounded baselines, evidence-aware
  verification, and an optional frozen hybrid remain comparison families.
- The first two of seven execution gates are complete; five downstream gates
  remain deliberately pending. The official Online Retail II
  ZIP and workbook are acquired, hashed, and Git-ignored; the two-sheet structure,
  three raw-header aliases, and 502,938-row strict prior-period boundary are
  verified. Completeness, duplicate/grain behavior, cancellation/value rules,
  and all 12 expected months are now profiled with documented controls. Canonical
  eight-field and date-blind seven-field comparisons both found zero repeated
  current-source records. An outcome-blind feasibility profile found 50 observed
  complete weeks and proved a 48-of-48 period-to-family matching across three
  allowed families, with minimum Hall-capacity slack 2. Customer concentration
  remains blocked because 100,207 Customer IDs are missing. A subsequent
  outcome-blind freeze now retains 48 selected periods and their 6/15/27 split
  in a Git-ignored private manifest under a public SHA-256 commitment. Questions,
  prompts, and model outcomes still do not exist.

The generated report at
`reports/bizhallu_confirmation_set_v1_design.html` introduces no new detector
metric. The current 0.835 AUPRC and 0.779 F1 remain historical exploratory
maxima and are not targets or results for Confirmation Set v1.

The companion source audit at
`reports/bizhallu_confirmation_dataset_source_audit.html` compares six routes,
records official source and license evidence, and keeps Complete Journey as the
preferred external-replication shortlist candidate. The selected source is now
locally acquired, structurally inspected, quality-profiled, and separated from
the current source at normalized record level. This remains same-retailer,
  same-lineage temporal replication, not external independence. The precision
  review and claim amendment below supersede the original 6/15/15 planning
  counts. No context manifest, prompt, generation, annotation target, or new
  empirical metric was created.

## Outcome-Blind Precision Review Update: 2026-09-02

Before selecting any contexts, a frozen simulation review evaluated 15, 21,
24, and 27 confirmation contexts under 16 central and 4 stress scenarios. It
used synthetic labels and detector scores only; no confirmation context,
answer, annotation, or detector outcome was accessed.

- None of the four candidates passed every frozen strong-comparison rule. The
  decision thresholds were not relaxed after the result.
- The largest capacity-feasible candidate, 27 confirmation contexts, passed 10
  of 16 preferred central scenarios. Its worst central median AUPRC half-width
  was 0.121219 and its worst central median paired-difference half-width was
  0.097796. These are simulation planning quantities, not empirical detector
  results.
- The study was narrowed from a detector-superiority design to an estimation-
  focused design. Detector-family AUPRC intervals are primary; paired
  differences and subgroup results are descriptive. Confirmation Set v1 must
  not be used to claim one detector family is statistically superior.
- The revised plan is 6 protocol-pilot, 15 development, and 27 confirmation
  contexts, with two questions per context: 48 contexts and 96 questions total.
- The aggregate capacity proof was rerun for the revised target. Fifty observed
  complete weeks support a 48-of-48 period-to-family matching with minimum Hall
  slack 2. No matching assignment or candidate-period list was retained.
- At this precision-review checkpoint, the next authorized action was only to
  freeze the deterministic 6/15/27 context manifest and seeded,
  period-disjoint split. The manifest update below records completion of that
  step; question generation, prompts, Qwen execution, annotation, and new
  detector metrics remain blocked.

## Context Manifest Freeze Update: 2026-09-02

The authorized manifest-only step is now complete without creating a new model
result.

- A deterministic, outcome-blind bipartite assignment fixed 48 unique complete
  weeks across three eligible families: 16 contexts per family.
- Each family is split into 2 protocol-pilot, 5 development, and 9 confirmation
  contexts, giving 6/15/27 overall. Two unmatched weeks remain source reserve
  and cannot replace difficult outputs after outcome access.
- The detailed manifest is Git-ignored. It contains selected periods, context
  IDs, family/split assignments, eligible scope entities, and canonical
  context evidence-pool hashes.
- The public report exposes aggregate counts and the whole-manifest canonical
  SHA-256 commitment only. It publishes no selected period, context ID, entity,
  invoice, customer value, or row fingerprint.
- All 48 selected periods, context IDs, and context evidence-pool hashes are
  unique. Historical canonical and date-blind source-record overlap remains 0.
- At this context-manifest checkpoint, exact question-level evidence payload
  fingerprint checks remained pending because deterministic question templates
  and gold payloads had not yet been created. The later Gate 3 update below
  supersedes that temporary boundary without altering this historical record.
- No question, gold answer, prompt, Qwen output, annotation, detector score,
  verifier prediction, AUPRC, F1, or other new empirical metric was created.

## Question and Gold Freeze Update: 2026-09-02

Gate 3 is now complete without running Qwen or creating a new empirical result.

- Six deterministic templates create two questions for each of the 48 frozen
  contexts: 12 protocol-pilot, 30 development, and 54 confirmation questions.
  The private inventory therefore contains 96 questions, with 32 questions per
  eligible business family.
- Net-revenue reconciliation includes weekly arithmetic and a daily
  cancellation-hotspot question. Product return comparison uses two disjoint
  product pairs per context and explicitly measures recorded returned units
  divided by positive units; it is not a customer-linked causal return rate.
  Country-product exposure selects the highest-revenue product only among five
  frozen candidates and reports its share of country merchandise net revenue.
- Question IDs, entity choices, and evidence presentation order use
  domain-separated seeded SHA-256 ordering. They do not use generated answers,
  labels, detector scores, or future model behavior.
- All 96 full payloads and all 96 normalized evidence-table contents have unique
  canonical fingerprints. Exact cross-split and cross-context overlap are both
  0. The normalized contents match 0 of the 66 unique historical full100
  evidence-table contents after wrapper metadata is removed and documented field
  aliases are normalized. These are exact-content controls, not a claim of
  external-domain independence.
- The detailed question/gold manifest is Git-ignored. It contains question IDs,
  question text, gold answers, selected entities, and evidence rows. The public
  report exposes only rules, aggregate counts, and the whole-manifest canonical
  SHA-256 commitment
  `b72ffaf715afef85867522fb0c7264377350ce146709962e420c16eaa6d9e80c`.
- No prompt, model output, annotation, detector score, verifier score, or new
  confirmation metric was created. Confirmation Set v1 remains design-only and
  has three of seven execution gates complete.

## Historical Record-Overlap Update: 2026-09-01

The frozen strict prior window was compared with the complete current Online
Retail source using domain-separated SHA-256 fingerprints over normalized
business fields. The proof is multiplicity-aware: duplicate copies cannot be
hidden by converting records to a simple set.

- Primary eight-field canonical overlap: 0 unique fingerprints and 0 multiset
  rows across 502,938 prior rows and 541,909 current rows.
- Date-blind seven-field sensitivity overlap: 0 unique fingerprints and 0
  multiset rows. The primary result therefore does not depend only on including
  the disjoint timestamp.
- The final prior record precedes the first current record by 12 hours 51
  minutes.
- A positive-control lineage comparison recovered all 541,909 current rows from
  the 541,910-row Online Retail II 2010-2011 sheet; the latter contains one
  additional source row. This validates canonicalization but does not establish
  external independence.
- There are 195,814 multiplicity-aware shared five-field business patterns.
  Product, description, customer, and country entities also overlap, as expected
  for the same retailer. These are disclosed as domain continuity, not counted
  as repeated records.
- Public artifacts expose aggregate counts and whole-inventory manifest hashes
  only. Raw invoice values, customer values, and row fingerprints remain local.

The historical-overlap sub-check is complete. This paragraph records the state
at the overlap checkpoint; the later capacity and precision updates above now
supersede it. The source gate is complete, 48-context capacity is verified, and
the combined context-manifest/split gate remains pending.

## Audit Scope

This audit reviews the current BizHallu project state after data preparation,
Qwen pilot generation, pilot review, annotation guideline drafting, and
pilot20 span annotation, coverage review, span-token alignment, and pilot
simple baseline evaluation, error review, error-family analysis, top3 structured
prompt variant generation, the 3-question top3 structured pilot evaluation, and
the sorted-evidence top3 diagnostic control plus token-signal, stock-code
score distribution, energy-trace readiness, and full100 run-config readiness
reviews, plus pilot20 energy retrace, energy baseline evaluation,
split-safe detector evaluation prep, full100 preflight, full100 generation,
full100 review-table preparation, full100 annotation queue preparation, and a
35-question held-out high-priority draft annotation file plus its consistency
audit, span-token alignment, validated detector score-file preparation,
simple/energy split-safe metric passes, detector-family comparison, and
full100 detector error review, report-ready detector interpretation, a focused
label confirmation packet, assistant review notes for the selected
presentation examples, a label lock package for portfolio use, a static
portfolio demo page built from the locked primary examples, a long-form
portfolio narrative page for presentation and career-branding use, and a
GitHub Pages-ready public bundle under `docs/`.

## Current Conclusion

The project direction remains coherent and feasible:

```text
auditable retail data -> deterministic business questions -> Qwen answers
-> span-level labels -> detector scores -> portfolio demo/report
```

The most important finding from execution is that Qwen3-0.6B makes frequent but
labelable business-analysis errors. The pilot set contains both correct spans
and hallucinated spans, so the span-level detection framing is still viable.

The first simple token-logit baselines show weak-to-moderate signal on pilot20:
best AUPRC is 0.703, best F1 is 0.691, and the all-positive reference F1 is
0.676. This means the pilot has detectable signal, but thresholded F1 is not a
strong final claim yet.

The baseline error review is now generated, so the project can inspect concrete
false positives and false negatives before scaling beyond pilot20.

The first error-family analysis groups 101 baseline-error rows into 52 unique
annotated span errors and 7 error families. This turns the pilot result from a
metric table into a diagnosis of why simple uncertainty fails.

The top3 structured prompt variant has now been run on the 3-question pilot.
It produced valid tables, but did not fix the underlying ranking failure:
0/3 exact top3 lists and 0/9 rank-position stock codes were correct. This is a
useful negative result because it isolates the issue as row selection and
sorting over evidence, not free-form answer formatting.

The sorted-evidence diagnostic control improved the same three questions to 2/3
exact top3 lists and 6/9 rank-position stock codes. The remaining failure is
`q_0065`, where the model skipped the highest-revenue evidence row even though
the table was sorted by net revenue. This clarifies the story: shuffled evidence
creates a strong row-selection/sorting failure, but Qwen3-0.6B can still miss
salient evidence even under an answer-visible control.

The token-signal review on `q_0065` shows a nuanced detector story. Simple
entropy and top-2 margin thresholds flag all wrong stock-code spans, but also
flag all correct stock-code spans in the two correct sorted-control answers.
The signal is sensitive to stock-code choice points, but not specific enough to
separate correct rank binding from wrong rank binding.

The stock-code distribution review confirms that the issue is not merely one
bad threshold. Max token entropy gives the best local ranking signal on the 9
stock-code spans, but the correct and incorrect score ranges overlap.

The energy-trace readiness check is now complete. The trace generator saves the
raw-logit and adjacent-step fields needed for a Spilled Energy adapter, and a
3-question rerun produced 359 token traces with all energy fields present and
formula-consistency checks passing. The regenerated answers match the earlier
sorted-control answers exactly, so the trace change did not change prompt
behavior.

The full100 generation config has now been used successfully. It listed all
100 question ids, preserved the 64 train / 18 dev / 18 test split, and wrote
outputs with the intended `qwen_full100` prefix rather than falling back to the
5-question smoke-test default.

The pilot20 energy retrace and baseline evaluation is now complete. Existing
pilot20 answers were not regenerated; the model was only used for a raw forward
pass over the saved prompt plus generated token ids. The retrace produced 20
energy-ready traces, 1660 token records, and 135/135 aligned annotated spans.
The adapter is operational, but the pilot result is a negative finding for pure
Spilled Energy: adjacent-step Spilled Energy features underperform the best
simple max-entropy baseline.

The split-safe detector evaluator is now implemented. It selects detector
thresholds on dev spans and reports test metrics using the fixed dev threshold.
A synthetic smoke fixture with real dev/test question ids passes, while the
train-only pilot20 score file is correctly rejected as not eligible for
held-out evaluation.

The consolidated full100 preflight now passes with 0 failures and
`ready_for_current_stage=true`. Its current stage is `github_pages_ready`; the older
`ready_to_run_full100_generation=true` field is retained only for backward
compatibility with earlier reports. It also detects that
`full100_generation_run=true` after validation. The remaining work is now
choosing a slide-deck or optional app branch.

The full100 review table is now prepared. It combines each generated answer
with gold answers, gold facts, prompt evidence rows, and evidence tables. This
closes the gap between raw model output and manual span annotation.

The first full100 annotation seed is also prepared. It labels 18 business-fact
spans across 5 held-out high-priority rows and validates exact character
offsets against the saved full100 generations. This confirms the schema and
offset mechanics before expanding to the full 35-row held-out batch.

The full100 held-out high-priority draft now covers all 35 selected dev/test
rows with 205 spans. The consistency audit has 0 hard failures. The audit-note
review resolved all four original notes, including one label change for
`q_0049`, and the span-token alignment validates 205/205 aligned spans with
simple and energy score fields present. The detector score-file step now
validates 205 score rows with 12 configured simple/energy fields and balanced
positive/negative coverage within both dev and test. No final detector metrics
had been reported at the score-file stage; the first split-safe metric pass is
now complete for both simple and energy baseline families. The family
comparison shows the best overall held-out test AUPRC and F1 both come from
simple uncertainty fields, while the best energy-family F1 comes from a
probability-mass control rather than pure adjacent-step energy. The full100
detector error review is now complete for the selected simple best-AUPRC and
energy best-F1 rows, and the report-ready detector interpretation page has
been generated and validated. A focused 15-span label confirmation packet is
complete. Assistant review notes cover those 15 items: all selected labels are
supported by this review pass, 0 source annotation fixes are recommended, and
6 items are flagged as span-level caveats because the surrounding generated
answer contains other errors. The label lock package now locks all 15 selected
spans with `lock_basis=assistant_full_review`; `q_0064` and `q_0069` are the
primary portfolio examples. The portfolio demo page now packages those two
questions into a validated presentation artifact. The portfolio narrative page
now turns the experiment into a full project story with pitch, resume bullets,
slide outline, and guardrails. The GitHub Pages bundle now exposes those pages
from `docs/index.html` with checked local links.

## Completed Artifacts

Data:

- Raw UCI Online Retail data in `data/raw/`.
- Cleaned and normalized data in `data/processed/`.
- Deterministic summary tables for month, country, product, and returns.

Question and prompt pipeline:

- 100 gold business questions in `data/processed/business_questions_gold.jsonl`.
- 100 Qwen prompt records in `outputs/qwen_input_prompts.jsonl`.
- Prompt design avoids leaking top-ranked answers through row order.

Generation:

- Single dry run: `outputs/qwen_dry_run_generation.jsonl`.
- Batch5 sampling and greedy smoke tests.
- Pilot20 generation and raw-logit token traces:
  - `outputs/qwen_pilot20_generations.jsonl`
  - `outputs/qwen_pilot20_token_traces.jsonl`
- Full100 generation and energy-ready token traces:
  - `outputs/qwen_full100_generations.jsonl`
  - `outputs/qwen_full100_token_traces.jsonl`
  - `outputs/qwen_full100_report.json`
  - `outputs/qwen_full100_validation.json`
  - `outputs/qwen_full100_stdout.log`
  - `outputs/qwen_full100_stderr.log`
- Full100 review:
  - `outputs/full100_review.csv`
  - `outputs/full100_review.jsonl`
  - `outputs/full100_review_sample.csv`
  - `outputs/full100_review_report.json`
  - `outputs/full100_review_validation.json`
- Full100 annotation queue:
  - `outputs/full100_annotation_queue.csv`
  - `outputs/full100_annotation_queue.jsonl`
  - `outputs/full100_heldout_high_annotation_batch.csv`
  - `outputs/full100_heldout_high_annotation_batch.jsonl`
  - `outputs/full100_annotation_queue_report.json`
  - `outputs/full100_annotation_queue_validation.json`
- Full100 annotation seed:
  - `data/annotations/span_annotations_full100_seed.jsonl`
  - `outputs/full100_annotation_seed_preview.csv`
  - `outputs/full100_annotation_seed_report.json`
  - `outputs/full100_annotation_seed_policy_review.json`
  - `outputs/full100_annotation_seed_validation.json`
- Full100 annotation draft:
  - `data/annotations/span_annotations_full100_draft.jsonl`
  - `outputs/full100_annotation_draft_preview.csv`
  - `outputs/full100_annotation_draft_report.json`
  - `outputs/full100_annotation_draft_round1_review.json`
  - `outputs/full100_annotation_draft_round2_review.json`
  - `outputs/full100_annotation_draft_round3_review.json`
  - `outputs/full100_annotation_draft_round4_review.json`
  - `outputs/full100_annotation_draft_validation.json`
- Full100 annotation consistency audit:
  - `outputs/full100_annotation_consistency_audit_report.json`
  - `outputs/full100_annotation_consistency_audit_by_question.csv`
  - `outputs/full100_annotation_consistency_audit_by_split.csv`
  - `outputs/full100_annotation_consistency_audit_policy_flags.csv`
- Full100 audit-note review:
  - `outputs/full100_audit_note_review.csv`
  - `outputs/full100_audit_note_review_report.json`
  - `outputs/full100_audit_note_review_validation.json`
- Full100 draft span-token alignment:
  - `outputs/full100_draft_span_token_alignment.jsonl`
  - `outputs/full100_draft_span_token_alignment.csv`
  - `outputs/full100_draft_span_token_alignment_report.json`
  - `outputs/full100_draft_span_token_alignment_validation.json`
  - `outputs/full100_draft_span_token_alignment_by_split.csv`
  - `outputs/full100_draft_span_token_alignment_by_question.csv`
- Full100 draft detector score files:
  - `results/full100_draft_detector_scores.csv`
  - `results/full100_draft_detector_scores_by_split.csv`
  - `results/full100_draft_detector_scores_report.json`
  - `results/full100_draft_detector_scores_validation.json`
- Full100 simple split-safe metrics:
  - `results/full100_draft_simple_split_metrics.csv`
  - `results/full100_draft_simple_split_report.json`
  - `results/full100_draft_simple_split_validation.json`
- Full100 energy split-safe metrics:
  - `results/full100_draft_energy_split_metrics.csv`
  - `results/full100_draft_energy_split_report.json`
  - `results/full100_draft_energy_split_validation.json`
- Full100 detector-family comparison:
  - `results/full100_draft_detector_family_comparison.csv`
  - `results/full100_draft_detector_family_summary.csv`
  - `results/full100_draft_detector_family_comparison_report.json`
  - `results/full100_draft_detector_family_comparison_validation.json`
- Full100 detector error review:
  - `results/full100_draft_detector_error_review.csv`
  - `results/full100_draft_detector_error_review_by_baseline.csv`
  - `results/full100_draft_detector_error_review_by_fact_type.csv`
  - `results/full100_draft_detector_error_review_by_question_type.csv`
  - `results/full100_draft_detector_error_review_examples.csv`
  - `results/full100_draft_detector_error_review_report.json`
  - `results/full100_draft_detector_error_review_validation.json`
- Full100 detector interpretation:
  - `reports/full100_detector_interpretation.html`
  - `reports/full100_detector_interpretation_summary.json`
  - `reports/full100_detector_interpretation_validation.json`
- Full100 label confirmation packet:
  - `reports/full100_label_confirmation_packet.html`
  - `reports/full100_label_confirmation_packet.csv`
  - `reports/full100_label_confirmation_packet.jsonl`
  - `reports/full100_label_confirmation_packet_summary.json`
  - `reports/full100_label_confirmation_packet_validation.json`
- Full100 label confirmation review notes:
  - `reports/full100_label_confirmation_review_notes.html`
  - `reports/full100_label_confirmation_review_notes.csv`
  - `reports/full100_label_confirmation_review_notes.jsonl`
  - `reports/full100_label_confirmation_review_notes_summary.json`
  - `reports/full100_label_confirmation_review_notes_validation.json`
- Full100 label lock package:
  - `reports/full100_label_lock_report.html`
  - `reports/full100_label_lock_decisions.csv`
  - `reports/full100_label_lock_decisions.jsonl`
  - `reports/full100_label_lock_summary.json`
  - `reports/full100_label_lock_validation.json`
- Portfolio demo package:
  - `reports/bizhallu_portfolio_demo.html`
  - `reports/bizhallu_portfolio_demo_summary.json`
  - `reports/bizhallu_portfolio_demo_validation.json`
- Portfolio narrative package:
  - `reports/bizhallu_portfolio_narrative.html`
  - `reports/bizhallu_portfolio_narrative_summary.json`
  - `reports/bizhallu_portfolio_narrative_validation.json`
- GitHub Pages package:
  - `docs/index.html`
  - `docs/portfolio_demo.html`
  - `docs/portfolio_narrative.html`
  - `docs/detector_interpretation.html`
  - `docs/label_lock_report.html`
  - `docs/label_confirmation_packet.html`
  - `docs/github_pages_manifest.json`
  - `docs/github_pages_validation.json`

Review and annotation preparation:

- Pilot20 selection config: `configs/pilot20_questions.json`.
- Pilot20 review table: `outputs/pilot20_review.csv`.
- Annotation guidelines: `data/annotations/annotation_guidelines.md`.
- Pilot20 span annotations: `data/annotations/span_annotations_pilot.jsonl`.
- Pilot20 coverage review:
  - `outputs/pilot20_span_coverage_report.json`
  - `outputs/pilot20_span_coverage_by_question.csv`
  - `outputs/pilot20_span_coverage_by_fact_type.csv`
- Pilot20 span-token alignment:
  - `outputs/pilot20_span_token_alignment.jsonl`
  - `outputs/pilot20_span_token_alignment.csv`
  - `outputs/pilot20_span_token_alignment_report.json`
- Pilot20 simple baseline sanity check:
  - `results/pilot20_simple_baseline_scores.csv`
  - `results/pilot20_simple_baseline_metrics.csv`
  - `results/pilot20_simple_baseline_report.json`
  - `results/pilot20_simple_baseline_validation.json`
  - `results/confusion_matrices/pilot20_simple_baselines_confusion_matrices.csv`
- Pilot20 baseline error review:
  - `results/pilot20_baseline_error_review.csv`
  - `results/pilot20_baseline_error_summary.json`
  - `results/pilot20_baseline_error_review_validation.json`
- Pilot20 error-family analysis:
  - `results/pilot20_error_analysis_by_family.csv`
  - `results/pilot20_error_analysis_examples.csv`
  - `results/pilot20_error_analysis_summary.json`
  - `results/pilot20_error_analysis_validation.json`
- Top3 structured prompt variant:
  - `outputs/qwen_top3_structured_prompts.jsonl`
  - `outputs/qwen_top3_structured_prompts_sample.csv`
  - `outputs/qwen_top3_structured_prompts_report.json`
  - `outputs/qwen_top3_structured_prompts_validation.json`
  - `configs/top3_structured_pilot3_questions.json`
- Top3 structured pilot generation and evaluation:
  - `outputs/qwen_top3_structured_pilot3_generations.jsonl`
  - `outputs/qwen_top3_structured_pilot3_token_traces.jsonl`
  - `outputs/qwen_top3_structured_pilot3_report.json`
  - `outputs/qwen_top3_structured_pilot3_validation.json`
  - `results/top3_structured_pilot3_evaluation.csv`
  - `results/top3_structured_pilot3_report.json`
  - `results/top3_structured_pilot3_validation.json`
- Top3 sorted-evidence diagnostic control:
  - `outputs/qwen_top3_sorted_control_prompts.jsonl`
  - `outputs/qwen_top3_sorted_control_prompts_sample.csv`
  - `outputs/qwen_top3_sorted_control_prompts_report.json`
  - `outputs/qwen_top3_sorted_control_prompts_validation.json`
  - `configs/top3_sorted_control_pilot3_questions.json`
  - `outputs/qwen_top3_sorted_control_pilot3_generations.jsonl`
  - `outputs/qwen_top3_sorted_control_pilot3_token_traces.jsonl`
  - `outputs/qwen_top3_sorted_control_pilot3_report.json`
  - `outputs/qwen_top3_sorted_control_pilot3_validation.json`
  - `results/top3_sorted_control_pilot3_evaluation.csv`
  - `results/top3_sorted_control_pilot3_report.json`
  - `results/top3_sorted_control_pilot3_validation.json`
  - `results/top3_prompt_condition_comparison.csv`
  - `results/top3_prompt_condition_comparison.json`
  - `results/top3_prompt_condition_comparison_validation.json`
- Top3 sorted-control token-signal review:
  - `results/top3_sorted_control_token_signal_spans.csv`
  - `results/top3_sorted_control_token_signal_summary.json`
  - `results/top3_sorted_control_token_signal_validation.json`
- Top3 stock-code score distribution:
  - `results/top3_stock_code_score_distribution.csv`
  - `results/top3_stock_code_score_distribution_summary.json`
  - `results/top3_stock_code_score_distribution_validation.json`
- Energy trace readiness:
  - `outputs/qwen_top3_sorted_control_pilot3_energy_generations.jsonl`
  - `outputs/qwen_top3_sorted_control_pilot3_energy_token_traces.jsonl`
  - `outputs/qwen_top3_sorted_control_pilot3_energy_report.json`
  - `outputs/qwen_top3_sorted_control_pilot3_energy_validation.json`
  - `results/energy_trace_readiness_report.json`
  - `results/energy_trace_readiness_validation.json`
- Full100 run config readiness:
  - `configs/full100_questions.json`
  - `outputs/full100_config_validation.json`
- Pilot20 energy retrace and baselines:
  - `outputs/qwen_pilot20_energy_generations.jsonl`
  - `outputs/qwen_pilot20_energy_token_traces.jsonl`
  - `outputs/qwen_pilot20_energy_report.json`
  - `outputs/qwen_pilot20_energy_validation.json`
  - `outputs/pilot20_energy_span_token_alignment.jsonl`
  - `outputs/pilot20_energy_span_token_alignment.csv`
  - `outputs/pilot20_energy_span_token_alignment_report.json`
  - `results/pilot20_energy_baseline_scores.csv`
  - `results/pilot20_energy_baseline_metrics.csv`
  - `results/pilot20_energy_baseline_report.json`
  - `results/pilot20_energy_baseline_validation.json`
  - `results/confusion_matrices/pilot20_energy_baselines_confusion_matrices.csv`
  - `results/pilot20_detector_readiness_summary.json`
  - `results/pilot20_detector_readiness_validation.json`
- Split-safe evaluation prep:
  - `configs/detector_baseline_suite.json`
  - `outputs/split_eval_smoke_scores.csv`
  - `outputs/split_eval_smoke_scores_report.json`
  - `results/split_eval_smoke_metrics.csv`
  - `results/split_eval_smoke_report.json`
  - `results/split_eval_smoke_validation.json`
  - `results/pilot20_train_only_split_guard_report.json`
- Full100 preflight:
  - `results/full100_preflight_report.json`
  - `results/full100_preflight_validation.json`

Presentation:

- Static project overview: `site/index.html`.
- Static portfolio demo: `reports/bizhallu_portfolio_demo.html`.
- Static portfolio narrative: `reports/bizhallu_portfolio_narrative.html`.
- GitHub Pages entry point: `docs/index.html`.

## Validation Status

Latest checks all pass:

- Processed data: 21 checks, 0 failures.
- Gold questions: 100 records, 0 failures.
- Prompt inputs: 100 records, 0 failures.
- Qwen dry run: 0 failures.
- Batch5 sampling: 0 failures.
- Batch5 greedy: 0 failures.
- Pilot20 generation: 20 generations and 20 traces, 0 failures.
- Pilot20 review table: 20 rows, 0 failures.
- Annotation guidelines: 0 failures.
- Pilot20 span annotations: 135 spans across 20 answers, 0 failures.
- Pilot20 coverage review: ready for pilot simple baselines, with 66 negative
  spans and 69 positive spans.
- Pilot20 span-token alignment: 135 aligned spans, 0 failures.
- Pilot20 simple baseline validation: 135 score rows, 5 baselines, 0 failures.
- Pilot20 baseline error review: 101 error rows across 2 selected baselines,
  0 failures.
- Pilot20 error analysis: 7 error families, 52 unique annotated span errors,
  0 failures.
- Top3 structured prompts: 13 prompts, deterministic hash evidence order,
  0 failures.
- Top3 structured pilot generation: 3 generations and 3 traces, 0 failures.
- Top3 structured pilot evaluation: 3/3 parseable tables, 0 infrastructure
  failures.
- Top3 sorted-control prompts: 13 prompts, sorted evidence order, 0 failures.
- Top3 sorted-control pilot generation: 3 generations and 3 traces, 0 failures.
- Top3 sorted-control pilot evaluation: 3/3 parseable tables, 0 infrastructure
  failures.
- Top3 prompt-condition comparison: same 3 question ids, 0 failures.
- Top3 sorted-control token-signal review: 36 generated spans, 12 focus spans
  for `q_0065`, 0 failures.
- Top3 stock-code score distribution: 9 stock-code spans, 6 correct and 3
  incorrect rank bindings, 0 failures.
- Energy trace readiness: 3 generations, 359 generated token traces, 359 tokens
  with all energy fields, 0 failures.
- Full100 config readiness: 100 question ids, 64 train / 18 dev / 18 test, 0
  failures.
- Pilot20 energy retrace: 20 generations copied, 20 energy traces, 1660 token
  records, 0 failures.
- Pilot20 energy span alignment: 135/135 spans, 0 failures.
- Pilot20 energy baselines: 135 score rows, 7 baselines, 0 failures.
- Detector readiness summary: simple and energy metrics compared, 0 failures.
- Split-safe evaluator smoke test: 8 synthetic rows, 2 detector fields, dev
  threshold reused on test, 0 failures.
- Train-only split guard: pilot20 train-only scores rejected as expected.
- Full100 preflight: gold questions, prompts, full100 config, energy traces,
  energy baselines, detector readiness, and split evaluator checks aggregated,
  0 failures.
- Full100 generation: 100 generations, 100 token traces, 7,575 generated
  tokens, 64 train / 18 dev / 18 test, 0 validation failures with
  `--require-energy-fields`.
- Full100 review: 100 rows, 100 JSONL records, 20 sample rows, 64 train / 18
  dev / 18 test, 0 validation failures.
- Full100 annotation queue: 100 rows, initial held-out high-priority batch of
  35 rows, 17 dev / 18 test, 0 validation failures.
- Full100 annotation seed: 5 held-out high-priority rows, 18 spans, 3 dev / 2
  test questions, 0 validation failures.
- Full100 annotation draft through round 4: all 35 held-out high-priority rows,
  205 spans, 17 dev / 18 test questions, 0 validation failures.
- Full100 annotation consistency audit: 0 hard failures, 3 remaining confirmed
  warning qids, `ready_for_alignment=true`.
- Full100 audit-note review: 4 questions reviewed, 1 label change applied,
  0 validation failures.
- Full100 draft span-token alignment: 205/205 spans aligned, 17 dev / 18 test
  questions, simple and energy score fields present, 0 validation failures,
  `metrics_reported=false`.
- Full100 detector score files: 205 score rows, 102 dev span rows, 103 test
  span rows, 12 simple/energy score fields, 0 validation failures, and
  `metrics_reported=false`.
- Full100 simple split-safe metrics: 5 baselines, 10 dev/test metric rows,
  thresholds selected on dev and reused on test, 0 validation failures.
- Full100 energy split-safe metrics: 7 baselines, 14 dev/test metric rows,
  thresholds selected on dev and reused on test, 0 validation failures.
- Full100 detector-family comparison: 12 baseline rows, 2 family summary rows,
  4 all-positive-like energy thresholds flagged, 0 validation failures.
- Full100 detector error review: 57 held-out test error rows across 2 selected
  baselines, grouped by fact type and question type, 0 validation failures.
- Full100 detector interpretation: report-ready draft generated from source
  result files, 0 validation failures.
- Full100 label confirmation packet: 15 selected spans across 9 questions,
  20 source detector-error example rows covered, 0 validation failures, labels
  not locked.
- Full100 label review notes: 15/15 selected labels supported, 0 source fixes,
  and 0 validation failures.
- Full100 label lock package: 15/15 selected spans locked with
  `lock_basis=assistant_full_review`, 0 source fixes, and 0 validation failures.
- Portfolio demo: `q_0064` and `q_0069` packaged with 7 locked primary spans,
  source-backed detector readouts, and 0 validation failures.

## Design vs Reality

### What Matched the Plan

- UCI Online Retail supports deterministic business questions well.
- The net revenue policy is reproducible and validates against line-level data.
- The question types cover realistic business-analysis failures:
  - wrong country or product
  - wrong ranking
  - wrong comparison direction
  - wrong arithmetic
  - gross/net/return confusion
- Qwen3-0.6B runs locally on CUDA and produces usable token traces.

### What Changed During Execution

- The project originally considered larger or paper-heavy baselines early. The
  current MVP should start with simple logit baselines before adapting paper
  methods.
- Pilot annotation was reduced from 30 answers to 20 answers to keep review
  manageable and avoid overcommitting before label rules are stable.
- TOHA remains deferred because the available implementation path is not yet
  reliable enough for this MVP.
- Hidden-state probe remains deferred because current Qwen runs do not save
  hidden states.
- `run_qwen_batch.py` now accepts `--prompts-path`, so structured prompt
  variants can be run without overwriting or replacing the base prompt file.
- `evaluate_top3_structured_pilot.py` now accepts prompt, generation prefix,
  config, output prefix, and condition-name arguments, so prompt conditions can
  be evaluated with the same logic.
- `build_top3_sorted_control_token_signal_review.py` creates automatic
  row/cell spans from structured tables and maps them to token uncertainty
  scores.
- `build_top3_stock_code_score_distribution.py` compares correct vs incorrect
  stock-code score distributions for the sorted-control run.
- `run_qwen_dry_run.py` and `run_qwen_batch.py` now write energy-ready trace
  fields from raw forward logits. `validate_qwen_batch.py` can enforce these
  fields with `--require-energy-fields`.
- `build_energy_trace_readiness_report.py` summarizes energy field coverage and
  formula-consistency checks before any full100 generation.
- `validate_full100_config.py` validates the explicit 100-question generation
  config and prevents accidentally using the 5-question smoke-test default.
- `retrace_qwen_outputs.py` rebuilds raw-logit traces for saved generations
  without regenerating answers.
- `evaluate_pilot_energy_baselines.py` and
  `validate_pilot_energy_baselines.py` evaluate and validate energy-style
  pilot baselines.
- `build_detector_readiness_summary.py` compares simple and energy baseline
  families before full100.
- `evaluate_detector_split_metrics.py` implements dev-threshold/test-metric
  evaluation for detector score files.
- `validate_detector_split_metrics.py` validates split-safe metric outputs.
- `build_split_eval_smoke_fixture.py` creates a tiny dev/test fixture to test
  the evaluator before full100.
- `build_full100_preflight_report.py` aggregates the required readiness checks
  and records whether full100 generation is safe to start.
- `build_full100_review.py` joins full100 generations with gold answers, gold
  facts, and evidence for manual review.
- `validate_full100_review.py` verifies review row order, split counts,
  generation text, prompt evidence, gold answer, gold facts, and JSONL parity.
- `build_full100_annotation_queue.py` creates the ordered full100 annotation
  queue and the initial held-out high-priority batch.
- `validate_full100_annotation_queue.py` verifies phase counts, initial-batch
  split counts, row order, and annotation template fields.
- `build_full100_annotation_seed.py` creates a draft 5-question span-label seed
  from the first held-out high-priority top-country rows.
- `build_full100_annotation_draft.py` combines the seed with balanced
  round-1 through round-4 multi-type expansion batches and writes the current
  35-question held-out high-priority full100 draft annotation file.
- `validate_span_annotations.py` now accepts `--generation-file`, so the same
  offset/schema validator can check both pilot20 and full100 annotation files.
- The default base conda Python does not have `torch`; model runs should use
  `C:\Users\yuchi\anaconda3\envs\torch\python.exe`, as documented in
  `docs/qwen_setup.md`.

### Useful Model Behavior

The pilot confirms that Qwen3-0.6B is weak enough to produce factual errors but
not useless:

- Easy country questions include likely correct facts.
- Medium product/ranking questions produce clear wrong entities and amounts.
- Comparison questions expose direction contradictions.
- Return-impact questions expose numeric and formatting issues.

This is useful for a hallucination-detection benchmark because it gives both
positive and negative span labels.

### Simple Baseline Behavior

The first baseline pass is useful as a sanity check, not a final result:

- Max token entropy has the best pilot AUPRC at 0.703.
- One-minus minimum top-2 margin has the best pilot F1 at 0.691.
- The all-positive reference F1 is already 0.676 because the pilot spans are
  nearly balanced.
- Pilot thresholds are selected and evaluated on the same 20 answers, so the
  numbers are optimistic.

Interpretation: there is real ranking signal in token-level uncertainty, but
the next step must inspect false positives and false negatives before scaling.

The generated error review shows the two selected baselines make many false
positives on correct currency amounts and business-definition spans, while
false negatives concentrate on top-3 product ranking and currency spans. This
is the right diagnostic target before adding a new detector.

The error-family analysis makes this more specific:

- 32 baseline-error rows are correct numeric facts flagged as uncertain.
- 28 rows are correct context facts flagged as uncertain.
- 20 rows are confident wrong top-3 ranking or rank-bound amount errors.
- 12 rows are correct business-definition spans flagged as uncertain.

### Structured Top3 Pilot Behavior

The structured prompt variant changed only the answer contract for top3 product
questions. It required exactly one markdown table with `rank`, `stock_code`,
`product_name`, and `net_revenue_gbp`.

Observed result on `q_0060`, `q_0065`, and `q_0072`:

- 3/3 generated answers were valid markdown tables.
- 0/3 exact top3 lists matched gold.
- 0/9 rank-position stock codes matched gold.
- 9/9 generated stock codes came from the evidence table.
- 9/9 generated amounts copied the selected evidence row correctly.
- 0/3 generated tables were sorted by their own generated revenue values.

Interpretation: formatting constraints were effective, but ranking over shuffled
evidence rows was still not solved by Qwen3-0.6B. The failure is mainly selecting
and sorting the correct evidence rows, not inventing product names or amounts.

### Sorted-Evidence Top3 Control Behavior

The sorted-control variant uses the same three pilot questions but sorts the
evidence table by `net_revenue_gbp` descending. This is explicitly a diagnostic
control and should not be treated as a fair final benchmark condition.

Observed comparison:

- Shuffled structured condition: 0/3 exact top3 lists and 0/9 rank-position
  stock codes.
- Sorted-control condition: 2/3 exact top3 lists and 6/9 rank-position stock
  codes.
- Both conditions produced valid tables for 3/3 questions.
- Both conditions copied 9/9 generated amounts from the selected evidence rows.
- The only sorted-control failure was `q_0065`; the model skipped the first row
  `47566 PARTY BUNTING` and selected lower-revenue products.

Interpretation: sorted evidence sharply improves the answer, so the original
failure is largely sorting/row selection over shuffled evidence. The `q_0065`
miss shows that even answer-visible prompts are not perfectly reliable for this
small model.

### Sorted-Control Token Signal Behavior

The token-signal review converts the three sorted-control generated tables into
36 automatic generated spans:

- 24 correct spans from `q_0060` and `q_0072`.
- 12 incorrect rank-binding spans from `q_0065`.
- The omitted gold top product `47566 PARTY BUNTING` has no generated tokens, so
  token-level detectors cannot directly flag the missing span.

Using the selected pilot20 thresholds as a diagnostic reference:

- `q_0065` wrong stock-code spans: 3/3 flagged.
- `q_0065` wrong row-level spans: 3/3 flagged.
- `q_0065` wrong product-name spans: 0/3 flagged.
- `q_0065` wrong amount spans: 0/3 flagged.
- Correct stock-code spans in the two correct answers: 6/6 flagged.
- Correct row-level spans in the two correct answers: 6/6 flagged.

Interpretation: token uncertainty is high around stock-code choices, but this
small diagnostic does not distinguish wrong stock-code rank binding from correct
stock-code rank binding. This supports the broader pilot conclusion that simple
internal uncertainty is useful but too blunt for report-ready business fact
verification.

### Stock-Code Score Distribution Behavior

The stock-code distribution review narrows the analysis to 9 stock-code spans
from the sorted-control run:

- 6 correct stock-code spans from `q_0060` and `q_0072`.
- 3 incorrect rank-binding stock-code spans from `q_0065`.

Local ranking signal exists:

- Max token entropy pairwise AUC: 0.889.
- Mean token NLL pairwise AUC: 0.833.
- One-minus minimum top-2 margin pairwise AUC: 0.778.

But the signal is not clean:

- Entropy overlap: incorrect minimum 0.663322 vs correct maximum 0.736682.
- NLL overlap: incorrect minimum 0.071334 vs correct maximum 0.145057.
- Top-2 margin overlap: incorrect minimum 0.446481 vs correct maximum 0.757162.

Interpretation: there is a useful ranking signal in stock-code token scores,
but threshold-only scoring is too brittle. The next detector step should inspect
whether energy-style features add separation beyond entropy, NLL, and top-2
margin.

### Energy Trace Readiness Behavior

The energy-ready rerun uses the same three sorted-control questions and greedy
settings as the earlier sorted-control pilot:

- `q_0060`, `q_0065`, and `q_0072` generated the same answers as the previous
  sorted-control run.
- 359/359 generated token traces contain all required energy fields.
- Formula checks pass with maximum selected-gap vs negative-logprob difference
  of about `1.89e-6`.
- `spilled_energy_delta` and `spilled_energy_abs_delta` are internally
  consistent with `next_state_logsumexp_logits - token_logit`.

Interpretation: the project no longer needs another Qwen trace-format change
before implementing the Spilled Energy adapter. The next risk is detector
scoring and span aggregation, not trace capture.

### Full100 Config Readiness Behavior

The full100 config is a preparation artifact, not a generation result:

- It lists `q_0001` through `q_0100` in the same order as the gold question
  file.
- It validates against all prompt records and gold metadata.
- It preserves split counts: 64 train, 18 dev, and 18 test.
- It records the intended output prefix: `qwen_full100`.
- It requires the later validation command to use `--require-energy-fields`.

Interpretation: when full100 is eventually run, the command path is clear. The
remaining reason to wait is experimental design, not missing infrastructure.

### Pilot20 Energy Baseline Behavior

The pilot20 energy run is a retrace, not a generation rerun:

- Existing generated text and generated token ids are identical to
  `qwen_pilot20`.
- 20/20 traces pass `--require-energy-fields`.
- 135/135 annotated spans align with energy-ready token traces.
- 7 energy-style baselines are evaluated.

Best pilot results:

- Best simple AUPRC: 0.703 from `max_token_entropy`.
- Best simple F1: 0.691 from `one_minus_min_top2_margin`.
- Best energy-suite AUPRC: 0.674 from `max_selected_step_energy_gap`, which is
  effectively a max-token-NLL control.
- Best pure adjacent-step Spilled Energy AUPRC: 0.560 from
  `negative_mean_spilled_energy_delta`.
- Pure `mean_spilled_energy_abs_delta` AUPRC is 0.472.

Interpretation: the energy adapter is technically ready, but pure Spilled
Energy is not currently stronger than simple uncertainty on the pilot. This is
still useful for the final project because it supports the original motivation:
internal signals can be weak or blunt when the model generates fluent but wrong
business facts.

### Split-Safe Evaluation and Full100 Preflight Behavior

The split-safe evaluator is ready to consume the validated full100 score files:

- It joins score rows to question metadata to recover `train`, `dev`, and
  `test` split labels.
- It requires both dev and test rows.
- It requires both positive and negative spans in each evaluated split.
- It selects thresholds only on dev spans using max F1.
- It reports test metrics with the fixed dev threshold.

The smoke fixture confirms that the mechanics work. The train-only guard
confirms that pilot20 scores cannot be accidentally reported as held-out
dev/test metrics.

The full100 preflight aggregates the existing readiness checks and currently
reports:

- 100 configured full100 question ids.
- 64 train, 18 dev, and 18 test question splits.
- 5 simple detector score fields and 7 energy detector score fields.
- 0 failures across the readiness checks.
- `ready_for_current_stage=true`.
- `current_stage=github_pages_ready`.
- `ready_to_run_full100_generation=true` is now a legacy compatibility field,
  not the active project-stage label.
- `full100_generation_run=true`.
- `full100_review.ready=true`.
- `full100_annotation_queue.ready=true`.
- `full100_annotation_seed.ready=true`.
- `full100_annotation_draft.ready=true`.
- `full100_annotation_consistency_audit.ready=true`.
- `full100_span_token_alignment.ready=true`.
- `full100_detector_scores.ready=true`.
- `full100_simple_split_metrics.ready=true`.
- `full100_energy_split_metrics.ready=true`.
- `full100_detector_family_comparison.ready=true`.
- `full100_detector_error_review.ready=true`.
- `full100_detector_interpretation.ready=true`.
- `full100_label_confirmation_packet.ready=true`.
- `full100_label_confirmation_review_notes.ready=true`.
- `full100_label_lock.ready=true`.
- `portfolio_demo.ready=true`.
- `portfolio_narrative.ready=true`.

Interpretation: generation and review preparation are complete from an
infrastructure standpoint, and the current 35-question held-out draft confirms
the label schema and offset mechanics across multiple question types. The
consistency audit, span-token alignment, and score-file validation confirm the
input to split-safe metrics is ready. The simple and energy split-safe metric
passes, detector-family comparison, and detector error review are complete. The
detector interpretation write-up is also complete, and a focused confirmation
packet, review-note layer, label lock package, portfolio demo page, portfolio
narrative page, and GitHub Pages bundle are ready. The next work is upload
hygiene and optional slide creation, not more metric computation.

### Full100 Review Behavior

The full100 review artifacts are annotation-prep files, not detector results:

- `outputs/full100_review.csv` is the spreadsheet-friendly review table.
- `outputs/full100_review.jsonl` keeps nested gold/evidence fields intact.
- `outputs/full100_review_sample.csv` gives a quick 20-row preview.

Current auto triage is intentionally conservative:

- 9 rows are `likely_correct`.
- 91 rows are `partially_correct`.
- 39 rows have high annotation priority.
- 36 rows are held-out dev/test rows.

Interpretation: the generated answers contain enough likely business-fact
errors for span annotation. The auto triage should guide review order but must
not be treated as ground truth.

### Full100 Annotation Queue Behavior

The annotation queue is a logistics artifact, not a label file:

- `outputs/full100_annotation_queue.csv` orders all 100 review rows.
- `outputs/full100_heldout_high_annotation_batch.csv` contains the first
  recommended batch.
- The first batch has 35 rows: 17 dev and 18 test.
- It covers all seven question types.
- Each row includes an annotation-record template for
  `data/annotations/span_annotations_full100.jsonl`.

Interpretation: the next manual labeling work can start without re-filtering
the review table. The queue does not change the evaluation policy; thresholds
still must be selected only on dev spans and reported on held-out test spans.

### Full100 Annotation Seed Behavior

The seed annotation file is a draft label-policy and offset check:

- `data/annotations/span_annotations_full100_seed.jsonl` contains 18 spans.
- The 5 seed rows are `q_0004`, `q_0005`, `q_0009`, `q_0010`, and `q_0014`.
- Split coverage is 3 dev rows and 2 test rows.
- Labels include 5 `correct_key_fact` spans and 13
  `hallucinated_key_fact` spans.
- Fact types include month, country, currency amount, malformed number, and
  ranking.
- `outputs/full100_annotation_seed_validation.json` reports 0 failures.
- `outputs/full100_annotation_seed_policy_review.json` records the reviewed
  rules for repeated wrong entities, malformed amounts, explicit ranking claims,
  and vague explanatory prose.

Interpretation: the mechanics scaled to the full 35-row held-out high-priority
batch. The seed remains useful as the policy template, while the combined draft
still needs review before final evaluation.

### Full100 Annotation Draft Behavior

The current draft annotation file combines the reviewed seed with multi-type
round-1 through round-4 expansions:

- `data/annotations/span_annotations_full100_draft.jsonl` contains 205 spans.
- The draft covers all 35 held-out high-priority rows: 17 dev and 18 test.
- The round-1 through round-4 expansions add 30 rows with a 14 dev / 16 test
  split after the 5-row seed.
- Covered question types now include top country, top product, country
  comparison, monthly revenue change, top 3 products, product revenue share,
  and return impact.
- Labels include 83 `correct_key_fact` spans, 121 `hallucinated_key_fact`
  spans, and 1 `unsupported_claim` span.
- Fact types include month, country, product name, product stock code, currency
  amount, percentage, ranking, comparison direction, malformed number, and
  unsupported business claim.
- `outputs/full100_annotation_draft_validation.json` reports 0 failures.
- `outputs/full100_annotation_consistency_audit_report.json` reports 0 hard
  failures and `ready_for_alignment=true`.
- The audit-note review changed `q_0049` from `unsupported_claim` to
  `hallucinated_key_fact`, kept `q_0021` as `unsupported_claim`, and confirmed
  `q_0058` plus `q_0097` as correct-only omission cases.

Interpretation: the draft now stress-tests the annotation policy across the
major business-analysis error families, and its 205 spans have now been aligned
to token traces. It is still not a final evaluation label file until the review
notes are checked and detector scoring is complete.

### Full100 Draft Span-Token Alignment Behavior

The full100 draft alignment maps the reviewable span labels to the saved token
traces:

- `outputs/full100_draft_span_token_alignment.jsonl` contains 205 aligned
  spans.
- The aligned rows cover the same 35 held-out high-priority questions: 17 dev
  and 18 test.
- Validation confirms the alignment annotation ids exactly match the draft
  annotation ids.
- The split label and fact-type distributions match the consistency audit.
- Token count ranges from 1 to 14 tokens per span, with a mean of 7.0537.
- Boundary slop is at most 1 character on either side; this is expected when a
  token includes a leading space around a span.
- Simple and energy score fields are present for every aligned span.
- `metrics_reported=false`; this is a score-preparation artifact, not a final
  detector result.

Interpretation: the alignment is stable enough for score-file construction.
Public/report metrics should still be treated as draft until the reviewed
labels are confirmed for presentation.

### Full100 Detector Score-File Behavior

The full100 score-file step converts aligned spans into the wide detector input
format required by `evaluate_detector_split_metrics.py`:

- `results/full100_draft_detector_scores.csv` contains 205 score rows.
- `results/full100_draft_detector_scores_by_split.csv` summarizes 102 dev span
  rows and 103 test span rows.
- `results/full100_draft_detector_scores_report.json` records the 12 configured
  simple/energy score fields and keeps `metrics_reported=false`.
- `results/full100_draft_detector_scores_validation.json` reports 0 failures
  and `ready_for_split_safe_metrics=true`.
- Dev contains 61 positive and 41 negative span rows.
- Test contains 61 positive and 42 negative span rows.

Interpretation: the score-file schema is ready for split-safe evaluation. This
step deliberately did not select thresholds, report metrics, or create
confusion matrices.

### Full100 Simple Split-Safe Metric Behavior

The first full100 split-safe evaluation covers the simple detector family:

- `results/full100_draft_simple_split_metrics.csv` contains 10 rows: 5 simple
  baselines times dev/test.
- `results/full100_draft_simple_split_report.json` records dev-selected
  thresholds and held-out test summaries.
- `results/full100_draft_simple_split_validation.json` reports 0 failures.
- Exploratory maximum test AUPRC is 0.835 from
  `one_minus_min_top2_margin`.
- Exploratory maximum test F1 is 0.779 from `mean_token_entropy`; this is a
  different candidate signal.
- The highest-AUPRC simple baseline has test precision 0.854, recall 0.672,
  specificity 0.833, and accuracy 0.738.

Interpretation: simple internal uncertainty has usable held-out signal on this
draft full100 subset, but the best-F1 and best-AUPRC baselines differ. That is
a useful warning against overselling one thresholded detector before reviewing
error examples.

### Full100 Energy Split-Safe Metric Behavior

The second full100 split-safe evaluation covers the energy detector family:

- `results/full100_draft_energy_split_metrics.csv` contains 14 rows: 7 energy
  baselines times dev/test.
- `results/full100_draft_energy_split_report.json` records dev-selected
  thresholds and held-out test summaries.
- `results/full100_draft_energy_split_validation.json` reports 0 failures.
- Exploratory maximum energy-family test AUPRC is 0.830 from
  `max_selected_step_energy_gap`.
- Exploratory maximum energy-family test F1 is 0.773 from
  `mean_spilled_probability_mass_after_top2`.
- Pure adjacent-step energy delta/abs-delta rows are weak or degenerate under
  the dev-F1 threshold policy: 4 energy rows are flagged as all-positive-like.

Interpretation: the strongest energy-family rows are not the pure
adjacent-step Spilled Energy fields. They are either probability-mass controls
or a same-step selected-token energy gap that is effectively close to a max-NLL
control.

### Detector Family Comparison Behavior

The family comparison puts simple and energy test rows into one audit table:

- `results/full100_draft_detector_family_comparison.csv` contains 12 baseline
  rows.
- `results/full100_draft_detector_family_summary.csv` contains 2 family summary
  rows.
- `results/full100_draft_detector_family_comparison_report.json` records the
  overall best AUPRC/F1 rows and interpretation guardrails.
- `results/full100_draft_detector_family_comparison_validation.json` reports 0
  failures.
- Exploratory maximum test AUPRC is 0.835 from simple
  `one_minus_min_top2_margin`.
- Exploratory maximum test F1 is 0.779 from simple `mean_token_entropy`.
- Exploratory maximum energy-family test F1 is 0.773 from
  `mean_spilled_probability_mass_after_top2`.
- Energy best AUPRC is 0.004679 below simple best AUPRC.
- Energy best F1 is 0.006685 below simple best F1.

Interpretation: this is not a clean win for pure Spilled Energy. The result is
more precise: simple uncertainty remains best for both ranking by AUPRC and the
overall thresholded F1 row, while the strongest energy-family row is still a
probability-mass control rather than pure adjacent-step energy.

### Full100 Detector Error Review Behavior

The detector error review inspects held-out test false positives and false
negatives for the selected simple best-AUPRC baseline and energy best-F1
baseline:

- `results/full100_draft_detector_error_review.csv` contains 57 baseline-specific
  test error rows.
- `results/full100_draft_detector_error_review_by_baseline.csv` confirms simple
  `one_minus_min_top2_margin` has 7 false positives and 20 false negatives.
- The energy `mean_spilled_probability_mass_after_top2` row has 20 false
  positives and 10 false negatives.
- The largest simple false-negative group is currency amounts, with 9 misses.
- Top-3 product questions account for 6 simple false negatives and 6 energy
  false negatives.
- Energy false positives concentrate on currency amounts, months, country
  comparison, and monthly revenue change spans.
- `results/full100_draft_detector_error_review_examples.csv` contains 20
  representative examples for manual inspection.

During this review, three rank-3 marker annotations were found with the right
span text but wrong occurrence: `q_0063`, `q_0068`, and `q_0064` pointed to
`3.` inside a currency amount rather than the list marker. The builder now uses
the second occurrence for those markers, and all downstream alignment, score,
metric, family-comparison, error-review, and preflight artifacts were rerun.

Interpretation: the error review makes the detector story more credible because
it found and fixed a real annotation-offset defect, then showed the remaining
misses are substantive: top-3 rank/product/amount bindings can be confidently
wrong, while token uncertainty over-flags some correct numeric and context
facts.

### Full100 Detector Interpretation Behavior

The detector interpretation page packages the metric and error-review findings
for portfolio use:

- `reports/full100_detector_interpretation.html` is the presentation HTML draft.
- `reports/full100_detector_interpretation_summary.json` stores the same claims
  in a machine-checkable summary.
- `reports/full100_detector_interpretation_validation.json` reports 0 failures.
- The page is generated from the family-comparison and error-review outputs, so
  headline numbers are not manually retyped.
- The central claim is conservative: simple uncertainty currently gives the
  strongest held-out signal, the strongest energy-family result is a
  probability-mass control rather than pure adjacent-step Spilled Energy, and
  business-context errors still require stronger evidence-aware methods.

Interpretation: this is now ready for presentation-level label confirmation and
portfolio packaging. It is still not a final publication claim until labels are
locked.

### Full100 Label Confirmation Packet Behavior

The label confirmation packet narrows final review to the examples most likely
to appear in the portfolio/demo:

- `reports/full100_label_confirmation_packet.html` is the pre-lock review
  packet.
- `reports/full100_label_confirmation_packet.csv` and `.jsonl` store the same
  selected items in machine-readable form.
- The packet contains 15 selected spans across 9 held-out questions.
- It covers all 20 detector error-example rows after deduplicating repeated
  annotation ids.
- It also includes the 3 rank-marker offset regression checks:
  `q_0063`, `q_0068`, and `q_0064`.
- `reports/full100_label_confirmation_packet_validation.json` reports 0
  failures.
- This packet records the pre-lock queue; the final lock decision is stored in
  the label lock package.

Interpretation: the project keeps the review queue for traceability while using
the separate lock package as the current presentation state.

### Full100 Label Confirmation Review-Note Behavior

The assistant review-note layer records how the 15 selected confirmation items
should be used in a portfolio/demo:

- `reports/full100_label_confirmation_review_notes.html` is the assistant
  review-note page.
- `reports/full100_label_confirmation_review_notes.csv` and `.jsonl` store the
  same review notes in machine-readable form.
- All 15 selected labels are `label_supported` in this pass.
- `source_fix_required_count=0`.
- 7 items are high-priority portfolio examples, concentrated in `q_0064` and
  `q_0069`.
- 6 items are `span_level_caveat`; these are supported spans inside generated
  answers that also contain other business errors.
- These notes feed the label lock package.

Interpretation: the best public story is span-level detection. The review notes
make it explicit that a correct span does not make the whole answer correct.

### Full100 Label Lock Behavior

The label lock package converts the selected review notes into presentation
decisions:

- `reports/full100_label_lock_report.html` is the current lock report.
- `reports/full100_label_lock_decisions.csv` and `.jsonl` store one locked
  decision per selected span.
- `reports/full100_label_lock_validation.json` reports 0 failures.
- `labels_locked=true`.
- `lock_basis=assistant_full_review`.
- 15/15 selected spans are locked.
- 7 rows are `primary_demo`, 6 rows are `caveat_demo`, and 2 rows are
  `qa_regression_only`.
- `q_0064` and `q_0069` are the primary demo questions.

Interpretation: public-facing claims can now use the selected spans as locked
presentation examples while staying explicit that the task is span-level
detection, not whole-answer correctness.

### Portfolio Demo Behavior

The portfolio demo page packages the locked primary examples into a
public-facing artifact:

- `reports/bizhallu_portfolio_demo.html` is the static demo page.
- `reports/bizhallu_portfolio_demo_summary.json` stores demo claims and
  thresholds in machine-checkable form.
- `reports/bizhallu_portfolio_demo_validation.json` reports 0 failures.
- The page uses `q_0064` and `q_0069`.
- It covers 7 locked primary-demo spans.
- It validates span offsets against `outputs/full100_review.jsonl`, labels
  against the lock package, and detector outcomes against the score table.

Interpretation: the demo is now ready as the main portfolio artifact. It shows
the key business failure directly: Qwen can copy real values from evidence but
bind them to the wrong rank or product, while simple internal signals can still
miss those confident wrong spans.

### Portfolio Narrative Behavior

The portfolio narrative page turns the technical results into a polished
presentation story:

- `reports/bizhallu_portfolio_narrative.html` is the long-form narrative page.
- `reports/bizhallu_portfolio_narrative_summary.json` stores the source-backed
  narrative claims in machine-checkable form.
- `reports/bizhallu_portfolio_narrative_validation.json` reports 0 failures.
- It includes the core project story, method, split-safe results, primary demo
  cases, one-minute pitch, LinkedIn/portfolio blurb, resume bullets, slide
  outline, presentation guardrails, and next build steps.
- It keeps `q_0064` and `q_0069` as the primary examples and uses the same
  locked label basis, `assistant_full_review`.

Interpretation: this is now the source of truth for how to explain BizHallu in
portfolio, interview, networking, or class-presentation contexts.

### GitHub Pages Bundle Behavior

The GitHub Pages bundle turns the report pages into a public-facing web entry:

- `docs/index.html` is the recommended GitHub Pages landing page.
- `docs/portfolio_demo.html` and `docs/portfolio_narrative.html` are generated
  public copies of the report demo and narrative.
- `docs/detector_interpretation.html`, `docs/label_lock_report.html`, and
  `docs/label_confirmation_packet.html` keep supporting evidence one click
  away.
- `docs/github_pages_validation.json` verifies required files, HTML parsing,
  local links, stale report-relative links, expected metrics, and primary
  question ids.

Interpretation: this is now the best GitHub-facing surface. The `reports/`
copies remain experiment-native outputs, while `docs/` is the clean public
entry point for GitHub Pages.

## Issues Found and Fixed

1. Partial December wording was inconsistent.
   - Problem: some gold short answers said "December 2011" even when the
     question scoped data through December 9.
   - Fix: updated question generation and validation so partial December answers
     explicitly include "through December 9".

2. Prompt metadata could become stale if generation and prompt-building scripts
   were run in the wrong order.
   - Fix: prompt validation now checks `gold_short_answer` against the source
     question record.

3. Pilot review initially missed comparison-direction contradictions.
   - Fix: review builder now adds a separate comparison-direction check for
     country comparison questions.

4. Annotation guideline example had an incorrect prompt id and offset.
   - Fix: corrected the example and added validation that checks the example
     span against the actual generated text.

5. Project housekeeping was incomplete.
   - Fix: added `.gitignore`, expanded runtime requirements, and clarified
     README/project blueprint status.

6. Span-token alignment could fail if generated `token_text` contains
   replacement characters for symbols such as approximate signs.
   - Fix: alignment now uses token character offsets and validates every
     annotated span; all 135 pilot spans align with 0 failures.

7. Pilot F1 could look better than it is without a reference baseline.
   - Fix: the simple baseline report now includes all-positive and all-negative
     references plus lift over positive prevalence.

8. Energy-style baselines would have required rerunning if traces only stored
   entropy and top-2 margin.
   - Fix: trace generation now stores same-step logit/logsumexp fields and
     adjacent-step Spilled Energy fields; a 3-question readiness run validates
     359/359 token traces.

9. Full100 generation could accidentally run only the default 5-question smoke
   test if no question config is supplied.
   - Fix: added and validated `configs/full100_questions.json` plus a dedicated
     config validator.

10. The project had energy-ready traces for a 3-question top3 control but not
    for the annotated pilot20 set.
    - Fix: added a retrace path for saved generations and evaluated energy-style
      baselines on all 135 pilot spans.

11. The project had detector adapters but no enforced dev/test threshold policy.
    - Fix: added split-safe detector evaluation, a smoke fixture, a train-only
      guard, and a consolidated full100 preflight report.

12. Full100 raw generations were not directly convenient for annotation.
    - Fix: added full100 review CSV/JSONL artifacts with gold answers, gold
      facts, evidence rows, evidence tables, and validation.

13. Full100 review rows still needed a reproducible annotation order.
    - Fix: added a full100 annotation queue and a 35-row held-out high-priority
      initial batch.

14. Full100 span annotation needed a small offset/schema trial before scaling.
    - Fix: added a 5-question annotation seed, preview CSV, policy review, and
      validation report with 18 exact-offset spans and 0 failures.

15. Full100 annotation needed broader policy coverage beyond top-country rows.
    - Fix: added a 35-question held-out high-priority draft annotation file
      with 205 exact-offset spans across seven question types and 0 validation
      failures.

16. Full100 draft labels needed a consistency check before token alignment.
    - Fix: added `audit_full100_annotation_consistency.py`, corrected one
      mismatched `gold_reference.fact_type`, and produced by-question,
      by-split, and policy-flag audit outputs with 0 hard failures.

17. Full100 draft spans needed token coverage validation before scoring.
    - Fix: built full100 draft span-token alignment and added
      `validate_full100_span_token_alignment.py`, which checks annotation-id
      equality, token windows, split distributions, score fields, and boundary
      slop.

18. Audit-note review found one label that was too weak.
    - Fix: changed `q_0049` `24.5% difference` from `unsupported_claim` to
      `hallucinated_key_fact`, because the prompt evidence supplies both net
      revenue values and the percentage is contradicted by deterministic
      calculation. Added `review_full100_audit_notes.py` to record all four
      review decisions.

19. Full100 metrics needed a clean input boundary before evaluation.
    - Fix: added `build_full100_detector_score_files.py` and
      `validate_full100_detector_score_files.py`, producing 205 score rows with
      12 configured simple/energy fields and confirming both dev and test have
      positive and negative spans. The validation also confirms no full100
      metric files were produced in this step.

20. The first full100 metrics needed to enforce the dev/test threshold policy.
    - Fix: ran `evaluate_detector_split_metrics.py` only for the simple family
      and validated the 10 metric rows with `validate_detector_split_metrics.py`.
      The report confirms thresholds come from dev and are reused on test.

21. Energy metrics needed the same split-safe policy plus family-level
    interpretation guards.
    - Fix: ran the energy family through the same split evaluator and validated
      14 metric rows. Added `build_full100_detector_family_comparison.py` and
      `validate_full100_detector_family_comparison.py` to compare 12 baselines
      and flag all-positive-like energy thresholds.

22. Three full100 rank-marker spans had correct text but wrong occurrence.
    - Problem: `q_0063`, `q_0068`, and `q_0064` rank-3 annotations matched
      `3.` inside a currency amount instead of the list marker.
    - Fix: updated `build_full100_annotation_draft.py` with explicit second
      occurrence selection for those markers, then reran annotation validation,
      alignment, score files, split metrics, family comparison, error review,
      and preflight.

23. Full100 detector metrics needed error-pattern inspection before reporting.
    - Fix: added `build_full100_detector_error_review.py` and
      `validate_full100_detector_error_review.py`, producing held-out test
      FP/FN tables by baseline, fact type, question type, and representative
      examples.

24. Detector results needed a presentation interpretation artifact.
    - Fix: added `build_full100_detector_interpretation.py` and
      `validate_full100_detector_interpretation.py`, producing a report-ready
      HTML draft and a machine-checkable summary from the source result files.

25. Presentation-level confirmation needed a focused review queue.
    - Fix: added `build_full100_label_confirmation_packet.py` and
      `validate_full100_label_confirmation_packet.py`, selecting 15 high-impact
      spans that cover all detector error examples plus the offset regression
      checks as the pre-lock review queue.

26. Presentation examples needed review notes before portfolio packaging.
    - Fix: added `build_full100_label_confirmation_review_notes.py` and
      `validate_full100_label_confirmation_review_notes.py`, confirming 15/15
      selected labels as supported in this assistant pass, flagging 6
      span-level caveats, and recommending 0 source annotation edits.

27. Presentation labels needed a lock package before final demo construction.
    - Fix: added `build_full100_label_lock_package.py` and
      `validate_full100_label_lock_package.py`, locking 15/15 selected spans
      with `lock_basis=assistant_full_review`, identifying 7 primary demo rows,
      6 caveat rows, and 2 QA regression rows.

28. Locked labels needed a portfolio/demo surface.
    - Fix: added `build_portfolio_demo.py` and `validate_portfolio_demo.py`,
      producing a static demo around `q_0064` and `q_0069` with 7 locked
      primary spans and source-backed detector readouts.

29. The demo needed a full portfolio narrative.
    - Fix: added `build_portfolio_narrative.py` and
      `validate_portfolio_narrative.py`, producing a source-backed narrative
      page with project story, results, pitch, resume bullets, slide outline,
      and presentation guardrails.

30. The portfolio pages needed a GitHub Pages-safe public bundle.
    - Fix: added `build_github_pages_bundle.py` and
      `validate_github_pages_bundle.py`, copying the validated pages into
      `docs/`, rewriting report-relative links, copying the detector error
      examples CSV, and advancing preflight to `github_pages_ready`.

31. The public repo needed final polish for recruiter and professor review.
    - Fix: strengthened the README first screen with a TL;DR, role statement,
      5-minute review path, and reproducibility levels.
    - Fix: added `AGENTS.md` so future agent edits preserve metrics, label
      wording, public path hygiene, and claim guardrails.

32. Public JSON paths needed a durable hygiene rule.
    - Fix: added `public_paths.py` and `validate_public_path_hygiene.py`, then
      updated public build/validation scripts so generated summaries and
      manifests use repo-relative paths instead of local Windows absolute
      paths.

33. Professor-facing packaging needed a concise research artifact.
    - Fix: added `build_research_one_pager.py` and
      `validate_research_one_pager.py`, then included `research_one_pager.html`
      in the GitHub Pages bundle.

34. Public artifact validation needed to run on GitHub.
    - Fix: added `.github/workflows/validate.yml` as a lightweight CI
      workflow that validates committed public artifacts without rerunning Qwen
      or depending on local-only token traces.

35. The next research direction needed a small, reviewable implementation path.
    - Fix: added a claim-evidence review schema over the 9 Demo v2 cases and 15
      selected presentation spans. Its statuses are label-derived and prepare
      a future independent comparison; they are not verifier predictions.

36. Confirmation Set v1 needed an official-source dataset decision before any
    new prompt or generation file could be created.
    - Fix: added `confirmation_dataset_source_audit_v1.json`, a generated HTML
      report, a machine-checkable summary, and a dedicated validator.
    - Decision: provisionally select UCI Online Retail II only within the strict
      `2009-12-01` inclusive to `2010-12-01` exclusive window for a temporal
      internal replication.
    - Initial boundary: source acquisition and local profiling were deferred to a
      separate gated step; no context, question, generation, annotation,
      detector, or confirmation result was created in the desk audit.
    - Academic path: retain Complete Journey as the preferred external
      replication shortlist candidate, with Olist and NYC TLC serving different
      relational-ecommerce and operations-transfer roles rather than being
      treated as equivalent datasets.

37. The provisional source needed immutable local acquisition and structure
    evidence before any analytical profile could be trusted.
    - Fix: downloaded the official UCI ZIP into the Git-ignored raw-data tree,
      validated its CRC and unique XLSX member, and recorded both SHA-256 hashes.
    - Reconciliation: the workbook has two sheets and exactly 1,067,371 data
      rows, matching UCI's documented instance count with a delta of zero.
    - Schema finding: actual headers require three deterministic aliases:
      `Invoice -> InvoiceNo`, `Price -> UnitPrice`, and
      `Customer ID -> CustomerID`.
    - Date finding: the complete date scan has zero blank or invalid dates. The
      strict `2009-12-01` inclusive to `2010-12-01` exclusive window retains
      502,938 rows and ends at `2010-11-30 19:35:00`.
    - Boundary at that checkpoint: full missingness, duplicate/grain,
      cancellation, monthly coverage, historical overlap, and context-feasibility
      checks remained pending. The dataset gate and all six downstream execution
      gates remained open.

38. The verified strict window needed a complete data-quality profile before any
    independence or context work could be trusted.
    - Completeness: all core transaction fields are complete; 2,821 descriptions
      and 100,207 customer IDs are missing. Customer-level questions remain
      blocked, and auditable product/value evidence requires a description.
    - Grain: 6,544 normalized exact duplicate extra rows are controlled through
      exact-row deduplication. `InvoiceNo + StockCode` is not treated as unique.
    - Cancellation: 11,933 rows have negative quantity, including 2,057 without
      the `C` invoice prefix. Net-revenue rules therefore retain negative
      quantities and do not rely on prefix alone.
    - Reconciliation: 492,887 valid net-revenue lines reconcile to GBP
      9,266,060.76, and all 12 expected months are present.
    - Boundary: the public report contains aggregates only; the 23-column local
      line table remains Git-ignored. Historical overlap and 36-context
      feasibility are still pending, so all seven execution gates remain open.

39. The strict prior window needed an explicit record-level comparison before
    any context construction could begin.
    - Canonical proof: all eight normalized business fields produced 0 shared
      unique fingerprints and 0 multiplicity-aware overlap rows.
    - Sensitivity proof: removing `invoice_date` still produced 0 shared records.
    - Calibration: all 541,909 current rows were recovered from the Online Retail
      II 2010-2011 sheet, which has one additional row.
    - Continuity disclosure: 195,814 five-field business-pattern rows overlap;
      this is expected same-retailer similarity, not record leakage.
    - Boundary: no context, question, prompt, Qwen output, annotation, detector,
      or new metric was created. Context feasibility remains the only unfinished
      source-data blocker.

40. The source then needed an outcome-blind capacity proof at the complete-week
    evidence-context grain.
    - The first planning target proved 36/36 matching with 14 unused complete
      weeks, but retained no matching assignment, period list, or split.
    - After the precision-review failure path increased the study to 48 total
      contexts, the same frozen family rules were rerun. All three allowed
      families had 50 eligible complete weeks, maximum matching filled 48/48
      slots, and generalized Hall capacity had minimum slack 2.
    - Customer concentration remained blocked because 100,207 Customer IDs are
      missing; it was not rescued with a post hoc complete-case denominator.

41. The planned detector comparison needed a precision review before any
    context manifest could be frozen.
    - A deterministic synthetic simulation tested 15, 21, 24, and 27
      confirmation-context candidates under fixed central and stress scenarios.
    - No candidate passed all frozen strong-comparison rules. An alternate-seed
      sensitivity check agreed on the failure direction, and the primary frozen
      simulation artifact was not replaced.
    - The decision thresholds were preserved. The project instead froze an
      estimation-focused scope, selected the largest balanced capacity-feasible
      plan of 6/15/27 contexts, and prohibited detector-superiority claims from
      Confirmation Set v1.
    - Boundary: the review used no confirmation outcomes and created no context
      manifest, questions, prompts, generated answers, annotations, detector
      scores, or empirical performance metrics.

## Remaining Risks

1. Current review auto-status is only a triage aid.
   - It should not be treated as ground-truth correctness.
   - Manual span annotation is now complete for pilot20, but full-scale labels
     should still be checked against gold answers rather than auto-status.

2. Some generated answers contain correct facts and contradicted facts in the
   same sentence.
   - Pilot guidelines now label each separable direction against the gold
     answer. The remaining risk is maintaining that consistency when scaling
     beyond pilot20.

3. Current token traces support simple uncertainty baselines and Spilled Energy
   style scoring, but not hidden-state probes.
   - Hidden-state extraction still needs to be added before a probe baseline.

4. Full100 generation is complete, but the output is not automatically a final
   benchmark.
   - The recurring patterns are summarized, and the top3 prompt controls show
     that table formatting alone does not fix rank-product-amount binding.
   - The token-signal review shows that simple uncertainty also needs stronger
     context-aware scoring before scaling claims.
   - The energy baselines are operational, but the full100 comparison shows the
     strongest energy-family result is a probability-mass control, not pure
     adjacent-step Spilled Energy.
   - The selected presentation labels are now locked, and the GitHub Pages
     bundle is ready, but claims should remain span-level and should not imply
     whole-answer correctness.

5. Claim-Evidence Review Schema v0 is intentionally small.
   - It covers only selected Demo v2 spans and derives statuses from existing
     presentation labels.
   - It is a protocol scaffold, not an independent production checker, a new
     benchmark result, or evidence that a verifier outperforms uncertainty.

6. Current pilot metrics are not held-out results.
    - The full100 evaluator correctly freezes each signal threshold on dev, but
      the 35-question annotation subset is outcome-informed, evidence contexts
      cross splits, and headline signals were chosen after test comparison.
    - Treat 0.835 AUPRC and 0.779 F1 as reproducible exploratory maxima, not as
      representative or confirmatory performance estimates.

7. A clean confirmation result does not exist yet.
   - The next result needs fresh or context-separated evidence, annotation
     targets selected before answer-quality review, independent human labeling,
     frozen detector decisions, and separate claim-extraction evaluation.
   - Online Retail II is selected for an internal temporal replication.
     Acquisition, hashes, structure, strict-window quality controls, monthly
     reconciliation, zero-overlap checks, outcome-blind precision review, and
     revised 48-context capacity proof are complete.
   - Statistical precision remains limited by the number of independent
     contexts. The study is estimation-focused; paired and subgroup contrasts
     are descriptive, and a stronger comparative claim requires more contexts
     or a separately audited second dataset.
   - The 6/15/27 context manifest and split are now frozen, but question
     templates, gold calculations, prompt/model configuration, independent
     reviewers, non-confirmation detector implementations, and sealed-run
     authorization remain incomplete.

## Recommended Next Steps

1. Keep the public GitHub Pages bundle as the source of truth.
   - Use `docs/index.html` as the public entry point.
   - Use `docs/portfolio_demo_v2.html` as the recruiter/interviewer demo.
   - Use `docs/career_package.html` for interview wording, resume bullets, and
     public positioning.
   - Use `docs/business_risk_lens.html` to connect the project to accounting,
     supply management, and BA / DS / AI Analyst roles.
   - Use `docs/research_one_pager.html` for professor, capstone, and research
     advisor outreach.
    - Use `docs/methodology_hardening.html` to disclose current evidence strength
      and the future confirmation protocol.
    - Use `docs/confirmation_dataset_overlap.html` to show aggregate-only
      historical record separation and its same-retailer limitation.
    - Use `docs/confirmation_context_manifest.html` to show the outcome-blind
      48-context freeze, 6/15/27 split, privacy boundary, and public commitment.
   - Use `docs/evidence_verifier_pilot.html` to show the claim-evidence review
     schema without claiming independent verifier predictions or new metrics.
   - Keep `docs/portfolio_demo.html`, `docs/portfolio_narrative.html`, and
     `docs/detector_interpretation.html` as deeper technical references.

2. Preserve claim guardrails.
   - Say span-level business-fact evaluation, not whole-answer correctness.
   - Say 205 AI-assisted provisional labels and 15 additionally
     assistant-reviewed presentation spans, not a human-labeled benchmark.
   - Say diagnostic detector baselines, not production-ready hallucination
     detection.
   - Say simple uncertainty is strongest in this run; do not imply the
     energy-family methods won overall.

3. Treat Confirmation Set v1 as the next research branch, but advance only one
   gate at a time.
   - Preserve the recorded official-file hashes and keep the workbook and local
     validation record under the Git-ignored raw-data tree.
   - Preserve the completed strict-window controls: three header aliases,
     exact-row deduplication, description-required product/value evidence,
     customer-level question blocking, and cancellation-aware net revenue.
   - Preserve the completed overlap proof: zero canonical and date-blind record
     overlap, with same-retailer entity and business-pattern continuity disclosed.
   - Preserve the completed precision result: no tested candidate passed every
     frozen strong-comparison rule, thresholds were not relaxed, and the study
     now estimates detector-family performance rather than claiming superiority.
   - Preserve the frozen private 6/15/27 manifest and its public SHA-256
     commitment. Do not expose selected periods, context IDs, or scope entities
     in public artifacts, and do not substitute the two reserve weeks after
     outcome access.
   - Preserve the frozen private 96-question/gold manifest and its separate
     public commitment. Do not expose question IDs, text, gold values, selected
     entities, evidence rows, or payload fingerprints.
   - Next, freeze exact model and tokenizer revisions, prompt templates, decoding
     settings, detector-family inclusion decisions, and metric implementations.
     This is a configuration gate only; do not run Qwen yet.
   - Keep the 12/30/54 question counts and 96-generation total fixed unless a
     new, separately justified design amendment is made before model outcomes.
   - Treat the current claim-evidence schema as label-derived v0 scaffolding;
     implement an independent decision protocol only on pilot/development data.
   - Keep internal-state and literature-grounded methods as comparison tracks:
     entropy, top-2 margin, energy-style signals, Semantic Entropy, TOHA, and
     entity-level hallucination detection.
   - Do not inspect sealed confirmation labels, tune on confirmation data, or
     promote a pilot result into a new headline metric.
