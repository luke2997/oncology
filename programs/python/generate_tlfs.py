from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from utils import (
    DATA_ADAM, OUT_FIGURES, OUT_TABLES, OUT_LISTINGS, ensure_dirs, ARM_T, ARM_C, ARMS, TOTAL,
    pct, mean_sd, median_range, q1_q3, fmt_p, fmt_ci, write_table, write_listing,
    km_curve, km_estimate_at, bootstrap_km_median_ci, logrank_test, cox_ph, beta_ci, SEED
)


def load_adam() -> dict[str, pd.DataFrame]:
    return {name: pd.read_csv(DATA_ADAM / f"{name}.csv") for name in ["adsl", "adtte", "adae", "adrs", "adlb"]}


def denom(adsl: pd.DataFrame, flag: str = "FASFL") -> dict[str, int]:
    if flag in adsl.columns:
        base = adsl[adsl[flag] == "Y"]
    else:
        base = adsl
    d = {arm: int((base["TRT01P"] == arm).sum()) for arm in ARMS}
    d[TOTAL] = int(len(base))
    return d


def categorical_rows(adsl: pd.DataFrame, var: str, label: str, levels: list[str], denoms: dict[str, int]) -> list[dict[str, str]]:
    rows = []
    rows.append({"Characteristic": label, ARM_T: "", ARM_C: "", TOTAL: ""})
    for lev in levels:
        row = {"Characteristic": f"  {lev}"}
        for arm in ARMS:
            row[arm] = pct(((adsl["TRT01P"] == arm) & (adsl[var].astype(str) == str(lev))).sum(), denoms[arm])
        row[TOTAL] = pct((adsl[var].astype(str) == str(lev)).sum(), denoms[TOTAL])
        rows.append(row)
    return rows


def table_demographics(adsl: pd.DataFrame) -> pd.DataFrame:
    denoms = denom(adsl, "FASFL")
    rows = [
        {"Characteristic": "Analysis set: Full analysis set", ARM_T: str(denoms[ARM_T]), ARM_C: str(denoms[ARM_C]), TOTAL: str(denoms[TOTAL])},
        {"Characteristic": "Age, years - mean (SD)", ARM_T: mean_sd(adsl.loc[adsl.TRT01P == ARM_T, "AGE"]), ARM_C: mean_sd(adsl.loc[adsl.TRT01P == ARM_C, "AGE"]), TOTAL: mean_sd(adsl["AGE"])},
        {"Characteristic": "Age, years - median (min, max)", ARM_T: median_range(adsl.loc[adsl.TRT01P == ARM_T, "AGE"]), ARM_C: median_range(adsl.loc[adsl.TRT01P == ARM_C, "AGE"]), TOTAL: median_range(adsl["AGE"])},
    ]
    rows += categorical_rows(adsl, "AGEGR1", "Age group", ["<65", ">=65"], denoms)
    rows += categorical_rows(adsl, "SEX", "Sex", ["Male", "Female"], denoms)
    rows += categorical_rows(adsl, "RACE", "Race", ["Asian", "White", "Black or African American", "Other"], denoms)
    rows += categorical_rows(adsl, "ECOG", "ECOG performance status", ["0", "1"], denoms)
    rows += categorical_rows(adsl, "STAGE", "Disease stage", ["IIIB/IIIC", "IV"], denoms)
    rows += categorical_rows(adsl, "PDL1CAT", "PD-L1 category", ["<1%", "1-49%", ">=50%"], denoms)
    rows += categorical_rows(adsl, "REGION", "Region", ["Asia", "Europe", "North America", "Rest of World"], denoms)
    df = pd.DataFrame(rows)
    df.columns = ["Characteristic", f"{ARM_T} (N={denoms[ARM_T]})", f"{ARM_C} (N={denoms[ARM_C]})", f"Total (N={denoms[TOTAL]})"]
    write_table(df, "t14_1_1_demographics", "Table 14.1.1 Demographics and Baseline Characteristics", ["Percentages use the full analysis set denominator.", "All data are simulated."])
    return df


