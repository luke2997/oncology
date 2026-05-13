from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils import (
    ARM_C,
    ARM_T,
    ARMS,
    DATA_ADAM,
    DATA_RAW,
    DATA_SPECS,
    DOCS,
    OUT_FIGURES,
    OUT_LISTINGS,
    OUT_REPORTS,
    OUT_TABLES,
    QC,
    STUDY_ID,
    TOTAL,
    cox_ph,
    ensure_dirs,
    fmt_p,
    km_curve,
    logrank_test,
)

PORTFOLIO_VERSION = "2.0"
GEN_DATE = date.today().isoformat()
SPONSOR = "Simulated Sponsor Ltd."
INDICATION = "Advanced/metastatic solid tumours"
PRODUCT = "ONC-305 + standard of care"
CONTROL = "Placebo + standard of care"


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=18, leading=22, spaceAfter=12))
    styles.add(ParagraphStyle(name="DocSubtitle", parent=styles["BodyText"], alignment=TA_CENTER, fontSize=10.5, leading=13, spaceAfter=8))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], fontSize=13.5, leading=17, spaceBefore=10, spaceAfter=7, textColor=colors.HexColor("#16365C")))
    styles.add(ParagraphStyle(name="Subsection", parent=styles["Heading2"], fontSize=10.8, leading=13.5, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#1F4E79")))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=8.9, leading=11.4, spaceAfter=4))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=7.6, leading=9.4, spaceAfter=3))
    styles.add(ParagraphStyle(name="Tiny", parent=styles["BodyText"], fontSize=6.4, leading=7.8))
    styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=6.8, leading=8.2))
    styles.add(ParagraphStyle(name="CellSmall", parent=styles["BodyText"], fontSize=6.0, leading=7.0))
    styles.add(ParagraphStyle(name="Note", parent=styles["BodyText"], fontSize=7.5, leading=9.0, textColor=colors.HexColor("#444444")))
    styles.add(ParagraphStyle(name="Right", parent=styles["BodyText"], alignment=TA_RIGHT, fontSize=8, leading=10))
    return styles


def _safe(text: object) -> str:
    # ReportLab paragraph XML parser is fragile; keep the documents ASCII-friendly.
    txt = "" if text is None else str(text)
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00a0": " ",
        "\u03b1": "alpha",
        "\u03b2": "beta",
    }
    for k, v in replacements.items():
        txt = txt.replace(k, v)
    return escape(txt).replace("\n", "<br/>")


def para(text: object, style_name: str = "Body") -> Paragraph:
    return Paragraph(_safe(text), _styles()[style_name])


def bullet_list(items: list[str], style_name: str = "Body") -> list:
    return [Paragraph("&bull; " + _safe(item), _styles()[style_name]) for item in items]


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.4)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(doc.leftMargin, 0.38 * inch, f"{STUDY_ID} | simulated portfolio | generated {GEN_DATE} | not for clinical decision-making")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(path: Path, flowables: list, landscape_page: bool = False, top_margin: float = 0.55, bottom_margin: float = 0.65) -> None:
    page_size = landscape(LETTER) if landscape_page else LETTER
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=page_size,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=top_margin * inch,
        bottomMargin=bottom_margin * inch,
    )
    doc.build(flowables, onFirstPage=_footer, onLaterPages=_footer)


def title_block(document_title: str, subtitle: str | None = None, version: str = PORTFOLIO_VERSION) -> list:
    flow = [para(STUDY_ID, "DocTitle"), para(document_title, "DocTitle")]
    if subtitle:
        flow.append(para(subtitle, "DocSubtitle"))
    flow.append(Spacer(1, 6))
    meta = pd.DataFrame(
        [
            ["Sponsor", SPONSOR],
            ["Study phase", "Phase III (simulated)"],
            ["Investigational product", PRODUCT],
            ["Control", CONTROL],
            ["Indication", INDICATION],
            ["Document version", version],
            ["Generation date", GEN_DATE],
            ["Data source", "Fully synthetic patient-level data; no real patient data or clinical evidence"],
        ],
        columns=["Item", "Value"],
    )
    flow.append(df_table(meta, font_size=7.5, first_col_width=1.8 * inch, total_width=6.9 * inch, header=True))
    flow.append(Spacer(1, 12))
    flow.append(para("Confidentiality and simulation notice", "Subsection"))
    flow.append(para("This portfolio is a professional demonstration of clinical-trial statistics and statistical-programming capability. It is deliberately structured like a small sponsor/CRO submission package, but all data and conclusions are simulated and must not be interpreted as clinical evidence.", "Small"))
    flow.append(Spacer(1, 8))
    return flow


def df_table(
    df: pd.DataFrame,
    max_rows: int | None = None,
    font_size: float = 6.8,
    first_col_width: float = 2.2 * inch,
    total_width: float = 7.0 * inch,
    header: bool = True,
    style_name: str = "Cell",
) -> Table:
    styles = _styles()
    df2 = df.copy()
    if max_rows is not None and len(df2) > max_rows:
        df2 = df2.head(max_rows).copy()
        df2.loc[len(df2)] = ["... full output provided in CSV/MD/TXT files"] + ["" for _ in range(max(0, df2.shape[1] - 1))]
    data = []
    if header:
        data.append([Paragraph(_safe(c), styles[style_name]) for c in df2.columns])
    for _, row in df2.iterrows():
        data.append([Paragraph(_safe(v), styles[style_name]) for v in row.tolist()])
    ncols = max(1, df2.shape[1])
    if ncols == 1:
        widths = [total_width]
    elif ncols == 2:
        widths = [first_col_width, total_width - first_col_width]
    else:
        remaining = max(total_width - first_col_width, 1.0 * inch)
        widths = [first_col_width] + [remaining / (ncols - 1)] * (ncols - 1)
    tbl = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E2F3")),
        ("FONT", (0, 0), (-1, -1), "Helvetica", font_size),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", font_size),
        ])
    tbl.setStyle(TableStyle(style))
    return tbl


def read_table(stem: str) -> pd.DataFrame:
    return pd.read_csv(OUT_TABLES / f"{stem}.csv", keep_default_na=False)


def _write_md(path: Path, sections: list[tuple[str, str | pd.DataFrame]]) -> None:
    lines = []
    for title, content in sections:
        lines.append(f"## {title}")
        lines.append("")
        if isinstance(content, pd.DataFrame):
            try:
                lines.append(content.to_markdown(index=False))
            except Exception:
                lines.append(content.to_csv(index=False))
        else:
            lines.append(str(content))
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def rmst_months(time: np.ndarray, event: np.ndarray, tau: float = 12.0) -> float:
    curve = km_curve(time, event)
    curve = curve.sort_values("time")
    last_t = 0.0
    surv = 1.0
    area = 0.0
    for _, row in curve.iterrows():
        t = float(row["time"])
        if t <= 0:
            surv = float(row["survival"])
            continue
        if t >= tau:
            area += max(0.0, tau - last_t) * surv
            return float(area)
        area += max(0.0, t - last_t) * surv
        surv = float(row["survival"])
        last_t = t
    if last_t < tau:
        area += (tau - last_t) * surv
    return float(area)


