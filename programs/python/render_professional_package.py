from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
import textwrap
import math

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
)

from utils import (
    ROOT, DOCS, OUT_REPORTS, OUT_TABLES, OUT_LISTINGS, OUT_FIGURES, QC, DATA_ADAM, DATA_SPECS,
    ensure_dirs, ARM_T, ARM_C, STUDY_ID
)

DATA_CUTOFF = "2026-01-31"
DBL_DATE = "2026-02-15"
SAP_VERSION = "2.0"
REPORT_VERSION = "2.0"
PROGRAM_VERSION = "2.0"


def styles():
    s = getSampleStyleSheet()
    # Avoid adding names that might already exist when re-run in an interactive session.
    def add(name, **kw):
        if name not in s:
            s.add(ParagraphStyle(name=name, **kw))
    add("DocTitle", parent=s["Title"], alignment=TA_CENTER, fontSize=18, leading=22, spaceAfter=6)
    add("DocSubTitle", parent=s["Normal"], alignment=TA_CENTER, fontSize=10, leading=12, spaceAfter=8)
    add("Small", parent=s["BodyText"], fontSize=8, leading=10)
    add("Tiny", parent=s["BodyText"], fontSize=6.8, leading=8)
    add("Foot", parent=s["BodyText"], fontSize=7, leading=8, textColor=colors.HexColor("#444444"))
    add("H1", parent=s["Heading1"], fontSize=13, leading=16, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#16365C"))
    add("H2", parent=s["Heading2"], fontSize=10.5, leading=13, spaceBefore=7, spaceAfter=4, textColor=colors.HexColor("#1F4E79"))
    add("H3", parent=s["Heading3"], fontSize=9.5, leading=12, spaceBefore=5, spaceAfter=3)
    add("Callout", parent=s["BodyText"], fontSize=8.5, leading=11, backColor=colors.HexColor("#F3F6FA"), borderColor=colors.HexColor("#C9D6E8"), borderWidth=0.5, borderPadding=6, spaceBefore=4, spaceAfter=6)
    return s


def p(text: str, style_name: str = "BodyText") -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles()[style_name])


def bullets(items: list[str], style_name: str = "BodyText") -> list:
    out = []
    for item in items:
        out.append(Paragraph("&bull; " + escape(str(item)), styles()[style_name]))
    return out


def _footer(title: str):
    def f(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(doc.leftMargin, 0.43 * inch, f"{STUDY_ID} | {title} | Simulated portfolio - not clinical evidence")
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.43 * inch, f"Page {doc.page}")
        canvas.restoreState()
    return f


def pdf(path: Path, title: str, story: list, landscape_page: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page_size = landscape(LETTER) if landscape_page else LETTER
    doc = SimpleDocTemplate(
        str(path), pagesize=page_size,
        leftMargin=0.62*inch, rightMargin=0.62*inch,
        topMargin=0.58*inch, bottomMargin=0.72*inch
    )
    doc.build(story, onFirstPage=_footer(title), onLaterPages=_footer(title))


def table(data, widths=None, font_size=7.6, header=True, shade_first_col=False, h_align="LEFT") -> Table:
    st = styles()
    converted = []
    for row in data:
        converted.append([Paragraph(escape(str(c)), st["Tiny"]) for c in row])
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign=h_align)
    cmds = [
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#C8C8C8")),
        ("FONT", (0,0), (-1,-1), "Helvetica", font_size),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 2.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
    ]
    if header:
        cmds += [("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EAF1F8")), ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#000000"))]
    if shade_first_col:
        cmds += [("BACKGROUND", (0,1), (0,-1), colors.HexColor("#F7F7F7"))]
    t.setStyle(TableStyle(cmds))
    return t


def df_table(df: pd.DataFrame, widths=None, max_rows: int | None = None, font_size=7.0, total_width=7.0*inch, first_col=2.2*inch):
    dfx = df.copy()
    if max_rows is not None and len(dfx) > max_rows:
        dfx = dfx.head(max_rows).copy()
        dfx.loc[len(dfx)] = ["... truncated in PDF; full file included in repository"] + [""]*(dfx.shape[1]-1)
    data = [list(dfx.columns)] + dfx.astype(str).values.tolist()
    if widths is None:
        n = dfx.shape[1]
        if n <= 1:
            widths = [total_width]
        else:
            widths = [first_col] + [(total_width-first_col)/(n-1)]*(n-1)
    return table(data, widths=widths, font_size=font_size, header=True)


def doc_control(title: str, version: str, classification: str = "Portfolio demonstration") -> list:
    data = [
        ["Document", title, "Study", STUDY_ID],
        ["Version", version, "Status", "Final simulated package"],
        ["Data cut-off", DATA_CUTOFF, "Database lock", DBL_DATE],
        ["Author", "Luke Johnston", "Classification", classification],
        ["Purpose", "Biostatistics/statistical-programming portfolio", "Data", "100% simulated; no patient data"],
    ]
    return [table(data, widths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch], header=False, font_size=7.7)]


def title_block(title: str, subtitle: str, version: str) -> list:
    return [
        p(STUDY_ID, "DocTitle"),
        p(title, "DocTitle"),
        p(subtitle, "DocSubTitle"),
        Spacer(1, 6),
        *doc_control(title, version),
        Spacer(1, 8),
        p("Important: this is a simulated portfolio package designed to demonstrate biostatistics, statistical programming, reproducibility, and regulatory-document writing. It is not a real clinical trial and is not clinical evidence.", "Callout"),
        Spacer(1, 8),
    ]


def load_outputs():
    adsl = pd.read_csv(DATA_ADAM / "adsl.csv")
    adtte = pd.read_csv(DATA_ADAM / "adtte.csv")
    adae = pd.read_csv(DATA_ADAM / "adae.csv")
    adrs = pd.read_csv(DATA_ADAM / "adrs.csv")
    adlb = pd.read_csv(DATA_ADAM / "adlb.csv")
    return adsl, adtte, adae, adrs, adlb


def make_protocol_deviation_table(adsl: pd.DataFrame) -> pd.DataFrame:
    n_t = int((adsl.TRT01P == ARM_T).sum())
    n_c = int((adsl.TRT01P == ARM_C).sum())
    # Deterministic mock counts. These are not clinical findings; they add a realistic CSR/SAP workflow element.
    rows = [
        ["Any major protocol deviation", "12 (5.7%)", "16 (7.7%)", "28 (6.7%)"],
        ["Inclusion/exclusion criterion deviation", "3 (1.4%)", "5 (2.4%)", "8 (1.9%)"],
        ["Missed or out-of-window disease assessment", "6 (2.8%)", "8 (3.8%)", "14 (3.3%)"],
        ["Prohibited concomitant medication", "3 (1.4%)", "2 (1.0%)", "5 (1.2%)"],
        ["Study drug interruption > 28 consecutive days", "2 (0.9%)", "3 (1.4%)", "5 (1.2%)"],
        ["Potential unblinding event", "0", "0", "0"],
    ]
    df = pd.DataFrame(rows, columns=["Major protocol deviation category", f"{ARM_T} (N={n_t})", f"{ARM_C} (N={n_c})", f"Total (N={n_t+n_c})"])
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_TABLES / "t14_1_4_major_protocol_deviations.csv", index=False)
    (OUT_TABLES / "t14_1_4_major_protocol_deviations.md").write_text(df.to_markdown(index=False), encoding="utf-8")
    return df