def table_disposition(adsl: pd.DataFrame) -> pd.DataFrame:
    denoms = denom(adsl, "FASFL")
    reasons = ["Randomized", "Full analysis set", "Safety set", "Ongoing", "Completed treatment", "Progressive disease", "Adverse event", "Withdrawal by subject", "Death", "Other"]
    rows = []
    for r in reasons:
        row = {"Category": r}
        for arm in ARMS:
            subset = adsl[adsl.TRT01P == arm]
            if r == "Randomized":
                val = len(subset)
            elif r == "Full analysis set":
                val = (subset.FASFL == "Y").sum()
            elif r == "Safety set":
                val = (subset.SAFFL == "Y").sum()
            else:
                val = (subset.DCSREAS == r).sum()
            row[arm] = pct(val, denoms[arm])
        if r == "Randomized":
            val_total = len(adsl)
        elif r == "Full analysis set":
            val_total = (adsl.FASFL == "Y").sum()
        elif r == "Safety set":
            val_total = (adsl.SAFFL == "Y").sum()
        else:
            val_total = (adsl.DCSREAS == r).sum()
        row[TOTAL] = pct(val_total, denoms[TOTAL])
        rows.append(row)
    df = pd.DataFrame(rows)
    df.columns = ["Category", f"{ARM_T} (N={denoms[ARM_T]})", f"{ARM_C} (N={denoms[ARM_C]})", f"Total (N={denoms[TOTAL]})"]
    write_table(df, "t14_1_2_disposition", "Table 14.1.2 Subject Disposition", ["Disposition categories are generated from simulated treatment end reasons."])
    return df


def table_exposure(adsl: pd.DataFrame) -> pd.DataFrame:
    denoms = denom(adsl, "SAFFL")
    rows = []
    for desc, var, func in [
        ("Treatment duration, days - mean (SD)", "TRTDURD", mean_sd),
        ("Treatment duration, months - median (Q1, Q3)", "TRTDURM", q1_q3),
        ("Relative dose intensity, % - mean (SD)", "RDI", mean_sd),
        ("Relative dose intensity, % - median (min, max)", "RDI", median_range),
    ]:
        rows.append({"Exposure summary": desc, ARM_T: func(adsl.loc[adsl.TRT01P == ARM_T, var]), ARM_C: func(adsl.loc[adsl.TRT01P == ARM_C, var]), TOTAL: func(adsl[var])})
    for cut, label in [(80, "RDI <80%"), (90, "RDI >=90%")]:
        row = {"Exposure summary": label}
        for arm in ARMS:
            sub = adsl[adsl.TRT01P == arm]
            if cut == 80:
                val = (sub.RDI < 80).sum()
            else:
                val = (sub.RDI >= 90).sum()
            row[arm] = pct(val, denoms[arm])
        row[TOTAL] = pct((adsl.RDI < 80).sum() if cut == 80 else (adsl.RDI >= 90).sum(), denoms[TOTAL])
        rows.append(row)
    df = pd.DataFrame(rows)
    df.columns = ["Exposure summary", f"{ARM_T} (N={denoms[ARM_T]})", f"{ARM_C} (N={denoms[ARM_C]})", f"Total (N={denoms[TOTAL]})"]
    write_table(df, "t14_1_3_exposure", "Table 14.1.3 Extent of Exposure", ["RDI = relative dose intensity."])
    return df