def get_key_results() -> dict[str, str]:
    adsl = pd.read_csv(DATA_ADAM / "adsl.csv")
    pfs = read_table("t14_2_1_primary_pfs")
    os_ = read_table("t14_2_2_overall_survival")
    orr = read_table("t14_2_3_best_overall_response")
    safety = read_table("t14_3_1_safety_overview")
    n_t = int((adsl.TRT01P == ARM_T).sum())
    n_c = int((adsl.TRT01P == ARM_C).sum())
    pfs_hr = pfs.loc[pfs.iloc[:, 0] == "Cox HR, treatment vs control", pfs.columns[-1]].iloc[0]
    pfs_p = pfs.loc[pfs.iloc[:, 0] == "Log-rank test p-value", pfs.columns[-1]].iloc[0]
    os_hr = os_.loc[os_.iloc[:, 0] == "Cox HR, treatment vs control", os_.columns[-1]].iloc[0]
    os_p = os_.loc[os_.iloc[:, 0] == "Log-rank test p-value", os_.columns[-1]].iloc[0]
    pfs_med_t = pfs.iloc[0, 3]
    pfs_med_c = pfs.iloc[1, 3]
    os_med_t = os_.iloc[0, 3]
    os_med_c = os_.iloc[1, 3]
    orr_row = orr[orr.iloc[:, 0].astype(str).str.contains("Objective response", regex=False)].iloc[0]
    any_teae = safety[safety.iloc[:, 0] == "Any TEAE"].iloc[0]
    grade3 = safety[safety.iloc[:, 0] == "Any grade >=3 TEAE"].iloc[0]
    return {
        "n_total": str(len(adsl)),
        "n_t": str(n_t),
        "n_c": str(n_c),
        "pfs_hr": str(pfs_hr),
        "pfs_p": str(pfs_p),
        "pfs_med_t": str(pfs_med_t),
        "pfs_med_c": str(pfs_med_c),
        "os_hr": str(os_hr),
        "os_p": str(os_p),
        "os_med_t": str(os_med_t),
        "os_med_c": str(os_med_c),
        "orr_t": str(orr_row.iloc[1]),
        "orr_c": str(orr_row.iloc[2]),
        "any_teae_t": str(any_teae.iloc[1]),
        "any_teae_c": str(any_teae.iloc[2]),
        "grade3_t": str(grade3.iloc[1]),
        "grade3_c": str(grade3.iloc[2]),
    }


