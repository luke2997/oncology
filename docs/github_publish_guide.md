# How to put this portfolio on GitHub

## 1. Create a clean repository

```bash
git init
python programs/python/run_all.py
git status
```

Keep the generated PDFs and key CSV outputs in the repo because recruiters should be able to inspect the project without running the code first.

## 2. Commit the full portfolio

```bash
git add README.md DISCLAIMER.md Makefile requirements.txt .gitignore
git add programs data docs metadata outputs qc
git commit -m "Add simulated Phase III oncology statistical submission portfolio"
```

## 3. Create a GitHub repo

Create a new public repository named something like:

```text
phase3-oncology-biostatistics-portfolio
```

Then push:

```bash
git branch -M main
git remote add origin https://github.com/<your-username>/phase3-oncology-biostatistics-portfolio.git
git push -u origin main
```

## 4. Add repository topics

Use topics such as:

```text
biostatistics, clinical-trials, oncology, survival-analysis, adam, cdisc, sas, r, python, statistical-programming, clinical-research, tlf, kaplan-meier, cox-regression
```

## 5. Pin the repository

Pin it on your GitHub profile and add a short description:

> Simulated Phase III oncology statistical-submission portfolio with SAP, ADaM-style datasets, survival/safety TLFs, validation report and Python/SAS/R workflow.

## 6. Add screenshots to README

Add images from:

- `outputs/figures/f14_2_1_km_pfs.png`
- `outputs/figures/f14_2_3_pfs_forest.png`
- `outputs/figures/f14_3_1_top_teae_bar.png`

Suggested README snippet:

```markdown
## Example outputs

![PFS Kaplan-Meier](outputs/figures/f14_2_1_km_pfs.png)
![PFS subgroup forest plot](outputs/figures/f14_2_3_pfs_forest.png)
![Top TEAEs](outputs/figures/f14_3_1_top_teae_bar.png)
```

## 7. Optional GitHub Actions

The included `.github/workflows/run-portfolio.yml` can regenerate the portfolio on each push. This is useful because it proves reproducibility.
