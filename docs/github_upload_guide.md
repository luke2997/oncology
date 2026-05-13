# How to put this portfolio on GitHub

## 1. Choose a strong repository name

Recommended name: `phase3-oncology-statistical-submission-portfolio`

Good alternatives:

- `oncology-biostatistics-submission-portfolio`
- `clinical-trial-stats-programming-portfolio`
- `phase3-oncology-adam-tlf-portfolio`

## 2. Create the GitHub repo

On GitHub, create a new public repository with the name above. Do not initialize with another README because this folder already contains one.

## 3. Upload from your computer using Git

From the folder that contains this project:

```bash
cd oncology_stat_submission_portfolio
git init
git add .
git commit -m "Initial Phase III oncology statistical submission portfolio"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/phase3-oncology-statistical-submission-portfolio.git
git push -u origin main
```

## 4. Add repository topics

Add these GitHub topics:

`biostatistics`, `clinical-trials`, `oncology`, `survival-analysis`, `adam`, `cdisc`, `tlf`, `statistical-programming`, `pharma`, `python`, `sas`, `r`, `kaplan-meier`, `cox-regression`

## 5. Pin the repo on your GitHub profile

Pin this repository near the top of your profile. Recruiters should see it before general teaching or unrelated projects.

## 6. Add a release

Create a release called:

`v1.0-professional-portfolio`

Release description:

> End-to-end simulated Phase III oncology statistical submission portfolio with SAP, CSR-style report, ADaM-style datasets, TLFs, validation report, reviewer guide, traceability metadata and reproducible Python/SAS/R programming structure.

## 7. What to highlight in interviews

Say:

> I built this to demonstrate the full pharma biostatistics workflow: protocol question -> SAP -> estimand -> ADaM derivations -> PFS/OS/ORR/safety TLFs -> validation -> CSR-style reporting. It uses simulated data only, but the structure mirrors the documents and outputs expected in regulated clinical trial work.

## 8. What not to overclaim

- Do not say this is a real trial.
- Do not say this is a regulatory submission.
- Do not say the SAS templates were executed unless you run them locally.
- Do not claim CDISC compliance certification; say "ADaM-style" and "define-like metadata" unless you later add formal Pinnacle 21 validation.

## 9. Optional next upgrades

- Export ADaM datasets to XPT using the optional R script.
- Add formal Pinnacle 21 Community validation screenshots if available.
- Add a short Loom/YouTube walkthrough.
- Add a Streamlit dashboard only if applying to clinical data science roles; for pure biostatistics, keep the repo document-focused.