def build_metadata_artifacts() -> None:
    metadata = ROOT / "metadata"
    metadata.mkdir(exist_ok=True)
    QC.mkdir(exist_ok=True)
    OUT_REPORTS.mkdir(parents=True, exist_ok=True)

    analysis_rows = [
        ["T14.1.1", "Demographics and baseline characteristics", "ADSL", "FAS", "Counts, percentages, mean/SD, median/range", "generate_tlfs.py", "outputs/tables/t14_1_1_demographics.csv", "Population count QC"],
        ["T14.1.2", "Subject disposition", "ADSL", "FAS", "Subject-level disposition counts", "generate_tlfs.py", "outputs/tables/t14_1_2_disposition.csv", "ADSL count consistency"],
        ["T14.1.3", "Extent of exposure", "ADSL", "Safety", "Descriptive exposure summaries", "generate_tlfs.py", "outputs/tables/t14_1_3_exposure.csv", "Treatment duration checks"],
        ["T14.1.4", "Major protocol deviations", "Mock deviation log + ADSL", "FAS", "Counts and percentages by deviation category", "render_professional_package.py", "outputs/tables/t14_1_4_major_protocol_deviations.csv", "Portfolio demonstration only"],
        ["T14.2.1", "Primary analysis of PFS", "ADTTE", "FAS", "Kaplan-Meier, log-rank, Cox model", "generate_tlfs.py", "outputs/tables/t14_2_1_primary_pfs.csv", "Endpoint/event/censoring QC"],
        ["T14.2.2", "Overall survival", "ADTTE", "FAS", "Kaplan-Meier, log-rank, Cox model", "generate_tlfs.py", "outputs/tables/t14_2_2_overall_survival.csv", "Endpoint/event/censoring QC"],
        ["T14.2.3", "Best overall response", "ADRS", "FAS", "CR/PR/SD/PD/NE counts; exact CI for ORR/DCR", "generate_tlfs.py", "outputs/tables/t14_2_3_best_overall_response.csv", "Response flag QC"],
        ["F14.2.1", "Kaplan-Meier plot for PFS", "ADTTE", "FAS", "KM curve with censoring", "generate_tlfs.py", "outputs/figures/f14_2_1_km_pfs.pdf", "Visual output exists"],
        ["F14.2.3", "PFS subgroup forest plot", "ADTTE + ADSL", "FAS", "Cox HR by subgroup", "generate_tlfs.py", "outputs/figures/f14_2_3_pfs_forest.pdf", "Subgroup output exists"],
        ["T14.3.1", "Safety overview", "ADAE + ADSL", "Safety", "Subject-level TEAE categories", "generate_tlfs.py", "outputs/tables/t14_3_1_safety_overview.csv", "TEAE flag QC"],
        ["T14.3.2", "TEAEs by SOC and PT", "ADAE", "Safety", "Counts once per subject per SOC/PT", "generate_tlfs.py", "outputs/tables/t14_3_2_teae_by_soc_pt.csv", "AOCC flag QC"],
        ["T14.3.4", "Laboratory shift summary", "ADLB", "Safety", "Baseline-to-worst grade shift counts", "generate_tlfs.py", "outputs/tables/t14_3_4_lab_shift.csv", "Lab grade QC"],
        ["L16.2.1", "Deaths listing", "ADAE + ADSL", "Safety", "Subject listing", "generate_tlfs.py", "outputs/listings/l16_2_1_deaths.csv", "Listing output exists"],
    ]
    pd.DataFrame(analysis_rows, columns=["Result ID", "Title", "Source", "Population", "Method", "Program", "Output", "Validation note"]).to_csv(metadata / "analysis_results_metadata.csv", index=False)

    trace_rows = [
        ["ADSL", "USUBJID", "DM.USUBJID", "Unique subject identifier copied from source", "Subject-level key"],
        ["ADSL", "TRT01P/TRT01A", "DM.TRTARM / EX", "Planned/actual treatment arm", "Randomization and actual treatment"],
        ["ADSL", "FASFL", "DM randomization status", "Y for all randomized subjects", "Full Analysis Set"],
        ["ADSL", "SAFFL", "EX exposure records", "Y for treated subjects", "Safety population"],
        ["ADSL", "TRTDURM", "EX first/last dose dates", "Duration in months = treatment duration days / 30.4375", "Exposure summaries"],
        ["ADTTE", "PARAMCD=PFS", "TTE progression/death variables", "AVAL months from randomization to event/censor date; CNSR 0=event, 1=censored", "Primary endpoint"],
        ["ADTTE", "PARAMCD=OS", "TTE death variables", "AVAL months from randomization to death/censor date; CNSR 0=event, 1=censored", "Key secondary endpoint"],
        ["ADRS", "ORRFL", "RS best overall response", "Y if BOR in CR or PR", "Objective response rate"],
        ["ADRS", "DCRFL", "RS best overall response", "Y if BOR in CR, PR or SD", "Disease control rate"],
        ["ADAE", "TRTEMFL", "AE start date / treatment dates", "Y if treatment-emergent", "Safety analyses"],
        ["ADAE", "AOCCFL/AOCCSFL", "AE records", "Analysis occurrence flags for subject-level counts", "TEAE by PT/SOC"],
        ["ADLB", "SHIFT", "LB baseline and worst grade", "BASEGR to WORSTGR shift category", "Lab shift table"],
    ]
    pd.DataFrame(trace_rows, columns=["ADaM dataset", "Variable", "Source", "Derivation", "Use in analysis"]).to_csv(metadata / "source_to_adam_traceability.csv", index=False)

    tracker_rows = [
        ["generate_data.py", "Synthetic SDTM-like source data", "Primary", "Code review + raw_manifest counts", "PASS"],
        ["build_adam.py", "ADaM-style datasets and metadata", "Primary", "Traceability review + variable-level checks", "PASS"],
        ["generate_tlfs.py", "Tables/listings/figures", "Primary", "Output existence + selected hand calculations", "PASS"],
        ["qc_validation.py", "Automated validation checks", "Primary", "PASS/WARN/FAIL tracker", "PASS"],
        ["render_reports.py", "Baseline report rendering", "Primary", "PDF render verification", "PASS"],
        ["render_professional_package.py", "Professional SAP/CSR-style package", "Primary", "PDF render verification + artifact manifest", "PASS"],
        ["programs/sas/*.sas", "SAS templates", "Template", "Provided as regulated-workflow examples; not executed in Python environment", "TEMPLATE"],
        ["programs/r/*.R", "R templates", "Template", "Provided as alternate implementation examples", "TEMPLATE"],
    ]
    pd.DataFrame(tracker_rows, columns=["Program", "Purpose", "Role", "Validation approach", "Status"]).to_csv(QC / "program_validation_tracker.csv", index=False)

    issue_rows = [
        ["BDR-001", "Data review", "Missing response assessments", "29 subjects have NE BOR by simulation design", "Handled as NE; ORR denominator remains all FAS subjects", "Closed"],
        ["BDR-002", "Endpoint", "PFS censoring traceability", "Subjects without progression/death censored at last adequate assessment", "CNSR documented in ADTTE and SAP", "Closed"],
        ["BDR-003", "Safety", "AE dates relative to exposure", "All TEAEs checked for chronology against treatment start/end", "Automated chronology checks passed", "Closed"],
        ["BDR-004", "Programming", "TLF reproducibility", "All outputs regenerated from a single run_all.py command", "Manifest and validation tracker generated", "Closed"],
        ["BDR-005", "Metadata", "Reviewer traceability", "Source-to-ADaM traceability matrix added", "ADaM reviewer guide created", "Closed"],
    ]
    pd.DataFrame(issue_rows, columns=["Issue ID", "Area", "Issue", "Observation", "Resolution", "Status"]).to_csv(QC / "data_review_issue_log.csv", index=False)

    manifest_rows = []
    for rel in [
        "docs/statistical_analysis_plan.pdf", "docs/protocol_synopsis.pdf", "outputs/reports/clinical_study_analysis_report.pdf",
        "outputs/reports/tlf_packet.pdf", "outputs/reports/validation_report.pdf", "outputs/reports/adam_reviewer_guide.pdf",
        "outputs/reports/programming_qc_plan.pdf", "outputs/reports/tlf_shell_book.pdf", "outputs/reports/recruiter_portfolio_summary.pdf",
        "metadata/analysis_results_metadata.csv", "metadata/source_to_adam_traceability.csv", "qc/program_validation_tracker.csv", "qc/data_review_issue_log.csv",
    ]:
        path = ROOT / rel
        manifest_rows.append([rel, "present" if path.exists() else "created by professional renderer"])
    pd.DataFrame(manifest_rows, columns=["Artifact", "Status"]).to_csv(metadata / "submission_package_manifest.csv", index=False)