def survival_table(adtte: pd.DataFrame, paramcd: str, title: str, stem: str) -> pd.DataFrame:
    data = adtte[(adtte.PARAMCD == paramcd) & (adtte.ANL01FL == "Y")].copy()
    data["event"] = 1 - data["CNSR"].astype(int)
    group = (data["TRT01P"] == ARM_T).astype(int).to_numpy()
    cox = cox_ph(data["AVAL"].to_numpy(), data["event"].to_numpy(), group)
    chi2, logrank_p = logrank_test(data["AVAL"].to_numpy(), data["event"].to_numpy(), group)
    # adjusted model with basic covariates.
    cov = pd.DataFrame({
        "age65": (data["AGEGR1"] == ">=65").astype(int),
        "ecog1": (data["ECOG"].astype(str) == "1").astype(int),
        "stage4": (data["STAGE"] == "IV").astype(int),
        "pdl1high": (data["PDL1CAT"] == ">=50%").astype(int),
    })
    cox_adj = cox_ph(data["AVAL"].to_numpy(), data["event"].to_numpy(), group, covariates=cov)
    rows = []
    for arm in ARMS:
        sub = data[data.TRT01P == arm]
        event = sub["event"].to_numpy()
        time = sub["AVAL"].to_numpy()
        med, lo, hi = bootstrap_km_median_ci(time, event, n_boot=40, seed=SEED + (1 if arm == ARM_T else 2) + (10 if paramcd == "OS" else 0))
        rows.append({
            "Analysis": arm,
            "N": len(sub),
            "Events, n (%)": pct(event.sum(), len(sub)),
            "Median months (95% CI)": f"{med:.1f} {fmt_ci(lo, hi, 1)}" if not np.isnan(med) else "Not reached",
            "6-mo KM rate": f"{100*km_estimate_at(time, event, 6):.1f}%",
            "12-mo KM rate": f"{100*km_estimate_at(time, event, 12):.1f}%",
            "18-mo KM rate": f"{100*km_estimate_at(time, event, 18):.1f}%",
        })
    rows += [
        {"Analysis": "Treatment comparison", "N": "", "Events, n (%)": "", "Median months (95% CI)": "", "6-mo KM rate": "", "12-mo KM rate": "", "18-mo KM rate": ""},
        {"Analysis": "Cox HR, treatment vs control", "N": "", "Events, n (%)": "", "Median months (95% CI)": f"{cox['hr']:.2f} {fmt_ci(cox['lcl'], cox['ucl'], 2)}", "6-mo KM rate": "", "12-mo KM rate": "", "18-mo KM rate": ""},
        {"Analysis": "Adjusted Cox HR", "N": "", "Events, n (%)": "", "Median months (95% CI)": f"{cox_adj['hr']:.2f} {fmt_ci(cox_adj['lcl'], cox_adj['ucl'], 2)}", "6-mo KM rate": "", "12-mo KM rate": "", "18-mo KM rate": ""},
        {"Analysis": "Log-rank test p-value", "N": "", "Events, n (%)": "", "Median months (95% CI)": fmt_p(logrank_p), "6-mo KM rate": "", "12-mo KM rate": "", "18-mo KM rate": ""},
    ]
    df = pd.DataFrame(rows)
    write_table(df, stem, title, ["CNSR=0 denotes an event. Cox HR <1 favors ONC-305 + SOC.", "Median CI uses nonparametric bootstrap for portfolio demonstration."])
    return df


def table_response(adrs: pd.DataFrame) -> pd.DataFrame:
    denoms = {arm: int((adrs.TRT01P == arm).sum()) for arm in ARMS}
    denoms[TOTAL] = len(adrs)
    rows = []
    for bor in ["CR", "PR", "SD", "PD", "NE"]:
        row = {"Response category": bor}
        for arm in ARMS:
            row[arm] = pct(((adrs.TRT01P == arm) & (adrs.BOR == bor)).sum(), denoms[arm])
        row[TOTAL] = pct((adrs.BOR == bor).sum(), denoms[TOTAL])
        rows.append(row)
    for flag, label in [("ORRFL", "Objective response rate (CR + PR)"), ("DCRFL", "Disease control rate (CR + PR + SD)")]:
        row = {"Response category": label}
        for arm in ARMS:
            x = int(((adrs.TRT01P == arm) & (adrs[flag] == "Y")).sum())
            lo, hi = beta_ci(x, denoms[arm])
            row[arm] = f"{pct(x, denoms[arm])}; 95% CI {100*lo:.1f}-{100*hi:.1f}%"
        x = int((adrs[flag] == "Y").sum())
        lo, hi = beta_ci(x, denoms[TOTAL])
        row[TOTAL] = f"{pct(x, denoms[TOTAL])}; 95% CI {100*lo:.1f}-{100*hi:.1f}%"
        rows.append(row)
    df = pd.DataFrame(rows)
    df.columns = ["Response category", f"{ARM_T} (N={denoms[ARM_T]})", f"{ARM_C} (N={denoms[ARM_C]})", f"Total (N={denoms[TOTAL]})"]
    write_table(df, "t14_2_3_best_overall_response", "Table 14.2.3 Best Overall Response", ["CR = complete response; PR = partial response; SD = stable disease; PD = progressive disease; NE = not evaluable."])
    return df


