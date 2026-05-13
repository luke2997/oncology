# How to Walk Through This Portfolio in an Interview

## 60-second summary
I built a full simulated Phase III oncology statistical submission portfolio. It starts from a protocol/SAP concept, generates synthetic patient-level trial data, builds ADaM-style analysis datasets, produces efficacy and safety TLFs, creates listings and figures, and runs validation checks. The code is reproducible end-to-end.

## What to show first
1. `outputs/reports/tlf_packet.pdf` - shows the deliverable quality.
2. `outputs/reports/validation_report.pdf` - shows QC mindset.
3. `data/adam/adsl.csv`, `adtte.csv`, `adae.csv` - shows ADaM-style data thinking.
4. `programs/python/generate_tlfs.py` - shows statistical methods and table generation.
5. `programs/sas/` - shows how outputs map to SAS clinical programming.

## What each component demonstrates
- Protocol/SAP: endpoint definition, populations, censoring, estimands, safety strategy.
- ADTTE: PFS/OS analysis variables, event/censoring flags, analysis flags.
- ADAE: TEAE flags, SOC/PT summaries, toxicity grades, seriousness, relationship, discontinuation.
- TLFs: production-style tables with denominators, n (%), survival medians, HRs, p-values.
- QC: subject uniqueness, endpoint record counts, valid censoring, valid AE grades, date chronology, output completeness.

## Recruiter angle
This project is deliberately practical: it is not a toy model or notebook. It demonstrates the workflow recruiters expect in clinical statistics/statistical programming - from data to analysis datasets, TLFs, validation, and documentation.