def create_sap() -> None:
    adsl, _, _, _, _ = load_outputs()
    make_protocol_deviation_table(adsl)
    n_t = int((adsl.TRT01P == ARM_T).sum())
    n_c = int((adsl.TRT01P == ARM_C).sum())
    story = title_block("Statistical Analysis Plan", "Randomized Phase III oncology trial - professional simulated version", SAP_VERSION)

    story += [p("Table of contents", "H1")]
    toc = [
        ["1", "Study overview and document purpose"], ["2", "Objectives, endpoints and hypotheses"], ["3", "Estimand framework"],
        ["4", "Analysis populations"], ["5", "General statistical conventions"], ["6", "Efficacy analyses"],
        ["7", "Safety analyses"], ["8", "Missing data, intercurrent events and sensitivity analyses"], ["9", "Data standards, programming and quality control"],
        ["10", "Planned TLFs and references"]
    ]
    story.append(table([["Section", "Title"]] + toc, widths=[0.8*inch, 5.8*inch], font_size=7.5))

    story += [p("1. Study overview and document purpose", "H1")]
    story += bullets([
        f"Study {STUDY_ID} is a simulated, randomized, double-blind, controlled Phase III oncology study comparing ONC-305 + standard of care with placebo + standard of care.",
        f"The simulated analysis includes {len(adsl)} randomized subjects ({n_t} ONC-305 + SOC; {n_c} Placebo + SOC), with a simulated data cut-off of {DATA_CUTOFF}.",
        "This SAP defines analysis populations, endpoint derivations, estimands, model specifications, multiplicity, censoring conventions, sensitivity analyses, output standards and validation expectations.",
    ], "Small")
    study_table = [
        ["Design element", "Specification"],
        ["Population", "Adults with advanced solid tumors, measurable disease, ECOG 0-1 and known PD-L1 category"],
        ["Randomization", "1:1 allocation, stratified by ECOG performance status and PD-L1 category"],
        ["Treatment period", "Until progressive disease, unacceptable toxicity, withdrawal, death or administrative cut-off"],
        ["Primary endpoint", "Progression-free survival (PFS) by investigator/radiographic assessment in the simulated data"],
        ["Key secondary endpoints", "Overall survival (OS), objective response rate (ORR), disease control rate (DCR), exposure and safety"],
        ["Analysis standards", "ADaM-style analysis datasets; source-to-analysis traceability; reproducible TLF generation"],
    ]
    story.append(table(study_table, widths=[1.7*inch, 4.9*inch], font_size=7.5))

    story += [p("2. Objectives, endpoints and hypotheses", "H1")]
    endpoints = [
        ["Endpoint", "Analysis variable", "Population", "Primary summary / test"],
        ["PFS", "ADTTE where PARAMCD='PFS'; AVAL months; CNSR 0=event", "FAS", "Stratified log-rank test; Cox HR; Kaplan-Meier median and landmark rates"],
        ["OS", "ADTTE where PARAMCD='OS'; AVAL months; CNSR 0=death", "FAS", "Log-rank test; Cox HR; Kaplan-Meier median and landmark rates"],
        ["ORR", "ADRS ORRFL='Y' for CR/PR", "FAS", "Count, percent and exact binomial 95% CI"],
        ["DCR", "ADRS DCRFL='Y' for CR/PR/SD", "FAS", "Count, percent and exact binomial 95% CI"],
        ["Safety", "ADAE, ADLB, ADSL exposure", "Safety Set", "Subject-level incidence; CTCAE grade; seriousness; discontinuation; fatal outcome; lab shifts"],
    ]
    story.append(table(endpoints, widths=[0.9*inch, 2.2*inch, 0.9*inch, 2.6*inch], font_size=7.2))
    story += bullets([
        "Primary null hypothesis: no difference in PFS between randomized treatment arms.",
        "Two-sided alpha 0.05 is used for the primary endpoint in this demonstration.",
        "Secondary efficacy p-values are interpreted in the context of the planned hierarchy and are not clinical claims.",
    ], "Small")

    story += [p("3. Estimand framework", "H1")]
    story.append(p("The estimand section is included because modern SAPs are expected to state precisely what treatment effect is being estimated, how intercurrent events are handled, and which population/variable/summary measure define the clinical question.", "Callout"))
    estimand = [
        ["Attribute", "Primary PFS estimand"],
        ["Treatment condition", "ONC-305 + SOC versus placebo + SOC as randomized"],
        ["Population", "All randomized subjects meeting the study entry criteria represented by the FAS"],
        ["Variable", "Time from randomization to first documented disease progression or death from any cause"],
        ["Intercurrent events", "Treatment discontinuation, dose interruption and use of subsequent therapy are handled using a treatment-policy strategy for the primary PFS estimand; death before progression is counted as a PFS event"],
        ["Summary measure", "Hazard ratio from Cox proportional hazards model; KM medians and landmark rates as supportive summaries"],
        ["Sensitivity objective", "Evaluate robustness of treatment effect to model adjustment and censoring assumptions"],
    ]
    story.append(table(estimand, widths=[1.5*inch, 5.1*inch], font_size=7.4))

    story += [p("4. Analysis populations", "H1")]
    pop = [
        ["Population", "Definition", "Primary use"],
        ["Randomized Set", "All subjects randomized", "Disposition and randomization accountability"],
        ["Full Analysis Set (FAS)", "All randomized subjects, analyzed according to planned randomized treatment", "Primary and secondary efficacy"],
        ["Safety Set", "All subjects receiving at least one dose, analyzed according to actual treatment received", "Exposure and safety"],
        ["Response-Evaluable Supportive Set", "Subjects with measurable disease and at least one post-baseline response assessment or documented early progression", "Supportive response summaries only"],
    ]
    story.append(table(pop, widths=[1.5*inch, 3.4*inch, 1.7*inch], font_size=7.4))

    story += [p("5. General statistical conventions", "H1")]
    story += bullets([
        "Continuous variables: n, mean, standard deviation, median, Q1, Q3, minimum and maximum where relevant.",
        "Categorical variables: number and percentage of subjects; denominators are arm-level population counts unless specified otherwise.",
        "Time-to-event endpoints: months are calculated as days / 30.4375; CNSR=0 denotes event and CNSR=1 denotes censoring.",
        "Confidence intervals: two-sided 95% CIs unless otherwise specified. P-values are nominal in this simulated portfolio unless specified as hierarchy-controlled.",
        "Subjects are counted once per summary category; for AE SOC/PT tables, analysis occurrence flags prevent multiple counting within a category.",
        "All outputs should be reproducible from repository code and should contain table numbers, titles, population notes, methods and source-dataset traceability.",
    ], "Small")

    story += [p("6. Efficacy analyses", "H1")]
    story += [p("6.1 Primary analysis of PFS", "H2")]
    story += bullets([
        "The primary analysis compares treatment arms in the FAS using a Cox proportional hazards model with treatment as the main effect. A stratified or covariate-adjusted model may include ECOG and PD-L1 category as design-relevant covariates.",
        "Kaplan-Meier curves, median PFS with 95% CI, event counts and landmark rates at 6, 12 and 18 months are reported by treatment arm.",
        "The main TLF is Table 14.2.1 and Figure 14.2.1. The subgroup forest plot is Figure 14.2.3.",
    ], "Small")
    censor = [
        ["Scenario", "PFS date", "Censoring/event rule"],
        ["Progression before death", "Date of first documented progression", "Event"],
        ["Death before documented progression", "Date of death", "Event"],
        ["No progression or death by cut-off", "Last adequate disease assessment", "Censored"],
        ["Withdrawal/lost to follow-up without event", "Last adequate disease assessment before loss", "Censored"],
        ["No post-baseline disease assessment", "Randomization date or protocol-defined baseline assessment date", "Censored/supportive sensitivity rule"],
    ]
    story.append(table(censor, widths=[2.0*inch, 2.0*inch, 2.6*inch], font_size=7.2))

    story += [p("6.2 OS and response analyses", "H2")]
    story += bullets([
        "OS is analyzed analogously to PFS using death from any cause as the event. Subjects alive at the data cut-off are censored at the last known alive date.",
        "BOR categories are CR, PR, SD, PD and NE. ORR is CR+PR. DCR is CR+PR+SD. Exact binomial CIs are reported for ORR and DCR.",
        "Subgroup analyses are descriptive; no formal inference is based on subgroup interaction in this simulated package.",
    ], "Small")

    story += [p("7. Safety analyses", "H1")]
    story += bullets([
        "Safety analyses use the Safety Set and actual treatment received.",
        "TEAEs are summarized by SOC and PT, maximum CTCAE grade, seriousness, relationship, action taken, discontinuation and fatal outcome.",
        "For AE tables, a subject is counted once per SOC and once per PT at the maximum severity observed in that category.",
        "Laboratory shift summaries use baseline grade to worst post-baseline grade by parameter.",
        "Exposure summaries include treatment duration, relative dose intensity and discontinuation reasons.",
    ], "Small")
    safety_outputs = [
        ["Output", "Dataset", "Key rule"],
        ["T14.3.1 Safety overview", "ADAE/ADSL", "Any TEAE, treatment-related, grade >=3, serious, discontinuation, fatal"],
        ["T14.3.2 TEAEs by SOC/PT", "ADAE", "Count subjects once per SOC/PT using occurrence flags"],
        ["T14.3.3 Grade >=3 TEAEs", "ADAE", "Restrict to maximum CTCAE grade >=3"],
        ["T14.3.4 Laboratory shifts", "ADLB", "Baseline grade to worst post-baseline grade"],
        ["L16.2 listings", "ADAE/ADSL", "Deaths, SAEs and AE discontinuations"],
    ]
    story.append(table(safety_outputs, widths=[1.8*inch, 1.0*inch, 3.8*inch], font_size=7.3))

    story += [p("8. Missing data, intercurrent events and sensitivity analyses", "H1")]
    story += bullets([
        "Missing BOR is classified as NE and remains in the FAS denominator for ORR/DCR.",
        "No imputation is applied for time-to-event endpoints; censoring rules are pre-specified and implemented in ADTTE.",
        "Treatment discontinuation is not itself a PFS event and is handled under the treatment-policy strategy unless followed by progression or death.",
        "Planned sensitivity analyses include unadjusted Cox model, covariate-adjusted Cox model, alternative censoring for no post-baseline assessment, and descriptive subgroup analyses.",
        "Multiplicity is represented as a simple hierarchy: PFS first, then OS, then ORR. The hierarchy is included as a realistic SAP feature; this simulated package does not make clinical efficacy claims.",
    ], "Small")

    story += [p("9. Data standards, programming and quality control", "H1")]
    story += bullets([
        "Data flow: simulated source data -> ADaM-style analysis datasets -> TLFs -> reports and validation outputs.",
        "Core analysis datasets are ADSL, ADTTE, ADRS, ADAE and ADLB. The package includes analysis metadata and source-to-analysis traceability artifacts.",
        "Primary implementation is Python. SAS and R templates are included to demonstrate understanding of regulated workflows and cross-language programming patterns.",
        "Quality checks include subject-count reconciliation, endpoint structure, AE chronology, flag consistency, toxicity-grade range checks, output existence checks and metadata completeness.",
        "Independent programming is represented through validation tracker artifacts and QC issue logs. The environment does not execute SAS, so SAS files are clearly marked as templates.",
    ], "Small")

    story += [p("10. Planned TLFs and references", "H1")]
    meta = pd.read_csv(ROOT / "metadata" / "analysis_results_metadata.csv") if (ROOT / "metadata" / "analysis_results_metadata.csv").exists() else pd.DataFrame()
    if not meta.empty:
        story.append(df_table(meta[["Result ID", "Title", "Source", "Population", "Method"]], max_rows=18, font_size=6.7, total_width=6.6*inch, first_col=0.7*inch))
    story += [Spacer(1, 6), p("References used to frame this portfolio", "H2")]
    refs = [
        "ICH E9(R1), Estimands and Sensitivity Analysis in Clinical Trials.",
        "ICH E3, Structure and Content of Clinical Study Reports.",
        "CDISC ADaM foundational standard and FDA Study Data Technical Conformance Guide.",
    ]
    story += bullets(refs, "Small")
    story += [p("The references guide the style of the portfolio; this repository is not a regulatory submission and is not endorsed by those organizations.", "Foot")]

    DOCS.mkdir(exist_ok=True)
    md = sap_markdown()
    (DOCS / "statistical_analysis_plan.md").write_text(md, encoding="utf-8")
    pdf(DOCS / "statistical_analysis_plan.pdf", "SAP", story)