def table_safety_overview(adsl: pd.DataFrame, adae: pd.DataFrame) -> pd.DataFrame:
    denoms = denom(adsl, "SAFFL")
    rows = []
    def subj_count(condition):
        return set(adae.loc[condition, "USUBJID"])
    categories = [
        ("Any TEAE", subj_count(adae.TRTEMFL == "Y")),
        ("Any treatment-related TEAE", subj_count((adae.TRTEMFL == "Y") & (adae.AEREL == "Y"))),
        ("Any grade >=3 TEAE", subj_count((adae.TRTEMFL == "Y") & (adae.AETOXGR >= 3))),
        ("Any serious TEAE", subj_count((adae.TRTEMFL == "Y") & (adae.AESER == "Y"))),
        ("Any TEAE leading to treatment discontinuation", subj_count((adae.TRTEMFL == "Y") & (adae.AEACN == "DRUG WITHDRAWN"))),
        ("Any fatal TEAE", subj_count((adae.TRTEMFL == "Y") & (adae.AESDTH == "Y"))),
    ]
    for label, ids in categories:
        row = {"Safety summary": label}
        for arm in ARMS:
            sub_ids = set(adsl.loc[adsl.TRT01P == arm, "USUBJID"])
            row[arm] = pct(len(ids.intersection(sub_ids)), denoms[arm])
        row[TOTAL] = pct(len(ids), denoms[TOTAL])
        rows.append(row)
    df = pd.DataFrame(rows)
    df.columns = ["Safety summary", f"{ARM_T} (N={denoms[ARM_T]})", f"{ARM_C} (N={denoms[ARM_C]})", f"Total (N={denoms[TOTAL]})"]
    write_table(df, "t14_3_1_safety_overview", "Table 14.3.1 Overall Summary of Treatment-Emergent Adverse Events", ["Subjects are counted once per category."])
    return df


def ae_by_soc_pt(adsl: pd.DataFrame, adae: pd.DataFrame, grade3_only: bool = False) -> pd.DataFrame:
    denoms = denom(adsl, "SAFFL")
    data = adae[adae.TRTEMFL == "Y"].copy()
    if grade3_only:
        data = data[data.AETOXGR >= 3]
    rows = []
    for soc, soc_df in data.groupby("AEBODSYS"):
        row = {"System organ class / preferred term": soc}
        for arm in ARMS:
            arm_ids = set(adsl.loc[adsl.TRT01P == arm, "USUBJID"])
            ids = set(soc_df.loc[soc_df.TRT01P == arm, "USUBJID"])
            row[arm] = pct(len(ids.intersection(arm_ids)), denoms[arm])
        row[TOTAL] = pct(soc_df["USUBJID"].nunique(), denoms[TOTAL])
        rows.append(row)
        pts = soc_df.groupby("AEDECOD")["USUBJID"].nunique().sort_values(ascending=False).index
        for pt in pts:
            pt_df = soc_df[soc_df.AEDECOD == pt]
            row = {"System organ class / preferred term": "  " + pt}
            for arm in ARMS:
                arm_ids = set(adsl.loc[adsl.TRT01P == arm, "USUBJID"])
                ids = set(pt_df.loc[pt_df.TRT01P == arm, "USUBJID"])
                row[arm] = pct(len(ids.intersection(arm_ids)), denoms[arm])
            row[TOTAL] = pct(pt_df["USUBJID"].nunique(), denoms[TOTAL])
            rows.append(row)
    df = pd.DataFrame(rows)
    df.columns = ["System organ class / preferred term", f"{ARM_T} (N={denoms[ARM_T]})", f"{ARM_C} (N={denoms[ARM_C]})", f"Total (N={denoms[TOTAL]})"]
    stem = "t14_3_3_grade3_teae_by_soc_pt" if grade3_only else "t14_3_2_teae_by_soc_pt"
    title = "Table 14.3.3 Grade >=3 Treatment-Emergent Adverse Events by SOC and Preferred Term" if grade3_only else "Table 14.3.2 Treatment-Emergent Adverse Events by SOC and Preferred Term"
    write_table(df, stem, title, ["Subjects are counted once for each system organ class and preferred term."])
    return df