def create_professional_spec_tables() -> None:
    """Create extra sponsor/CRO-style planning artifacts that recruiters can inspect."""
    ensure_dirs()
    adsl = pd.read_csv(DATA_ADAM / "adsl.csv")
    adtte = pd.read_csv(DATA_ADAM / "adtte.csv")
    adae = pd.read_csv(DATA_ADAM / "adae.csv")
    adrs = pd.read_csv(DATA_ADAM / "adrs.csv")
    adlb = pd.read_csv(DATA_ADAM / "adlb.csv")

    analysis_sets = pd.DataFrame([
        ["Randomized Set", "All randomized subjects", "Summaries of randomization and disposition", "According to randomized treatment"],
        ["Full Analysis Set (FAS/ITT)", "All randomized subjects", "Primary efficacy, OS, response, subgroups", "According to randomized treatment"],
        ["Safety Set", "All subjects receiving at least one dose", "Exposure, adverse events and laboratory summaries", "According to actual treatment received"],
        ["Response-Evaluable Set", "FAS subjects with baseline measurable disease and at least one post-baseline disease assessment or early progression/death", "Supportive response analyses", "According to randomized treatment"],
    ], columns=["Analysis set", "Definition", "Use", "Treatment assignment"])
    analysis_sets.to_csv(OUT_TABLES / "analysis_population_definitions.csv", index=False)

    estimands = pd.DataFrame([
        ["Primary", "Progression-free survival", "FAS adults with advanced/metastatic solid tumours", "Randomized ONC-305 + SOC vs randomized placebo + SOC", "Time from randomization to first progression or death", "Treatment discontinuation: treatment-policy; new anti-cancer therapy before progression: censor at last adequate assessment; missed assessment: censor or event according to SAP rules", "Hazard ratio from Cox model; two-sided log-rank p-value; KM medians/rates"],
        ["Key secondary", "Overall survival", "FAS", "Randomized ONC-305 + SOC vs randomized placebo + SOC", "Time from randomization to death from any cause", "Treatment discontinuation/new therapy: treatment-policy; lost-to-follow-up: censor at last known alive date", "Hazard ratio from Cox model; KM medians/rates"],
        ["Key secondary", "Objective response rate", "FAS with response assessment", "Randomized ONC-305 + SOC vs randomized placebo + SOC", "Best overall response of CR or PR", "Missing/non-evaluable response: non-responder in primary response summary", "Risk difference/ratio and exact 95% CIs; descriptive in this portfolio"],
        ["Safety", "Treatment-emergent adverse events", "Safety Set", "Actual ONC-305 + SOC vs actual placebo + SOC", "TEAEs from first dose through 30 days after last dose", "Events after treatment discontinuation included if treatment-emergent; recurrent events counted once per subject per summary level unless otherwise specified", "Subject incidence n (%) and exposure-adjusted event rates"],
    ], columns=["Family", "Estimand", "Population", "Treatment condition", "Variable", "Intercurrent event strategy", "Population-level summary"])
    estimands.to_csv(OUT_TABLES / "estimand_framework.csv", index=False)

    censoring = pd.DataFrame([
        ["PFS", "Progression or death documented after randomization", "Event", "Event date"],
        ["PFS", "No progression/death by data cutoff", "Censored", "Last adequate tumor assessment"],
        ["PFS", "New anti-cancer therapy before progression/death", "Censored", "Last adequate assessment before new therapy"],
        ["PFS", "Progression/death after two or more missed visits", "Censored in primary analysis", "Last adequate assessment before missed visits"],
        ["OS", "Death from any cause", "Event", "Death date"],
        ["OS", "Alive at data cutoff or lost to follow-up", "Censored", "Last date known alive"],
    ], columns=["Endpoint", "Scenario", "Outcome", "Analysis date"])
    censoring.to_csv(OUT_TABLES / "endpoint_censoring_rules.csv", index=False)

    multiplicity = pd.DataFrame([
        ["1", "PFS", "Two-sided alpha=0.05", "If statistically significant, proceed to OS"],
        ["2", "OS", "Two-sided alpha=0.05 conditional on PFS", "If statistically significant, proceed to ORR"],
        ["3", "ORR", "Two-sided alpha=0.05 conditional on PFS and OS", "Descriptive if hierarchy stops earlier"],
        ["Exploratory", "Subgroups, safety, exposure, laboratory shifts", "No multiplicity adjustment", "Interpret as descriptive and hypothesis-generating"],
    ], columns=["Order", "Endpoint family", "Type I error control", "Decision rule"])
    multiplicity.to_csv(OUT_TABLES / "multiplicity_strategy.csv", index=False)

    data_flow = pd.DataFrame([
        ["Raw/simulated", "DM", len(pd.read_csv(DATA_RAW / "dm.csv")), pd.read_csv(DATA_RAW / "dm.csv").shape[1], "Demography, randomization, baseline and treatment dates"],
        ["Raw/simulated", "TTE", len(pd.read_csv(DATA_RAW / "tte.csv")), pd.read_csv(DATA_RAW / "tte.csv").shape[1], "Progression-free survival and overall survival source"],
        ["Raw/simulated", "RS", len(pd.read_csv(DATA_RAW / "rs.csv")), pd.read_csv(DATA_RAW / "rs.csv").shape[1], "Best overall response and tumor change source"],
        ["Raw/simulated", "AE", len(pd.read_csv(DATA_RAW / "ae.csv")), pd.read_csv(DATA_RAW / "ae.csv").shape[1], "Adverse event source"],
        ["Raw/simulated", "LB", len(pd.read_csv(DATA_RAW / "lb.csv")), pd.read_csv(DATA_RAW / "lb.csv").shape[1], "Laboratory grade shifts source"],
        ["ADaM-style", "ADSL", len(adsl), adsl.shape[1], "Subject-level analysis dataset"],
        ["ADaM-style", "ADTTE", len(adtte), adtte.shape[1], "Time-to-event analysis dataset"],
        ["ADaM-style", "ADAE", len(adae), adae.shape[1], "Adverse event analysis dataset"],
        ["ADaM-style", "ADRS", len(adrs), adrs.shape[1], "Response analysis dataset"],
        ["ADaM-style", "ADLB", len(adlb), adlb.shape[1], "Laboratory analysis dataset"],
    ], columns=["Layer", "Dataset", "Rows", "Variables", "Purpose"])
    data_flow.to_csv(OUT_TABLES / "data_flow_summary.csv", index=False)

    # PFS sensitivity table: Cox/log-rank already in outputs, plus RMST through 12 months.
    pfs = adtte[adtte.PARAMCD == "PFS"].copy()
    g = (pfs.TRT01P == ARM_T).astype(int).to_numpy()
    cox = cox_ph(pfs.AVAL.to_numpy(), (1 - pfs.CNSR).to_numpy(), g)
    chi2, lr_p = logrank_test(pfs.AVAL.to_numpy(), (1 - pfs.CNSR).to_numpy(), g)
    rmst_t = rmst_months(pfs[pfs.TRT01P == ARM_T].AVAL.to_numpy(), (1 - pfs[pfs.TRT01P == ARM_T].CNSR).to_numpy(), tau=12.0)
    rmst_c = rmst_months(pfs[pfs.TRT01P == ARM_C].AVAL.to_numpy(), (1 - pfs[pfs.TRT01P == ARM_C].CNSR).to_numpy(), tau=12.0)
    pfs_sens = pd.DataFrame([
        ["Primary Cox PH", "Unstratified Cox model with treatment as covariate", f"HR {cox['hr']:.2f} ({cox['lcl']:.2f}, {cox['ucl']:.2f}); p={fmt_p(cox['p'])}"],
        ["Log-rank", "Two-sided log-rank test", f"Chi-square {chi2:.2f}; p={fmt_p(lr_p)}"],
        ["RMST sensitivity", "Restricted mean survival time through 12 months", f"{ARM_T}: {rmst_t:.2f} months; {ARM_C}: {rmst_c:.2f} months; difference {rmst_t-rmst_c:.2f}"],
        ["Censoring sensitivity", "Treat new anti-cancer therapy/missed assessment rules as SAP-defined censoring events", "Implemented through ADTTE CNSR/EVNTDESC fields in this synthetic portfolio"],
        ["Subgroup consistency", "Forest plot across age, sex, ECOG, PD-L1 and region", "Presented in Figure 14.2.3; descriptive only"],
    ], columns=["Analysis", "Description", "Result/implementation"])
    pfs_sens.to_csv(OUT_TABLES / "t14_2_5_pfs_sensitivity.csv", index=False)

    # Exposure-adjusted event rates.
    total_exp = adsl.groupby("TRT01P")["TRTDURM"].sum().to_dict()
    ae_rows = []
    for label, cond in [
        ("All TEAEs", adae.TRTEMFL == "Y"),
        ("Treatment-related TEAEs", (adae.TRTEMFL == "Y") & (adae.AEREL == "Y")),
        ("Grade >=3 TEAEs", (adae.TRTEMFL == "Y") & (adae.AETOXGR >= 3)),
        ("Serious TEAEs", (adae.TRTEMFL == "Y") & (adae.AESER == "Y")),
    ]:
        row = {"Event category": label}
        for arm in ARMS:
            sub = adae[cond & (adae.TRT01P == arm)]
            exp = total_exp.get(arm, 0.0)
            rate = 100 * len(sub) / exp if exp > 0 else np.nan
            row[f"{arm} subjects"] = f"{sub.USUBJID.nunique()}"
            row[f"{arm} events"] = f"{len(sub)}"
            row[f"{arm} rate per 100 pt-months"] = f"{rate:.1f}"
        ae_rows.append(row)
    expae = pd.DataFrame(ae_rows)
    expae.to_csv(OUT_TABLES / "t14_3_5_exposure_adjusted_teae.csv", index=False)

    tlf_index = pd.DataFrame([
        ["Table 14.1.1", "Demographics and baseline characteristics", "ADSL", "FAS", "outputs/tables/t14_1_1_demographics.*"],
        ["Table 14.1.2", "Subject disposition", "ADSL", "Randomized Set", "outputs/tables/t14_1_2_disposition.*"],
        ["Table 14.1.3", "Extent of exposure", "ADSL", "Safety Set", "outputs/tables/t14_1_3_exposure.*"],
        ["Table 14.2.1", "Primary PFS analysis", "ADTTE", "FAS", "outputs/tables/t14_2_1_primary_pfs.*"],
        ["Table 14.2.2", "Overall survival analysis", "ADTTE", "FAS", "outputs/tables/t14_2_2_overall_survival.*"],
        ["Table 14.2.3", "Best overall response", "ADRS", "FAS", "outputs/tables/t14_2_3_best_overall_response.*"],
        ["Table 14.2.5", "PFS sensitivity analyses", "ADTTE", "FAS", "outputs/tables/t14_2_5_pfs_sensitivity.*"],
        ["Table 14.3.1", "Overall TEAE summary", "ADAE/ADSL", "Safety Set", "outputs/tables/t14_3_1_safety_overview.*"],
        ["Table 14.3.2", "TEAEs by SOC/PT", "ADAE/ADSL", "Safety Set", "outputs/tables/t14_3_2_teae_by_soc_pt.*"],
        ["Table 14.3.3", "Grade >=3 TEAEs by SOC/PT", "ADAE/ADSL", "Safety Set", "outputs/tables/t14_3_3_grade3_teae_by_soc_pt.*"],
        ["Table 14.3.4", "Laboratory shift summary", "ADLB/ADSL", "Safety Set", "outputs/tables/t14_3_4_lab_shift.*"],
        ["Table 14.3.5", "Exposure-adjusted TEAE rates", "ADAE/ADSL", "Safety Set", "outputs/tables/t14_3_5_exposure_adjusted_teae.*"],
        ["Listing 16.2.1", "Deaths", "ADSL/ADTTE/ADAE", "Safety Set", "outputs/listings/l16_2_1_deaths.*"],
        ["Listing 16.2.2", "Serious adverse events", "ADAE", "Safety Set", "outputs/listings/l16_2_2_serious_adverse_events.*"],
        ["Listing 16.2.3", "AEs leading to treatment discontinuation", "ADAE", "Safety Set", "outputs/listings/l16_2_3_ae_discontinuations.*"],
    ], columns=["Output", "Title", "Source analysis dataset", "Population", "Location"])
    tlf_index.to_csv(OUT_TABLES / "tlf_index.csv", index=False)

    traceability = pd.DataFrame([
        ["Primary objective", "Compare PFS", "SAP Section 7.1", "ADTTE PARAMCD=PFS", "Table 14.2.1, Figure 14.2.1", "programs/python/generate_tlfs.py"],
        ["Key secondary objective", "Compare OS", "SAP Section 7.2", "ADTTE PARAMCD=OS", "Table 14.2.2, Figure 14.2.2", "programs/python/generate_tlfs.py"],
        ["Key secondary objective", "Summarize ORR", "SAP Section 7.3", "ADRS ORRFL", "Table 14.2.3, Figure 14.2.4", "programs/python/generate_tlfs.py"],
        ["Safety objective", "Summarize TEAEs", "SAP Section 8", "ADAE TRTEMFL/AOCCFL/AOCCSFL", "Tables 14.3.1-14.3.5, Listings 16.2.2-16.2.3", "programs/python/generate_tlfs.py"],
        ["Data standards", "Document ADaM-style metadata", "ADRG Section 4", "ADSL/ADTTE/ADAE/ADRS/ADLB", "define_like_metadata.xml, adam_spec.csv", "programs/python/build_adam.py"],
        ["QC objective", "Confirm reproducibility and output completeness", "Validation Report", "All analysis datasets and outputs", "qc/validation_checks.csv", "programs/python/qc_validation.py"],
    ], columns=["Requirement", "Analysis question", "Document reference", "Dataset/variables", "Output", "Program"])
    traceability.to_csv(OUT_TABLES / "traceability_matrix.csv", index=False)

    cdisc_map = pd.DataFrame([
        ["ADSL", "Subject-Level Analysis Dataset", "One record per subject", "Treatment, demographics, strata, flags, exposure", "ADSL for all population denominators"],
        ["ADTTE", "Time-to-Event Analysis Dataset", "One record per subject per endpoint", "PARAMCD, AVAL, CNSR, EVNTDESC, STARTDT, ADT", "PFS/OS KM, log-rank and Cox analyses"],
        ["ADRS", "Response Analysis Dataset", "One record per subject", "BOR, ORRFL, DCRFL, BESTPCHG", "ORR/DCR summaries and waterfall plot"],
        ["ADAE", "Adverse Event Analysis Dataset", "One record per AE", "AEBODSYS, AEDECOD, AETOXGR, AESER, AEREL, AEACN, AESDTH", "TEAE incidence, seriousness, severity, discontinuation and fatal-event outputs"],
        ["ADLB", "Laboratory Analysis Dataset", "One record per subject per lab parameter", "BASEGR, WORSTGR, SHIFT", "Laboratory grade-shift table"],
    ], columns=["Dataset", "Submission-style role", "Structure", "Key variables", "Why it matters"])
    cdisc_map.to_csv(OUT_TABLES / "cdisc_adam_style_map.csv", index=False)

    qc_plan = pd.DataFrame([
        ["Source-to-analysis traceability", "Raw record counts reconcile to ADaM-style datasets", "Automated check + metadata review"],
        ["Population denominators", "FAS/SAFFL/ITTFL are complete and treatment assignments are stable", "Automated check"],
        ["Endpoint derivations", "Time-to-event records have valid CNSR, dates and positive AVAL", "Automated check"],
        ["Safety derivations", "AE dates are treatment-emergent; toxicity grades, seriousness and fatal flags are valid", "Automated check"],
        ["Output completeness", "CSV/MD/TXT TLF files plus PDF packet are present", "Automated check + visual review"],
        ["Independent review", "Key outputs can be reproduced by alternative SAS/R skeletons", "Manual/programmatic double programming placeholder"],
        ["Version control", "Repository contains reproducible pipeline, seed and CI workflow", "GitHub workflow + README"],
    ], columns=["QC domain", "Expectation", "Evidence in portfolio"])
    qc_plan.to_csv(OUT_TABLES / "programming_qc_plan.csv", index=False)

    key = get_key_results()
    key_df = pd.DataFrame([
        ["Randomized subjects", f"{key['n_total']} ({key['n_t']} ONC-305 + SOC; {key['n_c']} placebo + SOC)"],
        ["Primary PFS HR", key["pfs_hr"]],
        ["PFS median", f"{ARM_T}: {key['pfs_med_t']}; {ARM_C}: {key['pfs_med_c']}"],
        ["PFS log-rank p-value", key["pfs_p"]],
        ["OS HR", key["os_hr"]],
        ["OS median", f"{ARM_T}: {key['os_med_t']}; {ARM_C}: {key['os_med_c']}"],
        ["OS log-rank p-value", key["os_p"]],
        ["ORR", f"{ARM_T}: {key['orr_t']}; {ARM_C}: {key['orr_c']}"],
        ["Any TEAE", f"{ARM_T}: {key['any_teae_t']}; {ARM_C}: {key['any_teae_c']}"],
        ["Grade >=3 TEAE", f"{ARM_T}: {key['grade3_t']}; {ARM_C}: {key['grade3_c']}"],
    ], columns=["Metric", "Result"])
    key_df.to_csv(OUT_TABLES / "key_results_summary.csv", index=False)