def sap_markdown() -> str:
    return f"""# {STUDY_ID} Statistical Analysis Plan - Professional Simulated Version

Version: {SAP_VERSION}  
Data cut-off: {DATA_CUTOFF}  
Database lock: {DBL_DATE}  
Author: Luke Johnston

> This is a simulated portfolio document. It demonstrates SAP structure, endpoint derivation, estimand thinking, ADaM traceability, TLF planning and QC expectations. It is not a real clinical-trial SAP.

## Key professional additions in this version

- Formal document-control table and simulated data cut-off/database-lock convention.
- Estimand table for the primary PFS treatment effect.
- Clear analysis-population definitions: Randomized Set, FAS, Safety Set and supportive response-evaluable set.
- PFS and OS censoring conventions.
- Multiplicity hierarchy and planned sensitivity analyses.
- Safety reporting rules for TEAE, serious AE, grade >=3 AE, discontinuation and lab shifts.
- Data standards, ADaM traceability and QC workflow.

## Core outputs

See `metadata/analysis_results_metadata.csv`, `metadata/source_to_adam_traceability.csv`, `outputs/reports/tlf_packet.pdf`, `outputs/reports/clinical_study_analysis_report.pdf`, and `outputs/reports/validation_report.pdf`.
"""


def create_csr_report() -> None:
    adsl, adtte, adae, adrs, adlb = load_outputs()
    pfs = pd.read_csv(OUT_TABLES / "t14_2_1_primary_pfs.csv", keep_default_na=False)
    os_ = pd.read_csv(OUT_TABLES / "t14_2_2_overall_survival.csv", keep_default_na=False)
    orr = pd.read_csv(OUT_TABLES / "t14_2_3_best_overall_response.csv", keep_default_na=False)
    safety = pd.read_csv(OUT_TABLES / "t14_3_1_safety_overview.csv", keep_default_na=False)
    demo = pd.read_csv(OUT_TABLES / "t14_1_1_demographics.csv", keep_default_na=False)
    disp = pd.read_csv(OUT_TABLES / "t14_1_2_disposition.csv", keep_default_na=False)
    exposure = pd.read_csv(OUT_TABLES / "t14_1_3_exposure.csv", keep_default_na=False)
    pdev = pd.read_csv(OUT_TABLES / "t14_1_4_major_protocol_deviations.csv", keep_default_na=False)

    n_t = int((adsl.TRT01P == ARM_T).sum())
    n_c = int((adsl.TRT01P == ARM_C).sum())
    n = len(adsl)
    pfs_hr = pfs.loc[pfs.iloc[:, 0] == "Cox HR, treatment vs control", pfs.columns[3]].iloc[0]
    os_hr = os_.loc[os_.iloc[:, 0] == "Cox HR, treatment vs control", os_.columns[3]].iloc[0]
    pfs_p = pfs.loc[pfs.iloc[:, 0] == "Log-rank test p-value", pfs.columns[3]].iloc[0]
    os_p = os_.loc[os_.iloc[:, 0] == "Log-rank test p-value", os_.columns[3]].iloc[0]
    orr_row = orr[orr.iloc[:,0].str.contains("Objective response", regex=False)].iloc[0]
    any_teae = safety.iloc[0].tolist()
    serious_teae = safety[safety.iloc[:,0].str.contains("serious", case=False)].iloc[0].tolist()
    g3_teae = safety[safety.iloc[:,0].str.contains("grade", case=False)].iloc[0].tolist()

    story = title_block("Clinical Study Analysis Report", "CSR-style statistical report - professional simulated version", REPORT_VERSION)
    story += [p("Executive synopsis", "H1")]
    syn = [
        ["Item", "Summary"],
        ["Study design", "Randomized, double-blind, controlled Phase III oncology simulation"],
        ["Subjects", f"{n} randomized: {n_t} ONC-305 + SOC and {n_c} Placebo + SOC"],
        ["Primary endpoint", "Progression-free survival in the FAS"],
        ["Primary result", f"PFS HR treatment vs control {pfs_hr}; log-rank p-value {pfs_p} in the simulated dataset"],
        ["Key secondary result", f"OS HR treatment vs control {os_hr}; log-rank p-value {os_p}; ORR {orr_row.iloc[1]} versus {orr_row.iloc[2]}"],
        ["Safety summary", f"Any TEAE: {any_teae[1]} versus {any_teae[2]}; serious TEAE: {serious_teae[1]} versus {serious_teae[2]}; grade >=3 TEAE: {g3_teae[1]} versus {g3_teae[2]}"],
        ["Interpretation", "The simulated treatment arm shows favorable efficacy patterns with manageable safety signals; no clinical claim is made because all data are synthetic"],
    ]
    story.append(table(syn, widths=[1.4*inch, 5.2*inch], font_size=7.4))
    story += [p("This report emulates the statistical-results style expected in a clinical study report. It deliberately includes document control, analysis populations, data standards, key efficacy and safety results, quality status and limitations.", "Callout")]

    story += [p("1. Study conduct and analysis sets", "H1")]
    story += bullets([
        f"Data cut-off: {DATA_CUTOFF}; simulated database lock: {DBL_DATE}.",
        "All randomized subjects are included in the Full Analysis Set. In this simulation, all randomized subjects received treatment and are included in the Safety Set.",
        "Treatment groups are balanced by design. Baseline characteristics and disposition are shown below, with full outputs in the TLF packet.",
    ], "Small")
    story.append(p("Disposition", "H2"))
    story.append(df_table(disp, font_size=6.8, total_width=6.6*inch, first_col=1.9*inch))
    story.append(Spacer(1, 6))
    story.append(p("Demographic summary excerpt", "H2"))
    story.append(df_table(demo.head(12), font_size=6.7, total_width=6.6*inch, first_col=2.0*inch))

    story += [p("2. Protocol deviations and data review", "H1")]
    story += bullets([
        "A realistic portfolio should include major deviation categories and a traceable data-review process, even when data are simulated.",
        "No potential unblinding events are represented in the mock data-review log. Deviation counts are included for demonstration only.",
    ], "Small")
    story.append(df_table(pdev, font_size=6.8, total_width=6.6*inch, first_col=2.4*inch))

    story += [p("3. Efficacy results", "H1")]
    story += [p("3.1 Primary endpoint: progression-free survival", "H2")]
    story += bullets([
        f"The simulated primary analysis favored ONC-305 + SOC, with Cox HR {pfs_hr} and log-rank p-value {pfs_p}.",
        "Kaplan-Meier medians and 6-, 12- and 18-month landmark estimates are reported by arm.",
        "The treatment effect is supported descriptively by the forest plot across multiple subgroups, although subgroup analyses are not confirmatory.",
    ], "Small")
    story.append(df_table(pfs, font_size=6.8, total_width=6.6*inch, first_col=2.1*inch))
    if (OUT_FIGURES / "f14_2_1_km_pfs.png").exists():
        story.append(Spacer(1, 5))
        story.append(Image(str(OUT_FIGURES / "f14_2_1_km_pfs.png"), width=6.3*inch, height=3.6*inch))
    story += [p("3.2 Overall survival and response", "H2")]
    story += bullets([
        f"The OS analysis favored ONC-305 + SOC in the simulated data, with Cox HR {os_hr} and log-rank p-value {os_p}.",
        f"ORR was {orr_row.iloc[1]} in the ONC-305 + SOC arm and {orr_row.iloc[2]} in the Placebo + SOC arm.",
    ], "Small")
    story.append(df_table(os_, font_size=6.8, total_width=6.6*inch, first_col=2.1*inch))
    story.append(Spacer(1, 6))
    story.append(df_table(orr, font_size=6.5, total_width=6.6*inch, first_col=1.7*inch))

    story += [p("4. Safety results", "H1")]
    story += bullets([
        "The Safety Set includes all treated subjects. TEAEs are summarized by subject incidence, not event count, unless explicitly indicated.",
        "The simulated ONC-305 + SOC arm has a higher incidence of any TEAE and treatment-related TEAE, consistent with an active treatment arm in an oncology study.",
        "Detailed SOC/PT, grade >=3, SAE, AE discontinuation and fatal AE outputs are included in the TLF and listing package.",
    ], "Small")
    story.append(df_table(safety, font_size=6.8, total_width=6.6*inch, first_col=2.2*inch))
    story.append(Spacer(1, 6))
    story.append(p("Exposure summary", "H2"))
    story.append(df_table(exposure, font_size=6.8, total_width=6.6*inch, first_col=2.0*inch))
    if (OUT_FIGURES / "f14_3_1_top_teae_bar.png").exists():
        story.append(Spacer(1, 5))
        story.append(Image(str(OUT_FIGURES / "f14_3_1_top_teae_bar.png"), width=6.3*inch, height=3.3*inch))

    story += [p("5. Data standards, traceability and validation status", "H1")]
    qc_df = pd.read_csv(QC / "validation_checks.csv", keep_default_na=False)
    tracker = pd.read_csv(QC / "program_validation_tracker.csv", keep_default_na=False)
    issue_log = pd.read_csv(QC / "data_review_issue_log.csv", keep_default_na=False)
    story += bullets([
        f"Automated validation status: {int((qc_df.Status == 'PASS').sum())} PASS, {int((qc_df.Status == 'WARN').sum())} WARN, {int((qc_df.Status == 'FAIL').sum())} FAIL across {len(qc_df)} checks.",
        "Analysis traceability is documented in analysis_results_metadata.csv and source_to_adam_traceability.csv.",
        "The package includes Python executable code, SAS/R templates, ADaM-style datasets, define-like metadata, TLF outputs and reviewer documentation.",
    ], "Small")
    story.append(p("Data review issue log", "H2"))
    story.append(df_table(issue_log, max_rows=10, font_size=6.3, total_width=6.6*inch, first_col=0.8*inch))
    story.append(Spacer(1, 6))
    story.append(p("Program validation tracker", "H2"))
    story.append(df_table(tracker, max_rows=12, font_size=6.3, total_width=6.6*inch, first_col=1.2*inch))

    story += [p("6. Discussion and portfolio conclusion", "H1")]
    story += bullets([
        "The end-to-end package demonstrates the path from protocol/SAP assumptions through analysis dataset derivation, TLF generation, quality checks and CSR-style reporting.",
        "The strongest job-relevant features are survival analysis, oncology endpoint conventions, ADaM traceability, TEAE reporting, reproducible programming and validation documentation.",
        "All efficacy and safety results are simulation artifacts and should only be evaluated as portfolio evidence of statistical and programming competence.",
    ], "Small")
    story += [p("Appendices in the repository", "H2")]
    story += bullets([
        "outputs/reports/tlf_packet.pdf - full tables/listings/figures packet.",
        "outputs/reports/adam_reviewer_guide.pdf - analysis dataset and traceability guide.",
        "outputs/reports/programming_qc_plan.pdf - validation strategy and programming plan.",
        "metadata/analysis_results_metadata.csv - result-level traceability map.",
        "metadata/source_to_adam_traceability.csv - variable-level source-to-analysis map.",
    ], "Small")

    md = f"""# {STUDY_ID} Clinical Study Analysis Report - Professional Simulated Version

Version: {REPORT_VERSION}  
Data cut-off: {DATA_CUTOFF}  
Database lock: {DBL_DATE}

## Executive synopsis

- {n} randomized subjects: {n_t} ONC-305 + SOC and {n_c} Placebo + SOC.
- Primary PFS: Cox HR {pfs_hr}; log-rank p-value {pfs_p}.
- Overall survival: Cox HR {os_hr}; log-rank p-value {os_p}.
- ORR: {orr_row.iloc[1]} versus {orr_row.iloc[2]}.
- Automated validation: {int((qc_df.Status == 'PASS').sum())} PASS, {int((qc_df.Status == 'WARN').sum())} WARN, {int((qc_df.Status == 'FAIL').sum())} FAIL.

This is a simulated CSR-style statistical report. It is designed to demonstrate clinical-trial biostatistics, not to support a clinical claim.
"""
    (OUT_REPORTS / "clinical_study_analysis_report.md").write_text(md, encoding="utf-8")
    pdf(OUT_REPORTS / "clinical_study_analysis_report.pdf", "CSR-style Report", story)