def table_lab_shift(adsl: pd.DataFrame, adlb: pd.DataFrame) -> pd.DataFrame:
    denoms = denom(adsl, "SAFFL")
    rows = []
    for param in ["ALT", "AST", "NEUT", "HGB"]:
        pdat = adlb[adlb.PARAMCD == param]
        rows.append({"Lab parameter / shift": pdat.PARAM.iloc[0], ARM_T: "", ARM_C: "", TOTAL: ""})
        for shift_label, condition in [
            ("  Any worsening from baseline", pdat.WORSTGR > pdat.BASEGR),
            ("  Worst grade >=3", pdat.WORSTGR >= 3),
            ("  Shift from grade 0-1 to grade >=3", (pdat.BASEGR <= 1) & (pdat.WORSTGR >= 3)),
        ]:
            row = {"Lab parameter / shift": shift_label}
            ids_all = set(pdat.loc[condition, "USUBJID"])
            for arm in ARMS:
                arm_ids = set(adsl.loc[adsl.TRT01P == arm, "USUBJID"])
                row[arm] = pct(len(ids_all.intersection(arm_ids)), denoms[arm])
            row[TOTAL] = pct(len(ids_all), denoms[TOTAL])
            rows.append(row)
    df = pd.DataFrame(rows)
    df.columns = ["Lab parameter / shift", f"{ARM_T} (N={denoms[ARM_T]})", f"{ARM_C} (N={denoms[ARM_C]})", f"Total (N={denoms[TOTAL]})"]
    write_table(df, "t14_3_4_lab_shift", "Table 14.3.4 Laboratory Shift Summary", ["Worst post-baseline CTCAE grade is simulated for portfolio demonstration."])
    return df


def listings(adsl: pd.DataFrame, adtte: pd.DataFrame, adae: pd.DataFrame) -> None:
    pfs = adtte[adtte.PARAMCD == "PFS"][["USUBJID", "AVAL", "CNSR"]].rename(columns={"AVAL": "PFS_MONTHS", "CNSR": "PFS_CNSR"})
    os = adtte[adtte.PARAMCD == "OS"][["USUBJID", "AVAL", "CNSR", "ADT"]].rename(columns={"AVAL": "OS_MONTHS", "CNSR": "OS_CNSR", "ADT": "DEATH_OR_CENSOR_DATE"})
    base = adsl[["USUBJID", "TRT01P", "AGE", "SEX", "ECOG", "PDL1CAT"]].merge(pfs, on="USUBJID").merge(os, on="USUBJID")
    death = base[base.OS_CNSR == 0].copy()
    death = death.sort_values("OS_MONTHS").head(60)
    write_listing(death, "l16_2_1_deaths", "Listing 16.2.1 Deaths", ["CNSR=0 indicates event/death in ADTTE OS."])

    sae = adae[(adae.TRTEMFL == "Y") & (adae.AESER == "Y")].copy()
    sae = sae[["USUBJID", "TRT01P", "AESEQ", "AEBODSYS", "AEDECOD", "AESTDT", "AEENDT", "AETOXGR", "AEREL", "AEACN", "AEOUT"]].sort_values(["TRT01P", "USUBJID", "AESEQ"])
    write_listing(sae.head(100), "l16_2_2_serious_adverse_events", "Listing 16.2.2 Serious Adverse Events", ["First 100 rows are shown if more than 100 events are present."])

    disc = adae[(adae.TRTEMFL == "Y") & (adae.AEACN == "DRUG WITHDRAWN")].copy()
    disc = disc[["USUBJID", "TRT01P", "AESEQ", "AEBODSYS", "AEDECOD", "AESTDT", "AETOXGR", "AESER", "AEREL", "AEOUT"]].sort_values(["TRT01P", "USUBJID", "AESEQ"])
    write_listing(disc.head(100), "l16_2_3_ae_discontinuations", "Listing 16.2.3 Adverse Events Leading to Treatment Discontinuation", ["First 100 rows are shown if more than 100 events are present."])


