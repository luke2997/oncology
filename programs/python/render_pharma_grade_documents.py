from __future__ import annotations

import pandas as pd
from pathlib import Path
from reportlab.lib.units import inch
from reportlab.platypus import Spacer, PageBreak, Image

from utils import ROOT, DOCS, OUT_REPORTS, OUT_TABLES, OUT_FIGURES, QC, DATA_ADAM, ARM_T, ARM_C, STUDY_ID
from render_professional_package import (
    p, bullets, table, df_table, pdf, title_block, make_protocol_deviation_table,
    DATA_CUTOFF, DBL_DATE, SAP_VERSION, REPORT_VERSION
)


def _load():
    return {
        "adsl": pd.read_csv(DATA_ADAM / "adsl.csv"),
        "adtte": pd.read_csv(DATA_ADAM / "adtte.csv"),
        "adae": pd.read_csv(DATA_ADAM / "adae.csv"),
        "adrs": pd.read_csv(DATA_ADAM / "adrs.csv"),
        "adlb": pd.read_csv(DATA_ADAM / "adlb.csv"),
        "pfs": pd.read_csv(OUT_TABLES / "t14_2_1_primary_pfs.csv", keep_default_na=False),
        "os": pd.read_csv(OUT_TABLES / "t14_2_2_overall_survival.csv", keep_default_na=False),
        "orr": pd.read_csv(OUT_TABLES / "t14_2_3_best_overall_response.csv", keep_default_na=False),
        "safety": pd.read_csv(OUT_TABLES / "t14_3_1_safety_overview.csv", keep_default_na=False),
        "demo": pd.read_csv(OUT_TABLES / "t14_1_1_demographics.csv", keep_default_na=False),
        "disp": pd.read_csv(OUT_TABLES / "t14_1_2_disposition.csv", keep_default_na=False),
        "expo": pd.read_csv(OUT_TABLES / "t14_1_3_exposure.csv", keep_default_na=False),
        "pdev": pd.read_csv(OUT_TABLES / "t14_1_4_major_protocol_deviations.csv", keep_default_na=False),
        "qc": pd.read_csv(QC / "validation_checks.csv", keep_default_na=False),
    }


def _hr(table_df: pd.DataFrame):
    return table_df.loc[table_df.iloc[:, 0] == "Cox HR, treatment vs control", table_df.columns[3]].iloc[0]


def _pval(table_df: pd.DataFrame):
    return table_df.loc[table_df.iloc[:, 0] == "Log-rank test p-value", table_df.columns[3]].iloc[0]