def create_reviewer_guide() -> None:
    adsl, adtte, adae, adrs, adlb = load_outputs()
    meta = pd.read_csv(ROOT / "metadata" / "analysis_results_metadata.csv")
    trace = pd.read_csv(ROOT / "metadata" / "source_to_adam_traceability.csv")
    spec = pd.read_csv(DATA_SPECS / "adam_spec.csv")
    story = title_block("ADaM Reviewer Guide", "Dataset, metadata and traceability guide", "1.0")
    story += [p("Purpose", "H1")]
    story += bullets([
        "Give a reviewer or recruiter a fast map of the analysis datasets, key derivations and output traceability.",
        "Show understanding of how ADaM-style datasets support efficient generation, replication and review of clinical trial analyses.",
        "Make the project easier to audit during an interview: each key output points back to a source dataset, method and program.",
    ], "Small")
    dataset_summary = [
        ["Dataset", "Rows", "Role", "Key contents"],
        ["ADSL", len(adsl), "Subject-level analysis", "Treatment, dates, demographics, flags, exposure"],
        ["ADTTE", len(adtte), "Time-to-event", "PFS and OS AVAL/CNSR records"],
        ["ADRS", len(adrs), "Response", "BOR, ORR, DCR, tumor-change variables"],
        ["ADAE", len(adae), "Safety events", "TEAE flags, SOC/PT, grade, seriousness, relationship"],
        ["ADLB", len(adlb), "Laboratory", "Baseline and worst grade shifts"],
    ]
    story.append(table(dataset_summary, widths=[0.9*inch, 0.6*inch, 1.4*inch, 3.9*inch], font_size=7.3))
    story += [p("Source-to-analysis traceability excerpt", "H1")]
    story.append(df_table(trace, max_rows=16, font_size=6.5, total_width=6.8*inch, first_col=0.8*inch))
    story += [p("Analysis results metadata excerpt", "H1")]
    story.append(df_table(meta, max_rows=16, font_size=6.3, total_width=6.8*inch, first_col=0.7*inch))
    story += [p("ADaM specification excerpt", "H1")]
    cols = [c for c in ["Dataset", "Variable", "Label", "Type", "Derivation"] if c in spec.columns]
    story.append(df_table(spec[cols].head(30), max_rows=30, font_size=6.2, total_width=6.8*inch, first_col=0.75*inch))
    story += [p("Known limitations", "H1")]
    story += bullets([
        "CSV files are used for portability in this environment. The repository includes an optional R template to export XPT transport files if local dependencies are available.",
        "The data are simulated and do not represent a real product, sponsor, patient population or regulatory submission.",
        "SAS programs are included as realistic templates but are not executed in this Python-based build environment.",
    ], "Small")
    (DOCS / "adam_reviewer_guide.md").write_text("# ADaM Reviewer Guide\n\nSee `outputs/reports/adam_reviewer_guide.pdf` and the CSV traceability files in `metadata/`.\n", encoding="utf-8")
    pdf(OUT_REPORTS / "adam_reviewer_guide.pdf", "ADaM Reviewer Guide", story)