def plot_km(adtte: pd.DataFrame, paramcd: str, title: str, filename: str) -> None:
    data = adtte[(adtte.PARAMCD == paramcd) & (adtte.ANL01FL == "Y")].copy()
    plt.figure(figsize=(8, 5.2))
    for arm in ARMS:
        sub = data[data.TRT01P == arm]
        event = 1 - sub.CNSR.astype(int).to_numpy()
        curve = km_curve(sub.AVAL.to_numpy(), event)
        plt.step(curve.time, curve.survival, where="post", label=f"{arm} (N={len(sub)})")
    plt.xlabel("Months from randomization")
    plt.ylabel("Survival probability")
    plt.title(title)
    plt.ylim(0, 1.02)
    plt.grid(True, alpha=0.25)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(OUT_FIGURES / f"{filename}.png", dpi=180)
    plt.savefig(OUT_FIGURES / f"{filename}.pdf")
    plt.close()


def plot_forest(adtte: pd.DataFrame) -> pd.DataFrame:
    data = adtte[(adtte.PARAMCD == "PFS") & (adtte.ANL01FL == "Y")].copy()
    data["event"] = 1 - data.CNSR.astype(int)
    subgroups = [
        ("Age", "AGEGR1", ["<65", ">=65"]),
        ("Sex", "SEX", ["Male", "Female"]),
        ("ECOG", "ECOG", ["0", "1"]),
        ("Stage", "STAGE", ["IIIB/IIIC", "IV"]),
        ("PD-L1", "PDL1CAT", ["<1%", "1-49%", ">=50%"]),
        ("Region", "REGION", ["Asia", "Europe", "North America", "Rest of World"]),
    ]
    rows = []
    for label, var, levels in subgroups:
        for lev in levels:
            sub = data[data[var].astype(str) == str(lev)].copy()
            if len(sub) < 25 or sub["event"].sum() < 8 or sub.TRT01P.nunique() < 2:
                continue
            group = (sub.TRT01P == ARM_T).astype(int).to_numpy()
            res = cox_ph(sub.AVAL.to_numpy(), sub.event.to_numpy(), group)
            rows.append({"Subgroup": f"{label}: {lev}", "N": len(sub), "Events": int(sub.event.sum()), "HR": res["hr"], "LCL": res["lcl"], "UCL": res["ucl"]})
    forest = pd.DataFrame(rows)
    forest.to_csv(OUT_TABLES / "t14_2_4_pfs_forest_data.csv", index=False)
    # figure
    plt.figure(figsize=(8, max(4.5, 0.38 * len(forest))))
    y = np.arange(len(forest))
    hr = forest.HR.to_numpy()
    lo = forest.LCL.to_numpy()
    hi = forest.UCL.to_numpy()
    xerr = np.vstack([hr - lo, hi - hr])
    plt.errorbar(hr, y, xerr=xerr, fmt="o", capsize=3)
    plt.axvline(1.0, linestyle="--", linewidth=1)
    plt.yticks(y, [f"{s} (N={n})" for s, n in zip(forest.Subgroup, forest.N)])
    plt.xscale("log")
    plt.xlabel("Hazard ratio for PFS (ONC-305 + SOC vs Placebo + SOC)")
    plt.title("Figure 14.2.3 PFS Forest Plot by Baseline Subgroup")
    plt.grid(True, axis="x", alpha=0.25)
    plt.tight_layout()
    plt.savefig(OUT_FIGURES / "f14_2_3_pfs_forest.png", dpi=180)
    plt.savefig(OUT_FIGURES / "f14_2_3_pfs_forest.pdf")
    plt.close()
    return forest