def protocol_synopsis() -> None:
    flow = title_block("Protocol Synopsis", "Simulated randomized, double-blind, controlled Phase III oncology study")
    sections: list[tuple[str, str | pd.DataFrame]] = []
    synopsis = pd.DataFrame([
        ["Study design", "Randomized, double-blind, parallel-group, controlled Phase III study"],
        ["Planned sample size", "Approximately 420 subjects randomized 1:1"],
        ["Population", "Adults with advanced/metastatic solid tumours, ECOG 0-1, measurable disease and PD-L1 category available"],
        ["Treatment arms", f"{PRODUCT} versus {CONTROL}"],
        ["Randomization strata", "ECOG performance status (0 vs 1), PD-L1 category (<1%, 1-49%, >=50%) and geographic region"],
        ["Primary endpoint", "Progression-free survival by investigator assessment"],
        ["Key secondary endpoints", "Overall survival, objective response rate, disease control rate, exposure and safety/tolerability"],
        ["Data standards", "ADaM-style ADSL, ADTTE, ADRS, ADAE and ADLB with define-like metadata"],
    ], columns=["Item", "Description"])
    sections.append(("1. Study synopsis", synopsis))
    flow.append(para("1. Study synopsis", "Section"))
    flow.append(df_table(synopsis, font_size=7.2, first_col_width=1.7 * inch, total_width=7.0 * inch))
    flow.append(Spacer(1, 8))

    flow.append(para("2. Objectives", "Section"))
    objectives = [
        "Primary objective: compare progression-free survival between ONC-305 + SOC and placebo + SOC in the Full Analysis Set.",
        "Key secondary objectives: compare overall survival and objective response rate, and describe duration of treatment and safety/tolerability.",
        "Portfolio objective: demonstrate realistic biostatistics workflow from protocol/SAP assumptions to ADaM-style datasets, TLFs, validation checks and a CSR-style report.",
    ]
    flow.extend(bullet_list(objectives))
    sections.append(("2. Objectives", "\n".join([f"- {x}" for x in objectives])))

    flow.append(para("3. Endpoint definitions", "Section"))
    endpoint_def = pd.DataFrame([
        ["PFS", "Time from randomization to first documented progression or death from any cause, whichever occurs first"],
        ["OS", "Time from randomization to death from any cause"],
        ["ORR", "Proportion of subjects with best overall response of complete response or partial response"],
        ["DCR", "Proportion of subjects with complete response, partial response or stable disease"],
        ["TEAE", "Any adverse event with onset from first dose through 30 days after last dose, or worsening from baseline during that window"],
    ], columns=["Endpoint", "Definition"])
    flow.append(df_table(endpoint_def, font_size=7.0, first_col_width=1.1 * inch, total_width=7.0 * inch))
    sections.append(("3. Endpoint definitions", endpoint_def))

    flow.append(para("4. Quality and reproducibility features", "Section"))
    flow.extend(bullet_list([
        "Fixed random seed and end-to-end executable pipeline.",
        "Source datasets, ADaM-style analysis datasets, define-like metadata and reviewer guide.",
        "TLF index, traceability matrix, analysis population definitions and QC plan.",
        "Validation report with PASS/WARN/FAIL checks and professional PDF outputs.",
    ]))
    sections.append(("4. Quality and reproducibility features", "\n".join(["- Fixed seed and end-to-end executable pipeline", "- ADaM-style datasets and define-like metadata", "- TLF index, traceability matrix and QC plan", "- Validation report and PDF output package"])))

    _write_md(DOCS / "protocol_synopsis.md", sections)
    build_pdf(DOCS / "protocol_synopsis.pdf", flow)