def pharma_grade_sap() -> None:
    d = _load()
    adsl = d["adsl"]
    n_t = int((adsl.TRT01P == ARM_T).sum())
    n_c = int((adsl.TRT01P == ARM_C).sum())
    story = title_block("Statistical Analysis Plan", "Pharma-style simulated version with estimands, TLF traceability and QC plan", SAP_VERSION)

    # Document administration
    story += [p("Document administration", "H1")]
    version_history = [
        ["Version", "Date", "Author", "Description"],
        ["1.0", "2026-02-01", "Luke Johnston", "Initial simulated SAP with endpoint and population definitions"],
        ["2.0", "2026-02-15", "Luke Johnston", "Professional version adding estimand, censoring, sensitivity, TLF traceability and QC sections"],
    ]
    story.append(table(version_history, widths=[0.8*inch, 1.1*inch, 1.5*inch, 3.2*inch], font_size=7.3))
    story.append(Spacer(1, 6))
    approvals = [
        ["Role", "Name", "Signature", "Date"],
        ["Study Statistician", "Luke Johnston", "________________", "________"],
        ["Statistical Programming Lead", "Portfolio demonstration", "________________", "________"],
        ["Clinical Lead", "Simulated", "________________", "________"],
        ["Data Management Lead", "Simulated", "________________", "________"],
    ]
    story.append(table(approvals, widths=[1.7*inch, 2.0*inch, 1.8*inch, 1.1*inch], font_size=7.3))
    story.append(p("In a real sponsor/CRO setting, this section would be finalized before database lock and signed according to the study's document-control process. It is included here to demonstrate awareness of formal SAP governance.", "Callout"))

    story += [p("Abbreviations", "H1")]
    abbr = [
        ["Term", "Meaning", "Term", "Meaning"],
        ["ADaM", "Analysis Data Model", "ADTTE", "Analysis dataset for time-to-event endpoints"],
        ["AE/TEAE", "Adverse event / treatment-emergent adverse event", "BOR", "Best overall response"],
        ["CNSR", "Censoring indicator", "CSR", "Clinical study report"],
        ["DCR", "Disease control rate", "FAS", "Full Analysis Set"],
        ["HR", "Hazard ratio", "KM", "Kaplan-Meier"],
        ["ORR", "Objective response rate", "PFS/OS", "Progression-free survival / overall survival"],
        ["SAP", "Statistical Analysis Plan", "TLF", "Tables, listings and figures"],
    ]
    story.append(table(abbr, widths=[0.8*inch, 2.1*inch, 0.8*inch, 2.9*inch], font_size=7.2))
    story.append(PageBreak())

    # Study overview
    story += [p("1. Study design and statistical objectives", "H1")]
    overview = [
        ["Design feature", "SAP specification"],
        ["Study design", "Randomized, double-blind, placebo-controlled Phase III oncology simulation"],
        ["Subjects", f"{len(adsl)} randomized; {n_t} ONC-305 + SOC and {n_c} Placebo + SOC"],
        ["Randomization", "1:1 allocation with stratification by ECOG performance status and PD-L1 category"],
        ["Primary objective", "Compare PFS between treatment arms in the FAS"],
        ["Key secondary objectives", "Compare OS and ORR; characterize exposure and safety"],
        ["Data cut-off", DATA_CUTOFF],
        ["Database lock", DBL_DATE],
    ]
    story.append(table(overview, widths=[1.7*inch, 4.9*inch], font_size=7.4))
    story += [p("The SAP is written from the perspective of a statistician preparing a final analysis package. It defines the analysis intent before interpreting treatment results and links each major endpoint to analysis datasets and outputs.", "Callout")]

    story += [p("2. Endpoints and endpoint derivations", "H1")]
    endpoints = [
        ["Endpoint", "Dataset / variable", "Derivation", "Output"],
        ["PFS", "ADTTE; PARAMCD=PFS; AVAL; CNSR", "Months from randomization to progression/death/censor date; CNSR=0 event", "T14.2.1, F14.2.1"],
        ["OS", "ADTTE; PARAMCD=OS; AVAL; CNSR", "Months from randomization to death/last-known-alive date; CNSR=0 death", "T14.2.2, F14.2.2"],
        ["ORR", "ADRS; ORRFL", "Y if BOR is CR or PR; all FAS subjects in denominator", "T14.2.3"],
        ["DCR", "ADRS; DCRFL", "Y if BOR is CR, PR or SD; all FAS subjects in denominator", "T14.2.3"],
        ["Exposure", "ADSL; TRTDURM; RDI", "Duration and relative dose intensity from synthetic exposure records", "T14.1.3"],
        ["Safety", "ADAE; ADLB", "Subject-level TEAE, grade, seriousness, discontinuation, fatal and lab-shift summaries", "T14.3.x, L16.2.x"],
    ]
    story.append(table(endpoints, widths=[0.8*inch, 1.6*inch, 3.0*inch, 1.2*inch], font_size=7.0))
    story.append(PageBreak())

    # Estimands and populations
    story += [p("3. Estimands", "H1")]
    story += [p("The estimand section defines the treatment effect of interest before analysis. This is now a key expectation in modern clinical-trial planning and is especially important for missing data and intercurrent-event handling.", "Callout")]
    estimands = [
        ["Attribute", "Primary PFS estimand", "Key secondary OS estimand", "Response estimand"],
        ["Treatment", "ONC-305 + SOC vs Placebo + SOC", "ONC-305 + SOC vs Placebo + SOC", "ONC-305 + SOC vs Placebo + SOC"],
        ["Population", "All randomized subjects in FAS", "All randomized subjects in FAS", "All randomized subjects in FAS"],
        ["Variable", "Time to progression/death", "Time to death", "Confirmed or simulated best overall response"],
        ["Intercurrent events", "Treatment-policy for discontinuation/subsequent therapy; death before progression is event", "Death regardless of treatment discontinuation", "Missing/non-evaluable response remains in denominator"],
        ["Summary measure", "Cox HR; KM median and landmark rates", "Cox HR; KM median and landmark rates", "Risk difference/ORR with exact CI"],
        ["Sensitivity", "Adjusted and alternative censoring analyses", "Adjusted/unadjusted Cox summaries", "Supportive response-evaluable analysis"],
    ]
    story.append(table(estimands, widths=[1.1*inch, 2.1*inch, 1.8*inch, 1.6*inch], font_size=6.8))
    story += [p("4. Analysis populations", "H1")]
    populations = [
        ["Population", "Definition", "Treatment grouping", "Primary outputs"],
        ["Randomized Set", "All randomized subjects", "Randomized arm", "Disposition and randomization accountability"],
        ["Full Analysis Set", "All randomized subjects", "Randomized arm", "PFS, OS, ORR, DCR, subgroup analyses"],
        ["Safety Set", "All subjects receiving at least one dose", "Actual treatment", "Exposure, AE and lab analyses"],
        ["Response-Evaluable Supportive Set", "Subjects with measurable disease and adequate response information", "Randomized arm", "Supportive response summaries only"],
    ]
    story.append(table(populations, widths=[1.5*inch, 2.7*inch, 1.1*inch, 1.3*inch], font_size=7.0))
    story.append(PageBreak())

    # Methods
    story += [p("5. General analysis conventions", "H1")]
    story += bullets([
        "Unless otherwise stated, all tests are two-sided and confidence intervals are 95%.",
        "Percentages are based on the relevant analysis population denominator shown in the table header.",
        "Time-to-event variables are summarized in months using days / 30.4375.",
        "A subject is counted once per AE summary category using occurrence flags; maximum severity is used where applicable.",
        "All results in this portfolio are simulated and should be evaluated as evidence of workflow competence rather than product efficacy or safety.",
    ], "Small")

    story += [p("6. Efficacy analysis methods", "H1")]
    models = [
        ["Analysis", "Primary method", "Model/covariates", "Interpretation"],
        ["PFS", "Stratified/log-rank comparison and Cox model", "Treatment main effect; adjusted model includes ECOG and PD-L1 category", "HR < 1 favors ONC-305 + SOC"],
        ["OS", "Log-rank comparison and Cox model", "Treatment main effect; adjusted model includes ECOG and PD-L1 category", "HR < 1 favors ONC-305 + SOC"],
        ["ORR/DCR", "Exact binomial CI by arm", "No formal model in primary portfolio", "Higher percentage favors ONC-305 + SOC"],
        ["Subgroups", "Descriptive Cox HR within subgroup", "Age, sex, ECOG, stage, PD-L1 and region", "Hypothesis-generating only"],
    ]
    story.append(table(models, widths=[0.8*inch, 2.0*inch, 2.2*inch, 1.6*inch], font_size=7.0))
    story += [p("PFS censoring rules", "H2")]
    censor = [
        ["Clinical scenario", "Analysis date", "CNSR", "Rationale"],
        ["Documented progression", "First progression date", "0", "Primary PFS event"],
        ["Death before progression", "Death date", "0", "Death is included in PFS"],
        ["Alive/no progression at cut-off", "Last adequate disease assessment", "1", "No event observed"],
        ["Withdrawal/lost to follow-up", "Last adequate disease assessment", "1", "Censored before missing follow-up"],
        ["No post-baseline assessment", "Randomization/baseline date", "1", "Conservative censoring; sensitivity analysis planned"],
    ]
    story.append(table(censor, widths=[2.0*inch, 1.7*inch, 0.7*inch, 2.2*inch], font_size=7.0))
    story.append(PageBreak())

    story += [p("7. Multiplicity, sensitivity and supplementary analyses", "H1")]
    mult = [
        ["Test sequence", "Endpoint", "Decision rule in simulated portfolio"],
        ["1", "PFS", "Primary endpoint at two-sided alpha 0.05"],
        ["2", "OS", "Key secondary endpoint interpreted after PFS"],
        ["3", "ORR", "Key secondary endpoint interpreted after OS"],
        ["Supportive", "DCR/subgroups/safety", "Descriptive only; no confirmatory alpha allocation"],
    ]
    story.append(table(mult, widths=[1.0*inch, 1.6*inch, 4.0*inch], font_size=7.2))
    sens = [
        ["Sensitivity/supplementary analysis", "Purpose", "Planned implementation"],
        ["Adjusted Cox model", "Assess robustness to baseline prognostic factors", "Treatment + ECOG + PD-L1 category"],
        ["Unstratified Cox model", "Assess model dependence", "Treatment-only Cox model"],
        ["Alternative PFS censoring", "Assess impact of no post-baseline assessment", "Censor at randomization or exclude as supportive only"],
        ["Subgroup analysis", "Evaluate consistency", "Forest plot with HRs by age, sex, ECOG, stage, PD-L1 and region"],
        ["Response-evaluable supportive ORR", "Assess impact of NE responses", "Exclude NE from denominator in supportive table if implemented"],
    ]
    story.append(Spacer(1, 6))
    story.append(table(sens, widths=[1.9*inch, 2.4*inch, 2.3*inch], font_size=7.0))

    story += [p("8. Safety analysis methods", "H1")]
    story += bullets([
        "Safety summaries use the Safety Set and actual treatment received.",
        "TEAEs are events starting or worsening on or after first dose in the synthetic data.",
        "AE tables count subjects, not repeated events, unless the listing explicitly shows event-level records.",
        "Laboratory shift tables summarize baseline grade to worst post-baseline grade by parameter.",
        "Fatal AEs, serious AEs and AEs leading to discontinuation are listed for reviewer traceability.",
    ], "Small")
    story.append(PageBreak())

    # Data standards, QC, outputs
    story += [p("9. Data standards and derivation traceability", "H1")]
    flow = [
        ["Layer", "Artifacts", "Purpose"],
        ["Synthetic source", "data/raw/*.csv", "Represent SDTM-like source records for subjects, AE, labs, exposure, response and TTE"],
        ["Analysis datasets", "data/adam/*.csv", "ADaM-style ADSL, ADTTE, ADAE, ADRS and ADLB"],
        ["Metadata", "data/specs and metadata/*.csv", "Variable definitions, define-like XML, result metadata and source-to-analysis traceability"],
        ["Outputs", "outputs/tables, outputs/listings, outputs/figures", "TLFs for efficacy, safety and listings"],
        ["Reports", "docs and outputs/reports", "SAP, CSR-style report, TLF packet, reviewer guide and validation report"],
    ]
    story.append(table(flow, widths=[1.2*inch, 2.2*inch, 3.2*inch], font_size=7.0))
    story += [p("10. Programming and quality control", "H1")]
    qc_methods = [
        ["QC area", "Expectation", "Portfolio evidence"],
        ["Reproducibility", "All outputs regenerated from one command", "programs/python/run_all.py"],
        ["Subject counts", "FAS/Safety counts reconcile across datasets", "qc/validation_checks.csv"],
        ["Endpoint integrity", "PFS/OS records and CNSR values checked", "ADTTE validation checks"],
        ["Safety integrity", "AE chronology and toxicity grades checked", "ADAE validation checks"],
        ["Metadata", "Analysis variables documented", "adam_spec.csv and define_like_metadata.xml"],
        ["Reviewer traceability", "Outputs linked to source datasets/programs", "analysis_results_metadata.csv"],
    ]
    story.append(table(qc_methods, widths=[1.5*inch, 2.5*inch, 2.6*inch], font_size=7.0))
    story.append(PageBreak())

    story += [p("11. Planned TLF package", "H1")]
    meta = pd.read_csv(ROOT / "metadata" / "analysis_results_metadata.csv")
    story.append(df_table(meta[["Result ID", "Title", "Source", "Population", "Method"]], max_rows=25, font_size=6.6, total_width=6.7*inch, first_col=0.75*inch))
    story += [p("12. Software, limitations and references", "H1")]
    story += bullets([
        "Primary executable implementation: Python with pandas, scipy, statsmodels, matplotlib and reportlab.",
        "SAS and R files are included as templates to demonstrate mapping to regulated workflows; they are not executed by this environment.",
        "CSV outputs are used for portability. The optional R script can be extended to export XPT files if local dependencies are available.",
        "No real patients, sites, product, sponsor or clinical claims are represented.",
    ], "Small")
    refs = [
        ["Reference", "How it informed this portfolio"],
        ["ICH E9(R1)", "Estimands, intercurrent events and sensitivity-analysis framing"],
        ["ICH E3", "CSR-style reporting structure and appendices"],
        ["CDISC ADaM", "Analysis dataset traceability and reviewability"],
        ["FDA Study Data Technical Conformance Guide", "Study-data submission packaging concepts and define-like metadata awareness"],
    ]
    story.append(table(refs, widths=[2.2*inch, 4.4*inch], font_size=7.0))

    DOCS.mkdir(exist_ok=True)
    (DOCS / "statistical_analysis_plan.md").write_text("""# Pharma-style Statistical Analysis Plan

This SAP is generated by `programs/python/render_pharma_grade_documents.py`.

Major content:

- Document administration, version history and mock approval table.
- Abbreviations and study overview.
- Endpoint derivations and analysis populations.
- Estimand table for PFS, OS and response.
- General conventions, PFS censoring rules, multiplicity and sensitivity analyses.
- Safety analysis methods.
- Data standards, ADaM traceability, programming/QC and TLF index.

See `docs/statistical_analysis_plan.pdf` for the full rendered version.
""", encoding="utf-8")
    pdf(DOCS / "statistical_analysis_plan.pdf", "SAP", story)