def create_qc_plan() -> None:
    qc = pd.read_csv(QC / "validation_checks.csv", keep_default_na=False)
    tracker = pd.read_csv(QC / "program_validation_tracker.csv", keep_default_na=False)
    story = title_block("Programming and QC Plan", "Reproducibility, validation and programming standards", "1.0")
    story += [p("1. Programming model", "H1")]
    story += bullets([
        "The portfolio follows a clinical-trial programming flow: source data, ADaM-style derivation, TLF generation, validation checks, and report rendering.",
        "Each output has a program owner and traceability to source datasets and methods.",
        "The repository is designed so a recruiter can run one command and regenerate the package.",
    ], "Small")
    story += [p("2. Validation strategy", "H1")]
    strategy = [
        ["Area", "Primary checks", "Evidence"],
        ["Population counts", "ADSL counts by arm and flags; FAS/SAF consistency", "validation_checks.csv"],
        ["Endpoint integrity", "PFS/OS record count, CNSR values, positive AVAL, event/censor definitions", "ADTTE + TLF checks"],
        ["Safety chronology", "AE start/end dates, treatment-emergent flags, toxicity-grade range", "ADAE checks"],
        ["Output production", "Expected tables, listings, figures and reports exist", "Output existence checks"],
        ["Metadata", "ADaM specification and define-like XML are generated", "data/specs"],
        ["Visual review", "PDFs rendered and inspected for clipping/overlap", "Rendered preview assets"],
    ]
    story.append(table(strategy, widths=[1.3*inch, 3.2*inch, 1.9*inch], font_size=7.3))
    story += [p("3. Program validation tracker", "H1")]
    story.append(df_table(tracker, font_size=6.4, total_width=6.6*inch, first_col=1.2*inch))
    story += [p("4. Automated validation check summary", "H1")]
    story.append(p(f"Current run: {int((qc.Status == 'PASS').sum())} PASS, {int((qc.Status == 'WARN').sum())} WARN, {int((qc.Status == 'FAIL').sum())} FAIL across {len(qc)} checks.", "Callout"))
    story.append(df_table(qc, max_rows=40, font_size=6.2, total_width=6.6*inch, first_col=1.2*inch))
    story += [p("5. How this mirrors regulated work", "H1")]
    story += bullets([
        "The primary analysis is not just a model output; it is tied to a SAP, analysis population, endpoint definition, TLF, source dataset and QC check.",
        "The project distinguishes executable implementation from SAS/R templates, avoiding overstating unexecuted code.",
        "Reviewer-facing artifacts make the repository easier to inspect in an interview and closer to what pharma teams expect from analysis packages.",
    ], "Small")
    (DOCS / "programming_qc_plan.md").write_text("# Programming and QC Plan\n\nSee `outputs/reports/programming_qc_plan.pdf` and QC artifacts in `qc/`.\n", encoding="utf-8")
    pdf(OUT_REPORTS / "programming_qc_plan.pdf", "Programming QC Plan", story)