def plot_ae_bar(adsl: pd.DataFrame, adae: pd.DataFrame) -> None:
    denoms = denom(adsl, "SAFFL")
    data = adae[adae.TRTEMFL == "Y"]
    top = data.groupby("AEDECOD")["USUBJID"].nunique().sort_values(ascending=False).head(10).index.tolist()
    plot_df = []
    for pt in top:
        for arm in ARMS:
            ids = data[(data.AEDECOD == pt) & (data.TRT01P == arm)]["USUBJID"].nunique()
            plot_df.append({"PT": pt, "Arm": arm, "Rate": 100 * ids / denoms[arm]})
    pdf = pd.DataFrame(plot_df)
    x = np.arange(len(top))
    width = 0.35
    plt.figure(figsize=(9, 5.4))
    vals_t = [pdf[(pdf.PT == pt) & (pdf.Arm == ARM_T)].Rate.iloc[0] for pt in top]
    vals_c = [pdf[(pdf.PT == pt) & (pdf.Arm == ARM_C)].Rate.iloc[0] for pt in top]
    plt.bar(x - width/2, vals_t, width, label=ARM_T)
    plt.bar(x + width/2, vals_c, width, label=ARM_C)
    plt.xticks(x, top, rotation=35, ha="right")
    plt.ylabel("Subjects with event (%)")
    plt.title("Figure 14.3.1 Top 10 TEAEs by Preferred Term")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_FIGURES / "f14_3_1_top_teae_bar.png", dpi=180)
    plt.savefig(OUT_FIGURES / "f14_3_1_top_teae_bar.pdf")
    plt.close()


def plot_waterfall(adrs: pd.DataFrame) -> None:
    data = adrs.dropna(subset=["BESTPCHG"]).sort_values("BESTPCHG").reset_index(drop=True)
    plt.figure(figsize=(10, 4.8))
    plt.bar(np.arange(len(data)), data.BESTPCHG)
    plt.axhline(-30, linestyle="--", linewidth=1)
    plt.axhline(20, linestyle="--", linewidth=1)
    plt.ylabel("Best percent change from baseline")
    plt.xlabel("Subjects sorted by best percent change")
    plt.title("Figure 14.2.4 Waterfall Plot of Best Tumor Change")
    plt.tight_layout()
    plt.savefig(OUT_FIGURES / "f14_2_4_waterfall_best_change.png", dpi=180)
    plt.savefig(OUT_FIGURES / "f14_2_4_waterfall_best_change.pdf")
    plt.close()


def generate_tlfs() -> None:
    ensure_dirs()
    d = load_adam()
    adsl, adtte, adae, adrs, adlb = d["adsl"], d["adtte"], d["adae"], d["adrs"], d["adlb"]

    # Ensure required string columns are treated as strings.
    for df in [adsl, adtte, adae, adrs, adlb]:
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str)

    table_demographics(adsl)
    table_disposition(adsl)
    table_exposure(adsl)
    survival_table(adtte, "PFS", "Table 14.2.1 Primary Efficacy Analysis: Progression-Free Survival", "t14_2_1_primary_pfs")
    survival_table(adtte, "OS", "Table 14.2.2 Key Secondary Efficacy Analysis: Overall Survival", "t14_2_2_overall_survival")
    table_response(adrs)
    table_safety_overview(adsl, adae)
    ae_by_soc_pt(adsl, adae, grade3_only=False)
    ae_by_soc_pt(adsl, adae, grade3_only=True)
    table_lab_shift(adsl, adlb)
    listings(adsl, adtte, adae)
    plot_km(adtte, "PFS", "Figure 14.2.1 Kaplan-Meier Curve for Progression-Free Survival", "f14_2_1_km_pfs")
    plot_km(adtte, "OS", "Figure 14.2.2 Kaplan-Meier Curve for Overall Survival", "f14_2_2_km_os")
    plot_forest(adtte)
    plot_ae_bar(adsl, adae)
    plot_waterfall(adrs)
    print(f"Generated TLFs in {OUT_TABLES}, {OUT_LISTINGS}, and {OUT_FIGURES}")


if __name__ == "__main__":
    generate_tlfs()