def pharma_grade_csr() -> None:
    d = _load()
    adsl = d["adsl"]
    n_t = int((adsl.TRT01P == ARM_T).sum())
    n_c = int((adsl.TRT01P == ARM_C).sum())
    pfs_hr = _hr(d["pfs"])
    os_hr = _hr(d["os"])
    pfs_p = _pval(d["pfs"])
    os_p = _pval(d["os"])
    orr_row = d["orr"][d["orr"].iloc[:,0].str.contains("Objective response", regex=False)].iloc[0]
    safety = d["safety"]
    any_teae = safety.iloc[0].tolist()
    serious = safety[safety.iloc[:,0].str.contains("serious", case=False)].iloc[0].tolist()
    g3 = safety[safety.iloc[:,0].str.contains("grade", case=False)].iloc[0].tolist()
    qc = d["qc"]

    story = title_block("Clinical Study Analysis Report", "Pharma-style simulated statistical report aligned to CSR sections", REPORT_VERSION)
    story += [p("Document administration", "H1")]
    version_history = [
        ["Version", "Date", "Description"],
        ["1.0", "2026-02-10", "Initial portfolio statistical report"],
        ["2.0", "2026-02-15", "CSR-style report with study conduct, efficacy, safety, QC and reviewer appendices"],
    ]
    story.append(table(version_history, widths=[0.9*inch, 1.2*inch, 4.5*inch], font_size=7.3))
    story += [p("Report synopsis", "H1")]
    synopsis = [
        ["Item", "Result / description"],
        ["Study", f"{STUDY_ID}; simulated Phase III oncology portfolio"],
        ["Data cut-off / DBL", f"{DATA_CUTOFF} / {DBL_DATE}"],
        ["Subjects", f"{len(adsl)} randomized: {n_t} ONC-305 + SOC and {n_c} Placebo + SOC"],
        ["Primary endpoint", f"PFS HR {pfs_hr}; log-rank p-value {pfs_p}"],
        ["Key secondary endpoints", f"OS HR {os_hr}; log-rank p-value {os_p}; ORR {orr_row.iloc[1]} vs {orr_row.iloc[2]}"],
        ["Safety", f"Any TEAE {any_teae[1]} vs {any_teae[2]}; serious TEAE {serious[1]} vs {serious[2]}; grade >=3 TEAE {g3[1]} vs {g3[2]}"],
        ["QC status", f"{int((qc.Status=='PASS').sum())} PASS, {int((qc.Status=='WARN').sum())} WARN, {int((qc.Status=='FAIL').sum())} FAIL"],
    ]
    story.append(table(synopsis, widths=[1.6*inch, 5.0*inch], font_size=7.4))
    story.append(p("This report is written as a portfolio-scale statistical report, not a complete regulatory CSR. It includes the sections a recruiter would expect a statistician to understand: populations, endpoint definitions, statistical methods, efficacy, safety, data standards, QC and limitations.", "Callout"))
    story.append(PageBreak())

    story += [p("1. Study design and analysis methods", "H1")]
    story += bullets([
        "Randomized, double-blind, placebo-controlled Phase III oncology simulation.",
        "The primary endpoint is PFS analyzed in the FAS using KM summaries, log-rank test and Cox model.",
        "OS and ORR are key secondary endpoints; safety is summarized in the Safety Set using actual treatment received.",
        "All analysis datasets, TLF outputs and reports are generated reproducibly from synthetic data.",
    ], "Small")
    methods = [
        ["Endpoint", "Population", "Primary method", "Result location"],
        ["PFS", "FAS", "KM, log-rank, Cox HR", "Table 14.2.1; Figure 14.2.1"],
        ["OS", "FAS", "KM, log-rank, Cox HR", "Table 14.2.2; Figure 14.2.2"],
        ["ORR/DCR", "FAS", "Counts, percentages, exact CI", "Table 14.2.3"],
        ["Safety", "Safety Set", "Subject-level TEAE and lab summaries", "Tables 14.3.x; Listings 16.2.x"],
    ]
    story.append(table(methods, widths=[0.9*inch, 1.0*inch, 2.8*inch, 1.9*inch], font_size=7.2))
    story += [p("2. Subject disposition and baseline characteristics", "H1")]
    story.append(df_table(d["disp"], font_size=6.8, total_width=6.6*inch, first_col=1.8*inch))
    story.append(Spacer(1, 6))
    story.append(p("Baseline characteristics excerpt", "H2"))
    story.append(df_table(d["demo"].head(14), font_size=6.4, total_width=6.6*inch, first_col=1.8*inch))
    story.append(PageBreak())

    story += [p("3. Data review and protocol deviations", "H1")]
    story += bullets([
        "A data-review log and protocol-deviation table are included to show realistic database-lock thinking.",
        "Deviation counts are mock/simulated and are not derived from real clinical data.",
    ], "Small")
    story.append(df_table(d["pdev"], font_size=6.7, total_width=6.6*inch, first_col=2.4*inch))
    issue = pd.read_csv(QC / "data_review_issue_log.csv", keep_default_na=False)
    story.append(Spacer(1, 6))
    story.append(p("Data review issue log", "H2"))
    story.append(df_table(issue, font_size=6.3, total_width=6.6*inch, first_col=0.7*inch))
    story.append(PageBreak())

    story += [p("4. Primary efficacy: progression-free survival", "H1")]
    story += bullets([
        f"The simulated primary analysis favors ONC-305 + SOC, with Cox HR {pfs_hr} and log-rank p-value {pfs_p}.",
        "Kaplan-Meier medians and landmark rates are reported by treatment arm.",
        "The subgroup forest plot is descriptive and intended to demonstrate oncology TLF competence.",
    ], "Small")
    story.append(df_table(d["pfs"], font_size=6.8, total_width=6.6*inch, first_col=2.0*inch))
    if (OUT_FIGURES / "f14_2_1_km_pfs.png").exists():
        story.append(Spacer(1, 6))
        story.append(Image(str(OUT_FIGURES / "f14_2_1_km_pfs.png"), width=6.4*inch, height=3.7*inch))
    story.append(PageBreak())

    story += [p("5. Secondary efficacy: OS and response", "H1")]
    story += bullets([
        f"OS in the simulated dataset favors ONC-305 + SOC, with Cox HR {os_hr} and log-rank p-value {os_p}.",
        f"ORR is {orr_row.iloc[1]} for ONC-305 + SOC and {orr_row.iloc[2]} for Placebo + SOC in the FAS.",
    ], "Small")
    story.append(df_table(d["os"], font_size=6.8, total_width=6.6*inch, first_col=2.0*inch))
    story.append(Spacer(1, 6))
    story.append(df_table(d["orr"], font_size=6.3, total_width=6.6*inch, first_col=1.7*inch))
    if (OUT_FIGURES / "f14_2_4_waterfall_best_change.png").exists():
        story.append(Spacer(1, 6))
        story.append(Image(str(OUT_FIGURES / "f14_2_4_waterfall_best_change.png"), width=6.4*inch, height=3.2*inch))
    story.append(PageBreak())

    story += [p("6. Safety and exposure", "H1")]
    story += bullets([
        "Safety summaries use the Safety Set and actual treatment received.",
        "The active arm has higher treatment-related TEAE incidence in the simulation, as often expected when demonstrating oncology safety reporting.",
        "Listings are included for deaths, SAEs and AEs leading to discontinuation.",
    ], "Small")
    story.append(df_table(d["safety"], font_size=6.8, total_width=6.6*inch, first_col=2.2*inch))
    story.append(Spacer(1, 6))
    story.append(df_table(d["expo"], font_size=6.8, total_width=6.6*inch, first_col=1.8*inch))
    if (OUT_FIGURES / "f14_3_1_top_teae_bar.png").exists():
        story.append(Spacer(1, 6))
        story.append(Image(str(OUT_FIGURES / "f14_3_1_top_teae_bar.png"), width=6.4*inch, height=3.4*inch))
    story.append(PageBreak())

    story += [p("7. Validation, traceability and reviewer readiness", "H1")]
    tracker = pd.read_csv(QC / "program_validation_tracker.csv", keep_default_na=False)
    meta = pd.read_csv(ROOT / "metadata" / "analysis_results_metadata.csv", keep_default_na=False)
    story += bullets([
        f"Validation status: {int((qc.Status=='PASS').sum())} PASS, {int((qc.Status=='WARN').sum())} WARN, {int((qc.Status=='FAIL').sum())} FAIL.",
        "Result-level traceability links outputs to source datasets, analysis populations, methods and programs.",
        "The package includes an ADaM Reviewer Guide, Programming/QC Plan and TLF Shell Book.",
    ], "Small")
    story.append(p("Program validation tracker", "H2"))
    story.append(df_table(tracker, max_rows=12, font_size=6.1, total_width=6.6*inch, first_col=1.1*inch))
    story.append(Spacer(1, 6))
    story.append(p("Analysis results metadata excerpt", "H2"))
    story.append(df_table(meta[["Result ID", "Title", "Source", "Population", "Program"]], max_rows=14, font_size=6.3, total_width=6.6*inch, first_col=0.7*inch))
    story.append(PageBreak())

    story += [p("8. Discussion, limitations and portfolio conclusion", "H1")]
    story += bullets([
        "The simulated efficacy results demonstrate survival-analysis and response-summary capability. They are not clinical evidence.",
        "The safety outputs demonstrate subject-level adverse-event reporting and lab-shift logic, not medical conclusions about a real therapy.",
        "The most job-relevant strength is the full analysis workflow: SAP -> ADaM derivation -> TLFs -> validation -> CSR-style report -> reviewer guide.",
        "The next optional upgrade would be to export formal XPT datasets and run a standards validation tool locally, then add the validation report to the repository.",
    ], "Small")
    story += [p("Repository appendices", "H2")]
    app = [
        ["Appendix", "Repository location"],
        ["Full TLF packet", "outputs/reports/tlf_packet.pdf"],
        ["Validation report", "outputs/reports/validation_report.pdf"],
        ["ADaM Reviewer Guide", "outputs/reports/adam_reviewer_guide.pdf"],
        ["Programming/QC Plan", "outputs/reports/programming_qc_plan.pdf"],
        ["TLF Shell Book", "outputs/reports/tlf_shell_book.pdf"],
        ["Traceability metadata", "metadata/analysis_results_metadata.csv and source_to_adam_traceability.csv"],
        ["GitHub guide", "docs/github_upload_guide.md"],
    ]
    story.append(table(app, widths=[2.1*inch, 4.5*inch], font_size=7.2))

    (OUT_REPORTS / "clinical_study_analysis_report.md").write_text(f"""# Pharma-style Clinical Study Analysis Report

Generated by `programs/python/render_pharma_grade_documents.py`.

## Key results in the simulated data

- N={len(adsl)} randomized subjects: {n_t} ONC-305 + SOC and {n_c} Placebo + SOC.
- PFS HR {pfs_hr}; log-rank p-value {pfs_p}.
- OS HR {os_hr}; log-rank p-value {os_p}.
- ORR {orr_row.iloc[1]} versus {orr_row.iloc[2]}.
- QC status: {int((qc.Status=='PASS').sum())} PASS, {int((qc.Status=='WARN').sum())} WARN, {int((qc.Status=='FAIL').sum())} FAIL.

See the rendered PDF for full CSR-style sections.
""", encoding="utf-8")
    pdf(OUT_REPORTS / "clinical_study_analysis_report.pdf", "CSR-style Report", story)


def render_pharma_grade_documents() -> None:
    d = _load()
    make_protocol_deviation_table(d["adsl"])
    pharma_grade_sap()
    pharma_grade_csr()
    print("Rendered pharma-grade SAP and CSR-style report.")


if __name__ == "__main__":
    render_pharma_grade_documents()