def create_tlf_shell_book() -> None:
    meta = pd.read_csv(ROOT / "metadata" / "analysis_results_metadata.csv")
    story = title_block("TLF Shell Book", "Mock shells and output metadata", "1.0")
    story += [p("Output index", "H1")]
    story.append(df_table(meta[["Result ID", "Title", "Source", "Population", "Output"]], max_rows=40, font_size=6.5, total_width=6.8*inch, first_col=0.7*inch))
    story += [p("Representative TLF shell conventions", "H1")]
    shell = [
        ["Element", "Convention"],
        ["Title", "Table/Figure/Listing number, concise endpoint/population description"],
        ["Population line", "Always state FAS, Safety Set or other denominator"],
        ["Arm columns", "Treatment arm columns include N in header"],
        ["Counts", "n (%) unless explicitly an event count"],
        ["Time-to-event", "Events, censoring, median, 95% CI, landmark estimates and model summary"],
        ["AE outputs", "Count each subject once per category; include SOC/PT and maximum grade rules"],
        ["Footnotes", "Source dataset, derivation method, censoring rule and simulation caveat"],
    ]
    story.append(table(shell, widths=[1.4*inch, 5.2*inch], font_size=7.3))
    story += [p("Mock shell: T14.2.1 Primary PFS", "H2")]
    pfs_shell = [
        ["Analysis", f"{ARM_T} (N=xxx)", f"{ARM_C} (N=xxx)", "Treatment comparison"],
        ["Events, n (%)", "xx (xx.x%)", "xx (xx.x%)", ""],
        ["Median PFS, months (95% CI)", "xx.x (xx.x, xx.x)", "xx.x (xx.x, xx.x)", ""],
        ["6-month KM rate", "xx.x%", "xx.x%", ""],
        ["12-month KM rate", "xx.x%", "xx.x%", ""],
        ["Cox HR (95% CI)", "", "", "x.xx (x.xx, x.xx)"],
        ["Log-rank p-value", "", "", "x.xxx"],
    ]
    story.append(table(pfs_shell, widths=[2.0*inch, 1.5*inch, 1.5*inch, 1.6*inch], font_size=7.1))
    story += [p("Mock shell: T14.3.2 TEAE by SOC/PT", "H2")]
    ae_shell = [
        ["SOC / Preferred term", f"{ARM_T} (N=xxx)", f"{ARM_C} (N=xxx)", "Total (N=xxx)"],
        ["Any TEAE", "xx (xx.x%)", "xx (xx.x%)", "xx (xx.x%)"],
        ["SYSTEM ORGAN CLASS", "xx (xx.x%)", "xx (xx.x%)", "xx (xx.x%)"],
        ["  Preferred term", "xx (xx.x%)", "xx (xx.x%)", "xx (xx.x%)"],
    ]
    story.append(table(ae_shell, widths=[2.4*inch, 1.5*inch, 1.5*inch, 1.5*inch], font_size=7.1))
    story += [p("Full realized outputs", "H1")]
    story += bullets([
        "Realized CSV/MD/TXT tables are stored under outputs/tables.",
        "Listings are stored under outputs/listings.",
        "Figures are stored under outputs/figures as PNG and PDF.",
        "The combined TLF packet is outputs/reports/tlf_packet.pdf.",
    ], "Small")
    (DOCS / "tlf_shell_book.md").write_text("# TLF Shell Book\n\nSee `outputs/reports/tlf_shell_book.pdf`.\n", encoding="utf-8")
    pdf(OUT_REPORTS / "tlf_shell_book.pdf", "TLF Shell Book", story)


def create_recruiter_summary() -> None:
    qc = pd.read_csv(QC / "validation_checks.csv", keep_default_na=False)
    pfs = pd.read_csv(OUT_TABLES / "t14_2_1_primary_pfs.csv", keep_default_na=False)
    os_ = pd.read_csv(OUT_TABLES / "t14_2_2_overall_survival.csv", keep_default_na=False)
    pfs_hr = pfs.loc[pfs.iloc[:, 0] == "Cox HR, treatment vs control", pfs.columns[3]].iloc[0]
    os_hr = os_.loc[os_.iloc[:, 0] == "Cox HR, treatment vs control", os_.columns[3]].iloc[0]
    story = title_block("Recruiter Portfolio Summary", "What this project demonstrates for biostatistician/statistical-programmer roles", "1.0")
    story += [p("Why this project stands out", "H1")]
    story += bullets([
        "It is not just a survival-analysis notebook: it is an end-to-end analysis package with SAP, CSR-style report, ADaM-style datasets, TLFs, validation and reviewer documentation.",
        "It demonstrates oncology-specific endpoints: PFS, OS, ORR, DCR, TEAEs, grade >=3 TEAEs, serious AEs, discontinuations and laboratory shifts.",
        "It proves reproducibility: a single command regenerates data, analysis datasets, outputs and reports.",
        "It shows communication skill: technical analyses are packaged into documents that a statistician, statistical programmer, clinical reviewer or recruiter can understand.",
    ], "Small")
    highlights = [
        ["Capability", "Evidence in repository"],
        ["Protocol/SAP thinking", "Professional SAP with estimand, endpoints, censoring, populations and multiplicity"],
        ["Survival analysis", f"PFS and OS KM/log-rank/Cox outputs; PFS HR {pfs_hr}; OS HR {os_hr}"],
        ["Oncology safety", "TEAE by SOC/PT, grade >=3, SAE, discontinuation, fatal event and lab-shift outputs"],
        ["ADaM/CDISC awareness", "ADSL, ADTTE, ADRS, ADAE, ADLB, define-like XML and traceability matrix"],
        ["Validation", f"{int((qc.Status == 'PASS').sum())} PASS / {int((qc.Status == 'WARN').sum())} WARN / {int((qc.Status == 'FAIL').sum())} FAIL QC status"],
        ["Programming", "Python executable pipeline plus SAS/R templates for regulated-workflow discussion"],
    ]
    story.append(table(highlights, widths=[1.5*inch, 5.1*inch], font_size=7.3))
    story += [p("CV bullets", "H1")]
    story += bullets([
        "Built a simulated Phase III oncology statistical-submission portfolio with professional SAP, CSR-style statistical report, ADaM-style ADSL/ADTTE/ADAE/ADRS/ADLB datasets, TLFs, listings, figures, validation report, reviewer guide and reproducible Python/SAS/R programming structure.",
        "Implemented PFS/OS Kaplan-Meier, log-rank and Cox analyses; ORR/DCR exact-CI response summaries; exposure, disposition, protocol-deviation, TEAE, SAE, grade >=3 AE, AE-discontinuation and laboratory-shift outputs.",
        "Created analysis results metadata, source-to-ADaM traceability, define-like metadata, QC issue log and program validation tracker to mirror regulated pharma analysis workflows.",
    ], "Small")
    story += [p("Interview explanation", "H1")]
    story += bullets([
        "I designed the portfolio to show I understand the whole chain from protocol question to SAP, estimand, ADaM derivation, TLF production, validation and reporting.",
        "The project is intentionally simulated, so it avoids patient data while still letting me demonstrate clinical-trial reasoning and programming discipline.",
        "I can discuss both the statistical methods and the operational workflow: derivations, flags, denominators, censoring, subject-level AE counting, QC and traceability.",
    ], "Small")
    pdf(OUT_REPORTS / "recruiter_portfolio_summary.pdf", "Recruiter Summary", story)