def sap_document() -> None:
    create_professional_spec_tables()
    flow = title_block("Statistical Analysis Plan", "Professional simulated SAP for a Phase III oncology statistical submission portfolio")
    sections: list[tuple[str, str | pd.DataFrame]] = []

    toc = pd.DataFrame([
        ["1", "Purpose and scope"], ["2", "Study design and objectives"], ["3", "Estimands"], ["4", "Analysis populations"],
        ["5", "General statistical conventions"], ["6", "Multiplicity and decision rules"], ["7", "Efficacy analyses"],
        ["8", "Safety analyses"], ["9", "Missing data, intercurrent events and sensitivity analyses"], ["10", "Programming, data standards and QC"],
    ], columns=["Section", "Title"])
    flow.append(para("Table of contents", "Section"))
    flow.append(df_table(toc, font_size=7.2, first_col_width=0.8 * inch, total_width=6.6 * inch))
    sections.append(("Table of contents", toc))
    flow.append(PageBreak())

    flow.append(para("1. Purpose and scope", "Section"))
    text = (
        "This Statistical Analysis Plan (SAP) specifies the simulated primary, secondary and safety analyses for study ONC-305-301. "
        "The document is intentionally written in a sponsor/CRO style: it defines estimands, analysis populations, endpoint derivations, censoring conventions, multiplicity, statistical methods, output specifications and QC expectations before interpreting the simulated results. "
        "The SAP follows the spirit of modern estimand-based clinical-trial planning and includes traceability to ADaM-style datasets and TLF outputs."
    )
    flow.append(para(text))
    sections.append(("1. Purpose and scope", text))

    flow.append(para("2. Study design and objectives", "Section"))
    text = (
        "ONC-305-301 is a simulated, randomized, double-blind, parallel-group Phase III oncology study comparing ONC-305 + SOC with placebo + SOC. "
        "Subjects are randomized 1:1 and followed for progression, survival, response, exposure, adverse events and laboratory shifts. "
        "The primary objective is to compare PFS. Key secondary objectives are OS and ORR. Safety objectives describe the incidence, severity, seriousness, relatedness and consequences of TEAEs."
    )
    flow.append(para(text))
    sections.append(("2. Study design and objectives", text))

    flow.append(para("3. Estimand framework", "Section"))
    est = pd.read_csv(OUT_TABLES / "estimand_framework.csv")
    flow.append(para("The portfolio includes an explicit estimand table. This is important because modern trial teams expect the clinical question, population, endpoint variable, intercurrent-event strategy and summary measure to be aligned before analysis begins.", "Body"))
    flow.append(df_table(est, font_size=5.7, first_col_width=0.85 * inch, total_width=7.1 * inch, style_name="CellSmall"))
    sections.append(("3. Estimand framework", est))

    flow.append(para("4. Analysis populations", "Section"))
    pops = pd.read_csv(OUT_TABLES / "analysis_population_definitions.csv")
    flow.append(df_table(pops, font_size=6.6, first_col_width=1.35 * inch, total_width=7.1 * inch))
    sections.append(("4. Analysis populations", pops))

    flow.append(para("5. General statistical conventions", "Section"))
    conventions = [
        "All efficacy analyses are based on the Full Analysis Set unless stated otherwise. Treatment is analysed as randomized for efficacy and as actually received for safety.",
        "All statistical tests are two-sided. The family-wise type I error strategy is described in the multiplicity section. Confidence intervals are two-sided 95% intervals unless stated otherwise.",
        "Time-to-event endpoints are expressed in months as (analysis date - randomization date + 1) / 30.4375.",
        "Continuous variables are summarized by n, mean, standard deviation, median, quartiles, minimum and maximum where appropriate. Categorical variables are summarized as n (%) using the relevant population denominator.",
        "A subject is counted once at the highest applicable level for subject-incidence AE summaries. Multiple events for the same subject may contribute to exposure-adjusted event-rate summaries.",
        "Outputs are generated from analysis datasets, not directly from raw source data, to preserve traceability and reproducibility.",
    ]
    flow.extend(bullet_list(conventions))
    sections.append(("5. General statistical conventions", "\n".join([f"- {x}" for x in conventions])))

    flow.append(para("6. Multiplicity and decision rules", "Section"))
    mult = pd.read_csv(OUT_TABLES / "multiplicity_strategy.csv")
    flow.append(df_table(mult, font_size=6.8, first_col_width=0.7 * inch, total_width=7.1 * inch))
    sections.append(("6. Multiplicity and decision rules", mult))

    flow.append(para("7. Efficacy analyses", "Section"))
    flow.append(para("7.1 Primary endpoint: progression-free survival", "Subsection"))
    pfs_text = (
        "PFS will be summarized using Kaplan-Meier methods by treatment arm. The primary treatment comparison uses a log-rank test and Cox proportional hazards model. "
        "The hazard ratio is expressed as ONC-305 + SOC versus placebo + SOC; values below 1 favour ONC-305 + SOC. The primary table includes event counts, medians, landmark rates, Cox HRs and p-values."
    )
    flow.append(para(pfs_text))
    flow.append(para("7.2 Overall survival", "Subsection"))
    os_text = "OS is analyzed analogously to PFS, with death from any cause as the event and living/lost subjects censored at the last date known alive."
    flow.append(para(os_text))
    flow.append(para("7.3 Response", "Subsection"))
    resp_text = "Best overall response is summarized as CR, PR, SD, PD or NE. ORR is defined as CR + PR and reported with exact binomial confidence intervals. Missing or not evaluable response is treated as non-response for the main ORR summary."
    flow.append(para(resp_text))
    sections.append(("7. Efficacy analyses", "\n\n".join([pfs_text, os_text, resp_text])))

    flow.append(para("8. Safety analyses", "Section"))
    safety_text = (
        "Safety analyses use the Safety Set. TEAEs are summarized by subject incidence and by MedDRA-style system organ class and preferred term in this simulated dataset. "
        "Outputs include overall TEAE categories, treatment-related events, grade >=3 events, serious events, fatal events, events leading to discontinuation, laboratory grade shifts and exposure-adjusted event rates."
    )
    flow.append(para(safety_text))
    sections.append(("8. Safety analyses", safety_text))

    flow.append(para("9. Missing data, censoring and sensitivity analyses", "Section"))
    cens = pd.read_csv(OUT_TABLES / "endpoint_censoring_rules.csv")
    flow.append(para("The censoring table below is included because oncology SAPs are scrutinized heavily for PFS censoring choices.", "Body"))
    flow.append(df_table(cens, font_size=6.5, first_col_width=0.8 * inch, total_width=7.1 * inch))
    flow.append(Spacer(1, 6))
    sens = pd.read_csv(OUT_TABLES / "t14_2_5_pfs_sensitivity.csv")
    flow.append(df_table(sens, font_size=6.4, first_col_width=1.35 * inch, total_width=7.1 * inch))
    sections.append(("9. Missing data, censoring and sensitivity analyses", pd.concat([cens, sens], axis=0, ignore_index=True)))

    flow.append(para("10. Programming, data standards and QC", "Section"))
    qcp = pd.read_csv(OUT_TABLES / "programming_qc_plan.csv")
    flow.append(para("The executable implementation is in Python, with SAS and R skeletons included to show how the work maps to regulated clinical-programming workflows. The package uses ADaM-style datasets, define-like metadata, a TLF index, a traceability matrix and automated validation checks.", "Body"))
    flow.append(df_table(qcp, font_size=6.5, first_col_width=1.35 * inch, total_width=7.1 * inch))
    sections.append(("10. Programming, data standards and QC", qcp))

    flow.append(para("Appendix A. TLF index", "Section"))
    tlf_index = pd.read_csv(OUT_TABLES / "tlf_index.csv")
    flow.append(df_table(tlf_index, max_rows=30, font_size=5.8, first_col_width=0.9 * inch, total_width=7.1 * inch, style_name="CellSmall"))
    sections.append(("Appendix A. TLF index", tlf_index))

    _write_md(DOCS / "statistical_analysis_plan.md", sections)
    build_pdf(DOCS / "statistical_analysis_plan.pdf", flow)


