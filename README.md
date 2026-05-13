# Simulated Phase III Oncology Statistical Submission Portfolio

**Study:** ONC-305-301, a simulated randomized Phase III oncology study comparing `ONC-305 + SOC` with `Placebo + SOC` in advanced solid tumors.

This repository is an end-to-end biostatistics/statistical-programming portfolio. It uses **synthetic data only** and is designed to demonstrate the workflow a pharma/CRO biostatistician or statistical programmer would be expected to understand: protocol question -> SAP -> estimand -> ADaM-style datasets -> TLFs -> validation -> CSR-style reporting.

## Why this project stands out

- Professional Statistical Analysis Plan with endpoints, estimand, censoring rules, analysis populations, multiplicity and sensitivity analyses.
- CSR-style Clinical Study Analysis Report with efficacy, safety, protocol-deviation, data-review and validation sections.
- ADaM-style datasets: `ADSL`, `ADTTE`, `ADAE`, `ADRS`, `ADLB`.
- Oncology outputs: PFS, OS, ORR, DCR, exposure, disposition, TEAEs, SAEs, grade >=3 AEs, AE discontinuations, fatal AEs and laboratory shifts.
- Kaplan-Meier, log-rank and Cox model outputs, plus subgroup forest plot and response waterfall plot.
- Reviewer-facing artifacts: ADaM Reviewer Guide, TLF Shell Book, Programming/QC Plan, Blinded Data Review Memo, analysis-results metadata and source-to-ADaM traceability.
- Reproducible Python pipeline with SAS and R templates for regulated-workflow discussion.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run_all.sh
# or: python programs/python/run_all.py
```

## Key reports

- `docs/statistical_analysis_plan.pdf`
- `docs/protocol_synopsis.pdf`
- `outputs/reports/clinical_study_analysis_report.pdf`
- `outputs/reports/tlf_packet.pdf`
- `outputs/reports/validation_report.pdf`
- `outputs/reports/adam_reviewer_guide.pdf`
- `outputs/reports/programming_qc_plan.pdf`
- `outputs/reports/tlf_shell_book.pdf`
- `outputs/reports/recruiter_portfolio_summary.pdf`
- `outputs/reports/blinded_data_review_memo.pdf`

## Data and metadata

- `data/raw/` - synthetic source data.
- `data/adam/` - ADaM-style analysis datasets.
- `data/specs/adam_spec.csv` - dataset/variable metadata.
- `data/specs/define_like_metadata.xml` - define-like XML metadata.
- `metadata/analysis_results_metadata.csv` - result-level traceability.
- `metadata/source_to_adam_traceability.csv` - source-to-analysis variable traceability.
- `qc/validation_checks.csv` - automated validation checks.
- `qc/program_validation_tracker.csv` - programming/QC tracker.
- `qc/data_review_issue_log.csv` - mock data-review log.


## Important disclaimer

All data are synthetic. This is not a real clinical trial, not a regulatory submission, not clinical evidence and not endorsed by any sponsor, regulator or standards organization. The repository is a portfolio demonstration of biostatistics and statistical-programming competence.

## GitHub setup guide

See `docs/github_upload_guide.md`.
