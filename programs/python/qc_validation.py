from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from utils import DATA_RAW, DATA_ADAM, DATA_SPECS, OUT_TABLES, OUT_LISTINGS, OUT_FIGURES, QC, ensure_dirs, ARM_T, ARM_C


def check(name: str, condition: bool, detail: str, severity: str = "FAIL") -> dict[str, str]:
    return {"Check": name, "Status": "PASS" if bool(condition) else severity, "Detail": detail}


def exists(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def run_qc() -> pd.DataFrame:
    ensure_dirs()
    adsl = pd.read_csv(DATA_ADAM / "adsl.csv")
    adtte = pd.read_csv(DATA_ADAM / "adtte.csv")
    adae = pd.read_csv(DATA_ADAM / "adae.csv")
    adrs = pd.read_csv(DATA_ADAM / "adrs.csv")
    adlb = pd.read_csv(DATA_ADAM / "adlb.csv")
    raw_dm = pd.read_csv(DATA_RAW / "dm.csv")
    raw_ae = pd.read_csv(DATA_RAW / "ae.csv")

    rows: list[dict[str, str]] = []

    # Population and source-to-analysis checks.
    rows.append(check("ADSL subject uniqueness", adsl.USUBJID.is_unique, f"ADSL subjects={len(adsl)}, unique={adsl.USUBJID.nunique()}"))
    rows.append(check("ADSL equals raw DM count", len(adsl) == len(raw_dm), f"ADSL={len(adsl)}, DM={len(raw_dm)}"))
    rows.append(check("Treatment arms present", set(adsl.TRT01P.unique()) == {ARM_T, ARM_C}, f"Arms={sorted(adsl.TRT01P.unique())}"))
    rows.append(check("Planned and actual treatment match in simulation", (adsl.TRT01P == adsl.TRT01A).all(), "All actual treatments equal planned treatment"))
    rows.append(check("FAS flag complete", (adsl.FASFL == "Y").all(), f"FAS N={(adsl.FASFL == 'Y').sum()}"))
    rows.append(check("Safety flag complete", (adsl.SAFFL == "Y").all(), f"Safety N={(adsl.SAFFL == 'Y').sum()}"))
    rows.append(check("ITT flag complete", (adsl.ITTFL == "Y").all(), f"ITT N={(adsl.ITTFL == 'Y').sum()}"))
    rows.append(check("Randomization before or on treatment start", (pd.to_datetime(adsl.RANDDT) <= pd.to_datetime(adsl.TRTSDT)).all(), "RANDDT <= TRTSDT for all subjects"))
    rows.append(check("Treatment start before or on treatment end", (pd.to_datetime(adsl.TRTSDT) <= pd.to_datetime(adsl.TRTEDT)).all(), "TRTSDT <= TRTEDT for all subjects"))
    rows.append(check("Positive treatment duration", (adsl.TRTDURD > 0).all(), f"Minimum TRTDURD={adsl.TRTDURD.min()}"))
    rows.append(check("Randomization roughly balanced", abs((adsl.TRT01P == ARM_T).sum() - (adsl.TRT01P == ARM_C).sum()) <= 5, f"{ARM_T}={(adsl.TRT01P == ARM_T).sum()}, {ARM_C}={(adsl.TRT01P == ARM_C).sum()}"))

    # Time-to-event checks.
    rows.append(check("ADTTE has two records per subject", adtte.groupby("USUBJID").size().eq(2).all(), f"ADTTE rows={len(adtte)}, expected={2*len(adsl)}"))
    rows.append(check("ADTTE unique subject/endpoint", not adtte.duplicated(["USUBJID", "PARAMCD"]).any(), "No duplicate USUBJID/PARAMCD records"))
    rows.append(check("ADTTE endpoints are PFS and OS", set(adtte.PARAMCD.unique()) == {"PFS", "OS"}, f"PARAMCD={sorted(adtte.PARAMCD.unique())}"))
    rows.append(check("ADTTE censoring values valid", set(adtte.CNSR.unique()).issubset({0, 1}), f"CNSR values={list(map(int, sorted(adtte.CNSR.dropna().unique())))}"))
    rows.append(check("ADTTE event description consistent", set(adtte.EVNTDESC.unique()).issubset({"Event", "Censored"}), f"EVNTDESC={sorted(adtte.EVNTDESC.unique())}"))
    rows.append(check("ADTTE event/censor consistency", ((adtte.CNSR.eq(0) & adtte.EVNTDESC.eq("Event")) | (adtte.CNSR.eq(1) & adtte.EVNTDESC.eq("Censored"))).all(), "CNSR and EVNTDESC agree"))
    rows.append(check("ADTTE positive times", (adtte.AVAL > 0).all(), f"Minimum AVAL={adtte.AVAL.min():.2f}"))
    rows.append(check("ADTTE dates after randomization", (pd.to_datetime(adtte.ADT) >= pd.to_datetime(adtte.STARTDT)).all(), "ADT >= STARTDT for all records"))
    rows.append(check("ADTTE analysis flag complete", (adtte.ANL01FL == "Y").all(), f"ANL01FL Y count={(adtte.ANL01FL == 'Y').sum()}"))

    # Response/lab/safety checks.
    rows.append(check("ADRS one record per subject", adrs.USUBJID.is_unique, f"ADRS subjects={adrs.USUBJID.nunique()}"))
    rows.append(check("ADRS BOR values valid", set(adrs.BOR.unique()).issubset({"CR", "PR", "SD", "PD", "NE"}), f"BOR={sorted(adrs.BOR.unique())}"))
    rows.append(check("ADRS ORR flag consistent", (((adrs.BOR.isin(["CR", "PR"])) & (adrs.ORRFL == "Y")) | ((~adrs.BOR.isin(["CR", "PR"])) & (adrs.ORRFL == "N"))).all(), "ORRFL equals Y for CR/PR only"))
    rows.append(check("ADRS DCR flag consistent", (((adrs.BOR.isin(["CR", "PR", "SD"])) & (adrs.DCRFL == "Y")) | ((~adrs.BOR.isin(["CR", "PR", "SD"])) & (adrs.DCRFL == "N"))).all(), "DCRFL equals Y for CR/PR/SD only"))
    rows.append(check("ADLB four parameters per subject", adlb.groupby("USUBJID").size().eq(4).all(), f"ADLB rows={len(adlb)}, expected={4*len(adsl)}"))
    rows.append(check("ADLB unique subject/parameter", not adlb.duplicated(["USUBJID", "PARAMCD"]).any(), "No duplicate lab records by subject/parameter"))
    rows.append(check("ADLB grades valid", set(adlb.BASEGR.unique()).union(set(adlb.WORSTGR.unique())).issubset({0, 1, 2, 3, 4}), f"Grades={sorted(set(adlb.BASEGR.unique()).union(set(adlb.WORSTGR.unique())))}"))
    rows.append(check("ADAE row count matches raw AE", len(adae) == len(raw_ae), f"ADAE={len(adae)}, raw AE={len(raw_ae)}"))
    rows.append(check("ADAE unique subject/sequence", not adae.duplicated(["USUBJID", "AESEQ"]).any(), "No duplicate USUBJID/AESEQ records"))
    rows.append(check("ADAE treatment-emergent dates", (pd.to_datetime(adae.AESTDT) >= pd.to_datetime(adae.TRTSDT)).all(), "All AE start dates are on or after treatment start"))
    rows.append(check("ADAE end dates after start dates", (pd.to_datetime(adae.AEENDT) >= pd.to_datetime(adae.AESTDT)).all(), "AEENDT >= AESTDT"))
    rows.append(check("ADAE toxicity grades valid", set(adae.AETOXGR.unique()).issubset({1, 2, 3, 4, 5}), f"Grades={list(map(int, sorted(adae.AETOXGR.dropna().unique())))}"))
    rows.append(check("ADAE serious flag valid", set(adae.AESER.unique()).issubset({"Y", "N"}), f"AESER={sorted(adae.AESER.unique())}"))
    rows.append(check("ADAE relatedness flag valid", set(adae.AEREL.unique()).issubset({"Y", "N"}), f"AEREL={sorted(adae.AEREL.unique())}"))
    rows.append(check("ADAE fatal flag valid", set(adae.AESDTH.unique()).issubset({"Y", "N"}), f"AESDTH={sorted(adae.AESDTH.unique())}"))
    rows.append(check("ADAE occurrence flags valid", set(adae.AOCCFL.dropna().unique()).issubset({"Y"}), f"AOCCFL values={sorted(map(str, adae.AOCCFL.dropna().unique()))}", severity="WARN"))

    # Metadata checks.
    spec_path = DATA_SPECS / "adam_spec.csv"
    define_path = DATA_SPECS / "define_like_metadata.xml"
    rows.append(check("ADaM specification exists", exists(spec_path), f"{spec_path.name} present={exists(spec_path)}"))
    rows.append(check("Define-like metadata exists", exists(define_path), f"{define_path.name} present={exists(define_path)}"))
    if exists(spec_path):
        spec = pd.read_csv(spec_path)
        dataset_col = "DATASET" if "DATASET" in spec.columns else ("Dataset" if "Dataset" in spec.columns else None)
        if dataset_col is None:
            rows.append(check("ADaM spec covers five datasets", False, f"No dataset column found; columns={list(spec.columns)}"))
        else:
            datasets = set(spec[dataset_col].dropna().astype(str).str.upper().unique())
            rows.append(check("ADaM spec covers five datasets", datasets.issuperset({"ADSL", "ADTTE", "ADAE", "ADRS", "ADLB"}), f"Datasets={sorted(datasets)}"))

    # Output presence checks.
    expected_tables = [
        "t14_1_1_demographics", "t14_1_2_disposition", "t14_1_3_exposure", "t14_2_1_primary_pfs",
        "t14_2_2_overall_survival", "t14_2_3_best_overall_response", "t14_3_1_safety_overview",
        "t14_3_2_teae_by_soc_pt", "t14_3_3_grade3_teae_by_soc_pt", "t14_3_4_lab_shift",
    ]
    for stem in expected_tables:
        ok = all(exists(OUT_TABLES / f"{stem}.{ext}") for ext in ["csv", "md", "txt"])
        rows.append(check(f"Output table exists: {stem}", ok, f"{stem}.csv/md/txt present={ok}"))

    expected_listings = ["l16_2_1_deaths", "l16_2_2_serious_adverse_events", "l16_2_3_ae_discontinuations"]
    for stem in expected_listings:
        ok = all(exists(OUT_LISTINGS / f"{stem}.{ext}") for ext in ["csv", "md", "txt"])
        rows.append(check(f"Output listing exists: {stem}", ok, f"{stem}.csv/md/txt present={ok}"))

    expected_figures = [
        "f14_2_1_km_pfs.png", "f14_2_2_km_os.png", "f14_2_3_pfs_forest.png",
        "f14_2_4_waterfall_best_change.png", "f14_3_1_top_teae_bar.png",
    ]
    for fname in expected_figures:
        rows.append(check(f"Output figure exists: {fname}", exists(OUT_FIGURES / fname), f"{fname} present={exists(OUT_FIGURES / fname)}"))

    # Programming assets.
    root = DATA_ADAM.parents[1]
    for rel in ["programs/python/run_all.py", "programs/python/generate_tlfs.py", "programs/sas/01_primary_pfs.sas", "programs/r/01_primary_pfs.R", "requirements.txt"]:
        rows.append(check(f"Programming asset exists: {rel}", exists(root / rel), f"{rel} present={exists(root / rel)}"))

    qc_df = pd.DataFrame(rows)
    qc_df.to_csv(QC / "validation_checks.csv", index=False)

    summary = []
    summary.append("# Validation Report")
    summary.append("")
    summary.append("This report provides reproducibility and consistency checks for the simulated ONC-305-301 statistical submission portfolio.")
    summary.append("")
    summary.append(f"Total checks: {len(qc_df)}")
    summary.append(f"PASS: {(qc_df.Status == 'PASS').sum()}")
    summary.append(f"WARN: {(qc_df.Status == 'WARN').sum()}")
    summary.append(f"FAIL: {(qc_df.Status == 'FAIL').sum()}")
    summary.append("")
    summary.append(qc_df.to_markdown(index=False))
    (QC / "validation_report.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"QC complete: {(qc_df.Status == 'PASS').sum()} PASS, {(qc_df.Status == 'WARN').sum()} WARN, {(qc_df.Status == 'FAIL').sum()} FAIL")
    return qc_df


if __name__ == "__main__":
    run_qc()