def analysis_data_reviewers_guide() -> None:
    flow = title_block("Analysis Data Reviewer's Guide", "Mini ADRG-style guide for the simulated ADaM submission package")
    sections: list[tuple[str, str | pd.DataFrame]] = []
    flow.append(para("1. Purpose", "Section"))
    text = "This guide explains the simulated analysis datasets, derivation logic, metadata, traceability and known limitations. It is included because reviewer guides are a normal part of regulatory-style clinical data submissions and show that the portfolio is not just a collection of tables."
    flow.append(para(text))
    sections.append(("1. Purpose", text))

    flow.append(para("2. Dataset overview", "Section"))
    cdisc = pd.read_csv(OUT_TABLES / "cdisc_adam_style_map.csv")
    flow.append(df_table(cdisc, font_size=6.4, first_col_width=0.85 * inch, total_width=7.1 * inch))
    sections.append(("2. Dataset overview", cdisc))

    flow.append(para("3. Data flow", "Section"))
    data_flow = pd.read_csv(OUT_TABLES / "data_flow_summary.csv")
    flow.append(df_table(data_flow, font_size=6.4, first_col_width=0.9 * inch, total_width=7.1 * inch))
    sections.append(("3. Data flow", data_flow))

    flow.append(para("4. Traceability matrix", "Section"))
    trace = pd.read_csv(OUT_TABLES / "traceability_matrix.csv")
    flow.append(df_table(trace, font_size=5.8, first_col_width=0.95 * inch, total_width=7.1 * inch, style_name="CellSmall"))
    sections.append(("4. Traceability matrix", trace))

    flow.append(para("5. Metadata and limitations", "Section"))
    lim = [
        "The analysis datasets are ADaM-style CSV files with define-like XML metadata. They are not official SAS XPT transport files in this executable environment.",
        "The synthetic data were generated for portfolio demonstration only and do not represent any real drug, patient or site.",
        "SAS and R skeletons are included for translation to a more conventional sponsor/CRO toolchain.",
        "All scripts are deterministic under the fixed seed and can be regenerated from the repository root.",
    ]
    flow.extend(bullet_list(lim))
    sections.append(("5. Metadata and limitations", "\n".join([f"- {x}" for x in lim])))

    _write_md(DOCS / "analysis_data_reviewers_guide.md", sections)
    build_pdf(DOCS / "analysis_data_reviewers_guide.pdf", flow)


def table_packet() -> None:
    flow = title_block("Tables, Listings and Figures Packet", "Generated outputs from simulated ADaM-style datasets", version=PORTFOLIO_VERSION)
    flow.append(para("Output index", "Section"))
    tlf_index = pd.read_csv(OUT_TABLES / "tlf_index.csv")
    flow.append(df_table(tlf_index, max_rows=50, font_size=5.7, first_col_width=0.85 * inch, total_width=9.7 * inch, style_name="CellSmall"))
    flow.append(PageBreak())

    table_order = [
        ("t14_1_1_demographics", "Table 14.1.1 Demographics and Baseline Characteristics", 80),
        ("t14_1_2_disposition", "Table 14.1.2 Subject Disposition", 80),
        ("t14_1_3_exposure", "Table 14.1.3 Extent of Exposure", 80),
        ("t14_2_1_primary_pfs", "Table 14.2.1 Primary Efficacy Analysis: PFS", 80),
        ("t14_2_2_overall_survival", "Table 14.2.2 Key Secondary Efficacy Analysis: OS", 80),
        ("t14_2_3_best_overall_response", "Table 14.2.3 Best Overall Response", 80),
        ("t14_2_5_pfs_sensitivity", "Table 14.2.5 PFS Sensitivity Analyses", 80),
        ("t14_3_1_safety_overview", "Table 14.3.1 Safety Overview", 80),
        ("t14_3_2_teae_by_soc_pt", "Table 14.3.2 TEAEs by SOC/PT", 42),
        ("t14_3_3_grade3_teae_by_soc_pt", "Table 14.3.3 Grade >=3 TEAEs by SOC/PT", 42),
        ("t14_3_4_lab_shift", "Table 14.3.4 Laboratory Shift Summary", 80),
        ("t14_3_5_exposure_adjusted_teae", "Table 14.3.5 Exposure-Adjusted TEAE Event Rates", 80),
    ]
    for stem, title, max_rows in table_order:
        csv_path = OUT_TABLES / f"{stem}.csv"
        if csv_path.exists():
            flow.append(para(title, "Section"))
            flow.append(df_table(pd.read_csv(csv_path, keep_default_na=False), max_rows=max_rows, font_size=5.9, first_col_width=2.1 * inch, total_width=9.7 * inch, style_name="CellSmall"))
            flow.append(PageBreak())

    figure_order = [
        ("f14_2_1_km_pfs.png", "Figure 14.2.1 Kaplan-Meier Curve for PFS"),
        ("f14_2_2_km_os.png", "Figure 14.2.2 Kaplan-Meier Curve for OS"),
        ("f14_2_3_pfs_forest.png", "Figure 14.2.3 PFS Forest Plot"),
        ("f14_2_4_waterfall_best_change.png", "Figure 14.2.4 Waterfall Plot of Best Tumor Change"),
        ("f14_3_1_top_teae_bar.png", "Figure 14.3.1 Top TEAEs by Preferred Term"),
    ]
    for fname, title in figure_order:
        fpath = OUT_FIGURES / fname
        if fpath.exists():
            flow.append(para(title, "Section"))
            flow.append(Image(str(fpath), width=8.9 * inch, height=5.1 * inch))
            flow.append(PageBreak())

    listing_order = [
        ("l16_2_1_deaths", "Listing 16.2.1 Deaths", 30),
        ("l16_2_2_serious_adverse_events", "Listing 16.2.2 Serious Adverse Events", 35),
        ("l16_2_3_ae_discontinuations", "Listing 16.2.3 Adverse Events Leading to Treatment Discontinuation", 35),
    ]
    for stem, title, max_rows in listing_order:
        csv_path = OUT_LISTINGS / f"{stem}.csv"
        if csv_path.exists():
            flow.append(para(title, "Section"))
            flow.append(df_table(pd.read_csv(csv_path, keep_default_na=False), max_rows=max_rows, font_size=5.4, first_col_width=1.1 * inch, total_width=9.8 * inch, style_name="CellSmall"))
            flow.append(PageBreak())
    build_pdf(OUT_REPORTS / "tlf_packet.pdf", flow, landscape_page=True)


