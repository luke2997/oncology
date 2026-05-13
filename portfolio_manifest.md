# Portfolio Manifest

## Repository contents

- `programs/python/`: executable end-to-end pipeline.
- `programs/sas/`: SAS templates for PFS, safety, and validation/QC workflows.
- `programs/r/`: R templates for survival and safety outputs.
- `data/raw/`: simulated source datasets.
- `data/adam/`: ADaM-style analysis datasets.
- `data/specs/`: ADaM specification CSV and define-like XML metadata.
- `outputs/tables/`: TLF table outputs in CSV, Markdown, and TXT.
- `outputs/listings/`: listing outputs in CSV, Markdown, and TXT.
- `outputs/figures/`: Kaplan-Meier, forest, waterfall, and TEAE figures.
- `outputs/reports/`: TLF packet, clinical analysis report, and validation report PDFs.
- `docs/`: protocol synopsis, SAP, recruiter summary, and interview walkthrough.
- `qc/`: validation checks and QC report markdown.

## Regeneration command

```bash
python programs/python/run_all.py
```

## Validation status

The included validation report shows 28 PASS, 0 WARN, 0 FAIL.