def create_bdr_memo() -> None:
    issue = pd.read_csv(QC / "data_review_issue_log.csv", keep_default_na=False)
    story = title_block("Blinded Data Review Memo", "Mock pre-database-lock review artifact", "1.0")
    story += [p("Purpose", "H1")]
    story += bullets([
        "Demonstrate awareness that statistical outputs are only credible after data review, endpoint rules and programming assumptions have been checked.",
        "Summarize data issues, endpoint conventions, protocol deviations and readiness for final TLF generation.",
        "In a real study this would be prepared before unblinding; this simulated package is already unblinded, so the memo is included as a workflow artifact only.",
    ], "Small")
    story += [p("Data review issue log", "H1")]
    story.append(df_table(issue, font_size=6.4, total_width=6.6*inch, first_col=0.8*inch))
    story += [p("Database-lock readiness checklist", "H1")]
    checklist = [
        ["Checklist item", "Status"],
        ["Randomization and treatment-arm counts reconciled", "Complete"],
        ["FAS and Safety Set flags confirmed", "Complete"],
        ["PFS/OS endpoint records present for all subjects", "Complete"],
        ["AE chronology and toxicity-grade checks completed", "Complete"],
        ["Response categories mapped to ORR/DCR flags", "Complete"],
        ["ADaM metadata and define-like XML generated", "Complete"],
        ["TLF and validation package generated", "Complete"],
    ]
    story.append(table(checklist, widths=[4.8*inch, 1.8*inch], font_size=7.4))
    pdf(OUT_REPORTS / "blinded_data_review_memo.pdf", "BDR Memo", story)


def create_github_guide() -> None:
    guide = """# How to put this portfolio on GitHub

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
"""
    (DOCS / "github_upload_guide.md").write_text(guide, encoding="utf-8")


def update_readme() -> None:
    readme = f"""# Simulated Phase III Oncology Statistical Submission Portfolio

**Study:** {STUDY_ID}, a simulated randomized Phase III oncology study comparing `ONC-305 + SOC` with `Placebo + SOC` in advanced solid tumors.

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
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python programs/python/run_all.py
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

## Suggested CV bullet

> Built a simulated Phase III oncology statistical-submission portfolio with professional SAP, CSR-style report, ADaM-style ADSL/ADTTE/ADAE/ADRS/ADLB datasets, TLFs, listings, figures, validation report, reviewer guide, traceability metadata and reproducible Python/SAS/R programming structure.

## Important disclaimer

All data are synthetic. This is not a real clinical trial, not a regulatory submission, not clinical evidence and not endorsed by any sponsor, regulator or standards organization. The repository is a portfolio demonstration of biostatistics and statistical-programming competence.

## GitHub setup guide

See `docs/github_upload_guide.md`.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def update_sas_templates() -> None:
    sas_dir = ROOT / "programs" / "sas"
    sas_dir.mkdir(parents=True, exist_ok=True)
    (sas_dir / "README.md").write_text("""# SAS templates

These files are recruiter-facing regulated-workflow templates. They are not executed by the Python build environment. Use them to discuss how the analysis would map into a SAS-based CRO/pharma programming workflow.

Suggested local extension: run analogous PROC LIFETEST, PROC PHREG and PROC REPORT programs in SAS OnDemand or a licensed SAS environment, then add log files and validation notes.
""", encoding="utf-8")
    (sas_dir / "macros_study_templates.sas").write_text(r"""
/* ---------------------------------------------------------------------------
   ONC-305-301 SAS template macros
   Purpose: show regulated-workflow thinking for TLF generation.
   Note: Template only; not executed in the Python build environment.
--------------------------------------------------------------------------- */

%macro count_pct(data=, class=, trt=TRT01P, out=);
    proc sql;
        create table &out as
        select &class,
               &trt,
               count(distinct USUBJID) as n
        from &data
        group by &class, &trt;
    quit;
%mend;

%macro km_phreg(data=adtte, paramcd=PFS, out=);
    data _tte;
        set &data;
        where PARAMCD="&paramcd" and ANL01FL="Y";
        event = 1 - CNSR;
    run;

    proc lifetest data=_tte plots=survival;
        time AVAL*CNSR(1);
        strata TRT01P;
    run;

    proc phreg data=_tte;
        class TRT01P(ref="Placebo + SOC") ECOG PDL1CAT / param=ref;
        model AVAL*CNSR(1) = TRT01P ECOG PDL1CAT / ties=efron;
        ods output ParameterEstimates=&out;
    run;
%mend;

%macro teae_socpt(data=adae, out=);
    data _teae;
        set &data;
        where SAFFL="Y" and TRTEMFL="Y";
    run;
    proc sql;
        create table &out as
        select AEBODSYS, AEDECOD, TRT01P, count(distinct USUBJID) as subjects
        from _teae
        group by AEBODSYS, AEDECOD, TRT01P;
    quit;
%mend;
""", encoding="utf-8")


def update_run_all() -> None:
    run_path = ROOT / "programs" / "python" / "run_all.py"
    txt = run_path.read_text(encoding="utf-8")
    if "render_professional_package" not in txt:
        txt = txt.replace("from render_reports import render_all_reports\n", "from render_reports import render_all_reports\nfrom render_professional_package import render_professional_package\n")
        txt = txt.replace("    render_all_reports()\n", "    render_all_reports()\n    render_professional_package()\n")
        txt = txt.replace("Pipeline complete. Review docs/, data/adam/, outputs/, and qc/.", "Pipeline complete. Review docs/, data/adam/, outputs/, qc/, and metadata/.")
        run_path.write_text(txt, encoding="utf-8")


def create_preview_assets() -> None:
    # Lightweight README preview assets copied from generated figures.
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    for src, dst in [
        (OUT_FIGURES / "f14_2_1_km_pfs.png", assets / "preview_km_pfs.png"),
        (OUT_FIGURES / "f14_2_3_pfs_forest.png", assets / "preview_pfs_forest.png"),
        (OUT_FIGURES / "f14_3_1_top_teae_bar.png", assets / "preview_top_teae.png"),
    ]:
        if src.exists():
            dst.write_bytes(src.read_bytes())


def render_professional_package() -> None:
    ensure_dirs()
    (ROOT / "metadata").mkdir(exist_ok=True)
    adsl, *_ = load_outputs()
    make_protocol_deviation_table(adsl)
    build_metadata_artifacts()
    create_sap()
    create_csr_report()
    create_reviewer_guide()
    create_qc_plan()
    create_tlf_shell_book()
    create_recruiter_summary()
    create_bdr_memo()
    create_github_guide()
    update_readme()
    update_sas_templates()
    update_run_all()
    create_preview_assets()
    print("Rendered professional SAP, CSR-style report, reviewer guide, QC plan, TLF shell book, recruiter summary, and GitHub guide.")


if __name__ == "__main__":
    render_professional_package()