def analysis_report() -> None:
    key = get_key_results()
    flow = title_block("Clinical Study Analysis Report", "CSR-style statistical results report for simulated Phase III oncology study")
    sections: list[tuple[str, str | pd.DataFrame]] = []

    flow.append(para("1. Executive summary", "Section"))
    summary = (
        f"The simulated study randomized {key['n_total']} subjects ({key['n_t']} to ONC-305 + SOC and {key['n_c']} to placebo + SOC). "
        f"In the simulated primary analysis, PFS favoured ONC-305 + SOC with Cox HR {key['pfs_hr']} and log-rank p-value {key['pfs_p']}. "
        f"OS showed Cox HR {key['os_hr']} and log-rank p-value {key['os_p']}. "
        f"ORR was {key['orr_t']} for ONC-305 + SOC and {key['orr_c']} for placebo + SOC. "
        "Safety outputs show a realistic oncology pattern with high overall TEAE incidence and separate summaries for grade >=3, serious, related, discontinuation and fatal events."
    )
    flow.append(para(summary))
    sections.append(("1. Executive summary", summary))

    flow.append(para("Key results dashboard", "Subsection"))
    key_df = pd.read_csv(OUT_TABLES / "key_results_summary.csv")
    flow.append(df_table(key_df, font_size=7.0, first_col_width=2.0 * inch, total_width=7.0 * inch))
    sections.append(("Key results dashboard", key_df))

    flow.append(para("2. Study design and analysis populations", "Section"))
    data_flow = pd.read_csv(OUT_TABLES / "data_flow_summary.csv")
    flow.append(para("The analysis followed the prespecified SAP. Efficacy analyses used the FAS/ITT principle, and safety analyses used the Safety Set. The table below documents the generated data flow from raw simulation to ADaM-style analysis datasets.", "Body"))
    flow.append(df_table(data_flow, max_rows=20, font_size=6.2, first_col_width=1.0 * inch, total_width=7.1 * inch, style_name="CellSmall"))
    sections.append(("2. Study design and analysis populations", data_flow))

    flow.append(para("3. Primary efficacy: PFS", "Section"))
    pfs = read_table("t14_2_1_primary_pfs")
    flow.append(para(f"Median PFS was {key['pfs_med_t']} for ONC-305 + SOC and {key['pfs_med_c']} for placebo + SOC. The treatment HR was {key['pfs_hr']}. The Kaplan-Meier curve and sensitivity table are provided below.", "Body"))
    flow.append(df_table(pfs, max_rows=80, font_size=6.4, first_col_width=2.3 * inch, total_width=7.1 * inch))
    fpath = OUT_FIGURES / "f14_2_1_km_pfs.png"
    if fpath.exists():
        flow.append(Spacer(1, 6))
        flow.append(Image(str(fpath), width=6.7 * inch, height=3.8 * inch))
    flow.append(para("PFS sensitivity analyses", "Subsection"))
    sens = pd.read_csv(OUT_TABLES / "t14_2_5_pfs_sensitivity.csv")
    flow.append(df_table(sens, font_size=6.2, first_col_width=1.35 * inch, total_width=7.1 * inch))
    sections.append(("3. Primary efficacy: PFS", pd.concat([pfs, sens], axis=0, ignore_index=True)))

    flow.append(PageBreak())
    flow.append(para("4. Secondary efficacy: OS and response", "Section"))
    os_ = read_table("t14_2_2_overall_survival")
    orr = read_table("t14_2_3_best_overall_response")
    flow.append(para(f"Median OS was {key['os_med_t']} for ONC-305 + SOC and {key['os_med_c']} for placebo + SOC. ORR was {key['orr_t']} versus {key['orr_c']}. These results are simulated and are used only to demonstrate reporting and interpretation structure.", "Body"))
    flow.append(df_table(os_, max_rows=80, font_size=6.4, first_col_width=2.3 * inch, total_width=7.1 * inch))
    fpath = OUT_FIGURES / "f14_2_2_km_os.png"
    if fpath.exists():
        flow.append(Spacer(1, 6))
        flow.append(Image(str(fpath), width=6.7 * inch, height=3.8 * inch))
    flow.append(para("Best overall response", "Subsection"))
    flow.append(df_table(orr, max_rows=80, font_size=6.4, first_col_width=2.3 * inch, total_width=7.1 * inch))
    sections.append(("4. Secondary efficacy: OS and response", pd.concat([os_, orr], axis=0, ignore_index=True)))

    flow.append(PageBreak())
    flow.append(para("5. Safety", "Section"))
    safety = read_table("t14_3_1_safety_overview")
    expae = pd.read_csv(OUT_TABLES / "t14_3_5_exposure_adjusted_teae.csv")
    flow.append(para(f"Any TEAE was reported in {key['any_teae_t']} of ONC-305 + SOC subjects and {key['any_teae_c']} of placebo + SOC subjects. Grade >=3 TEAEs were reported in {key['grade3_t']} and {key['grade3_c']}, respectively. Exposure-adjusted rates are included to show an additional safety-analysis perspective.", "Body"))
    flow.append(df_table(safety, max_rows=80, font_size=6.4, first_col_width=2.5 * inch, total_width=7.1 * inch))
    flow.append(para("Exposure-adjusted TEAE rates", "Subsection"))
    flow.append(df_table(expae, max_rows=80, font_size=5.6, first_col_width=1.5 * inch, total_width=7.1 * inch, style_name="CellSmall"))
    fpath = OUT_FIGURES / "f14_3_1_top_teae_bar.png"
    if fpath.exists():
        flow.append(Spacer(1, 6))
        flow.append(Image(str(fpath), width=6.7 * inch, height=3.8 * inch))
    sections.append(("5. Safety", pd.concat([safety, expae], axis=0, ignore_index=True)))

    flow.append(PageBreak())
    flow.append(para("6. Interpretation and limitations", "Section"))
    interp = [
        "The report is intentionally realistic but not clinically meaningful because all data are synthetic.",
        "The results should be interpreted as a demonstration of SAP-to-CSR workflow, not evidence about ONC-305 or any real therapy.",
        "The current implementation uses ADaM-style CSV datasets and define-like XML. A production sponsor workflow would normally provide validated SAS XPT transport files, SDTM datasets, an ADRG/SDRG and controlled-terminology compliance checks.",
        "A recruiter should focus on the end-to-end competence shown: derivation logic, survival methods, safety reporting, traceability, QC and professional documentation.",
    ]
    flow.extend(bullet_list(interp))
    sections.append(("6. Interpretation and limitations", "\n".join([f"- {x}" for x in interp])))

    _write_md(OUT_REPORTS / "clinical_study_analysis_report.md", sections)
    build_pdf(OUT_REPORTS / "clinical_study_analysis_report.pdf", flow)


def validation_report_pdf() -> None:
    qc_df = pd.read_csv(QC / "validation_checks.csv", keep_default_na=False)
    flow = title_block("Validation and QC Report", "Automated checks, traceability and programming-quality evidence")
    flow.append(para("1. QC summary", "Section"))
    flow.append(para(f"Total checks: {len(qc_df)}; PASS: {(qc_df.Status == 'PASS').sum()}; WARN: {(qc_df.Status == 'WARN').sum()}; FAIL: {(qc_df.Status == 'FAIL').sum()}."))
    flow.append(df_table(qc_df, max_rows=120, font_size=5.6, first_col_width=2.2 * inch, total_width=9.7 * inch, style_name="CellSmall"))
    flow.append(PageBreak())
    flow.append(para("2. Programming QC plan", "Section"))
    qcp = pd.read_csv(OUT_TABLES / "programming_qc_plan.csv")
    flow.append(df_table(qcp, max_rows=50, font_size=6.2, first_col_width=1.5 * inch, total_width=9.7 * inch, style_name="CellSmall"))
    flow.append(para("3. Traceability matrix", "Section"))
    trace = pd.read_csv(OUT_TABLES / "traceability_matrix.csv")
    flow.append(df_table(trace, max_rows=50, font_size=5.8, first_col_width=1.1 * inch, total_width=9.7 * inch, style_name="CellSmall"))
    build_pdf(OUT_REPORTS / "validation_report.pdf", flow, landscape_page=True)


def portfolio_summary_pdf() -> None:
    key = get_key_results()
    flow = title_block("Portfolio One-Page Summary", "What a recruiter or hiring manager should notice first")
    flow.append(para("Why this project is strong", "Section"))
    flow.extend(bullet_list([
        "Looks like a small sponsor/CRO statistical package rather than a generic coding demo.",
        "Connects protocol/SAP thinking to ADaM-style datasets, TLFs, CSR-style reporting and validation.",
        "Shows oncology survival analysis, response analysis, safety reporting and exposure-adjusted AE rates.",
        "Includes Python executable code plus SAS/R templates for regulated workflow translation.",
        "Demonstrates traceability, QC, reviewer-guide documentation and GitHub-ready reproducibility.",
    ]))
    flow.append(para("Headline simulated results", "Section"))
    flow.append(df_table(pd.read_csv(OUT_TABLES / "key_results_summary.csv"), font_size=7.0, first_col_width=2.0 * inch, total_width=7.0 * inch))
    flow.append(para("Suggested CV bullet", "Section"))
    flow.append(para("Built a simulated Phase III oncology statistical-submission portfolio with SAP, protocol synopsis, ADaM-style ADSL/ADTTE/ADAE/ADRS/ADLB datasets, Kaplan-Meier/Cox/log-rank survival analyses, ORR and safety TLFs, exposure-adjusted AE rates, listings, figures, reviewer guide, traceability matrix, QC checks and reproducible Python/SAS/R programming structure.", "Small"))
    build_pdf(OUT_REPORTS / "portfolio_one_page_summary.pdf", flow)


