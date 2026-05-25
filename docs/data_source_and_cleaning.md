# Data Source and Cleaning Notes

## Source

Dataset: UCI Machine Learning Repository, Online Retail.

Citation: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33

Official page: https://archive.ics.uci.edu/dataset/352/online+retail

The dataset is a UK-based non-store online retail transaction dataset covering 2010-12-01 through 2011-12-09. It contains invoice, product, quantity, invoice timestamp, unit price, customer, and country fields.

## Why This Dataset Fits BizHallu

This dataset is suitable for the first hallucination-detection benchmark because it supports deterministic business questions:

- revenue by month, country, product, and invoice
- top-k product and country rankings
- country-to-country comparisons
- month-over-month change
- cancellation and return handling
- product vs non-product charge distinctions

These facts can be computed exactly from the source data, so model outputs can be audited against reproducible gold answers.

## Cleaning Policy

The raw file is kept unchanged in `data/raw/`.

The script `src/clean_online_retail.py` creates separate processed files:

- `retail_lines_normalized.csv`: all raw rows with normalized columns and quality flags
- `retail_sales_lines.csv`: positive, non-cancelled sales lines for gross sales analysis
- `retail_merchandise_sales_lines.csv`: positive gross sales excluding service/charge stock codes
- `retail_net_revenue_lines.csv`: valid revenue lines including negative cancellation/return rows
- `retail_merchandise_net_revenue_lines.csv`: valid merchandise revenue lines including cancellations/returns
- `retail_cancellation_lines.csv`: cancellation or negative-quantity rows for future return-analysis questions
- `retail_excluded_lines.csv`: rows excluded from positive sales, with exclusion reasons
- `monthly_coverage_summary.csv`: month-level coverage and recommended trend-question periods
- summary tables for month, country, and product analysis

Positive sales exclude exact duplicate rows, cancellation invoices, negative quantities, nonpositive unit prices, and missing descriptions.

Net revenue lines exclude exact duplicates, nonpositive unit prices, and missing descriptions, but they keep negative quantities and cancellation invoices so that cancellations/returns reduce revenue.

Merchandise sales additionally exclude non-product stock codes such as postage, discounts, manual adjustments, bank charges, Amazon fees, samples, and no-digit stock codes.

For BizHallu question generation, default to the `*_net_revenue_summary.csv` files when the question says "net revenue." Use `*_sales_summary.csv` only when the question explicitly says "gross positive sales."

One expected consequence: total merchandise net revenue can be higher than total net revenue because merchandise tables exclude negative non-product charges such as discounts or adjustments. Use country/month net revenue for company-level revenue questions and merchandise net revenue only for product-ranking questions.

## Question-Generation Policy

Use `net revenue` as the default revenue metric.

For month-over-month or trend questions, use 2011-01 through 2011-11. The dataset ends on 2011-12-09, so 2011-12 should not be treated as a complete month. It can still be used in questions only if the prompt explicitly says "through 2011-12-09" or "partial December 2011."

Country-month groups can have negative net revenue when cancellations exceed positive sales. This is valid, but early MVP questions should avoid tiny or negative country-month groups unless the goal is specifically to test return/cancellation reasoning.

## Validation

Run:

```powershell
python src/validate_processed_data.py
```

The validation script independently checks raw row counts, sales filters, revenue calculations, and whether monthly/country/product summaries reconcile to the underlying line-level tables.

## Known Data Issues

The UCI page lists missing values as "No", but the downloaded Excel file contains missing `CustomerID` and `Description` values. This is not a blocker for BizHallu because the MVP does not rely on customer identity. Missing descriptions are excluded from positive/product sales where product labels are needed.