def recruiter_docs() -> None:
    README = f"""# Simulated Phase III Oncology Statistical Submission Portfolio

**Study:** {STUDY_ID}, a simulated randomized Phase III oncology trial comparing `ONC-305 + SOC` with `Placebo + SOC` in advanced/metastatic solid tumours.

This repository is a professional biostatistics/statistical-programming portfolio. It is designed to show how a trial statistician can move from protocol and SAP assumptions to ADaM-style datasets, TLFs, CSR-style reporting, reviewer documentation, validation checks and reproducible code.

> All patient-level data are synthetic. This project is not clinical evidence and is not for clinical decision-making.

## What this demonstrates

- Phase III oncology SAP writing, including estimands, analysis populations, multiplicity, censoring and sensitivity analyses.
- ADaM-style datasets: `ADSL`, `ADTTE`, `ADAE`, `ADRS`, `ADLB`.
- Survival analysis: Kaplan-Meier, log-rank tests, Cox proportional hazards models, landmark rates, subgroup forest plot and RMST sensitivity.
- Response analysis: best overall response, ORR, DCR and exact binomial confidence intervals.
- Safety reporting: TEAEs, treatment-related TEAEs, grade >=3 TEAEs, SAEs, discontinuations, fatal events, lab shifts and exposure-adjusted event rates.
- Regulatory-style documentation: SAP, protocol synopsis, mini ADRG, TLF index, traceability matrix, QC plan and validation report.
- Reproducible programming: Python executable pipeline plus SAS/R templates.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python programs/python/run_all.py
```

## Key outputs

- `docs/statistical_analysis_plan.pdf`
- `docs/protocol_synopsis.pdf`
- `docs/analysis_data_reviewers_guide.pdf`
- `outputs/reports/clinical_study_analysis_report.pdf`
- `outputs/reports/tlf_packet.pdf`
- `outputs/reports/validation_report.pdf`
- `outputs/reports/portfolio_one_page_summary.pdf`
- `outputs/tables/tlf_index.csv`
- `outputs/tables/traceability_matrix.csv`
- `data/specs/adam_spec.csv`
- `data/specs/define_like_metadata.xml`

## Repository structure

```text
data/raw/          simulated source datasets
data/adam/         ADaM-style analysis datasets
data/specs/        variable metadata and define-like XML
docs/              SAP, protocol synopsis, ADRG, GitHub guide, CV bullets
programs/python/   executable pipeline
programs/sas/      sponsor/CRO-style SAS templates
programs/r/        R templates and optional transport export skeleton
outputs/tables/    TLF CSV/MD/TXT outputs
outputs/listings/  listing CSV/MD/TXT outputs
outputs/figures/   KM, forest, waterfall and safety figures
outputs/reports/   PDF report package
qc/                validation checks and QC report
```

## Suggested CV bullet

> Built a simulated Phase III oncology statistical-submission portfolio with SAP, protocol synopsis, ADaM-style ADSL/ADTTE/ADAE/ADRS/ADLB datasets, Kaplan-Meier/Cox/log-rank survival analyses, ORR and safety TLFs, exposure-adjusted AE rates, listings, figures, reviewer guide, traceability matrix, QC checks and reproducible Python/SAS/R programming structure.

## Important limitation

The executable pipeline writes ADaM-style CSV files and define-like XML in this environment. A production regulatory submission would normally include validated SAS XPT transport files, controlled terminology checks, SDTM datasets, ADRG/SDRG documents and sponsor-specific validation procedures.
"""
    (Path(__file__).resolve().parents[2] / "README.md").write_text(README, encoding="utf-8")

    github_guide = """# How to put this portfolio on GitHub

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
"""
    (DOCS / "github_publish_guide.md").write_text(github_guide, encoding="utf-8")

    cv_bullets = """# CV bullets for pharma biostatistics roles

Use one or two of these depending on space:

- Built a simulated Phase III oncology statistical-submission portfolio with SAP, protocol synopsis, ADaM-style ADSL/ADTTE/ADAE/ADRS/ADLB datasets, Kaplan-Meier/Cox/log-rank survival analyses, ORR and safety TLFs, exposure-adjusted AE rates, listings, figures, reviewer guide, traceability matrix, QC checks and reproducible Python/SAS/R programming structure.
- Produced sponsor/CRO-style clinical-trial outputs including PFS/OS Kaplan-Meier analyses, Cox hazard ratios, ORR exact confidence intervals, TEAE summaries by SOC/PT, grade >=3 events, serious AEs, AE discontinuations, deaths and laboratory grade shifts.
- Created validation checks for subject counts, flags, treatment assignment, date chronology, endpoint censoring, AE toxicity grades, output completeness, ADaM-style metadata and traceability from SAP objectives to TLF outputs.
"""
    (DOCS / "cv_bullets.md").write_text(cv_bullets, encoding="utf-8")

    talking = """# Interview talking points

1. I built this as a SAP-to-CSR workflow, not just a set of tables.
2. The primary endpoint is PFS, so the project shows Kaplan-Meier estimation, log-rank testing, Cox modelling, censoring rules, landmark rates and sensitivity analysis.
3. I included ADaM-style datasets because pharma teams want traceability from source data to analysis datasets to TLFs.
4. I included safety outputs that are common in oncology: TEAEs by SOC/PT, grade >=3 events, SAEs, discontinuations, fatal events, laboratory shifts and exposure-adjusted rates.
5. I included a mini ADRG, TLF index and traceability matrix to show awareness of regulatory-style review workflows.
6. The project is reproducible from one command and includes Python plus SAS/R templates.
"""
    (DOCS / "interview_talking_points.md").write_text(talking, encoding="utf-8")

    mermaid = """flowchart LR
  A[Simulated raw datasets: DM/TTE/RS/AE/LB/EX/DS] --> B[ADaM-style datasets: ADSL/ADTTE/ADRS/ADAE/ADLB]
  B --> C[TLFs: efficacy, safety, listings and figures]
  C --> D[CSR-style report and TLF packet]
  B --> E[ADRG, define-like metadata and traceability matrix]
  C --> F[Validation report and QC checks]
"""
    (DOCS / "data_flow_diagram.mmd").write_text(mermaid, encoding="utf-8")

    # GitHub Actions workflow and improved Makefile.
    workflow_dir = Path(__file__).resolve().parents[2] / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow = """name: Regenerate portfolio

on:
  push:
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pipeline
        run: python programs/python/run_all.py
      - name: Check key outputs
        run: |
          test -f docs/statistical_analysis_plan.pdf
          test -f outputs/reports/clinical_study_analysis_report.pdf
          test -f outputs/reports/validation_report.pdf
"""
    (workflow_dir / "run-portfolio.yml").write_text(workflow, encoding="utf-8")

    makefile = """all:
	python programs/python/run_all.py

clean:
	rm -rf data/raw/*.csv data/adam/*.csv outputs/tables/* outputs/listings/* outputs/figures/* outputs/reports/* qc/* docs/*.pdf

summary:
	python programs/python/run_all.py
	ls -lh docs/*.pdf outputs/reports/*.pdf
"""
    (Path(__file__).resolve().parents[2] / "Makefile").write_text(makefile, encoding="utf-8")


def render_all_reports() -> None:
    ensure_dirs()
    create_professional_spec_tables()
    protocol_synopsis()
    sap_document()
    analysis_data_reviewers_guide()
    table_packet()
    analysis_report()
    validation_report_pdf()
    portfolio_summary_pdf()
    recruiter_docs()
    print("Rendered professional SAP, protocol, ADRG, TLF packet, CSR-style report, validation report, one-page summary and recruiter docs.")


if __name__ == "__main__":
    render_all_reports()
