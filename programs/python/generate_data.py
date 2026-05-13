from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

from utils import DATA_RAW, ensure_dirs, ARM_T, ARM_C, STUDY_ID, SEED


def _random_dates(rng, n, start="2024-01-02", end="2024-08-31"):
    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end)
    days = (end_dt - start_dt).days
    offsets = rng.integers(0, days + 1, n)
    return start_dt + pd.to_timedelta(offsets, unit="D")


def _weibull_event_time(rng, hazard, shape=1.18):
    # Weibull proportional-hazards parameterization: S(t) = exp(-hazard * t^shape)
    u = rng.uniform(size=len(hazard))
    return (-np.log(u) / hazard) ** (1.0 / shape)


def generate_trial_data(n: int = 420, seed: int = SEED) -> None:
    """Generate a realistic simulated Phase III oncology dataset.

    The trial is intentionally simulated with a clear treatment effect so that the portfolio
    contains interpretable survival, response, and safety outputs while remaining fully synthetic.
    """
    ensure_dirs()
    rng = np.random.default_rng(seed)

    subjid = np.arange(1, n + 1)
    usubjid = [f"{STUDY_ID}-{i:04d}" for i in subjid]
    siteid = rng.choice([f"{i:03d}" for i in range(101, 126)], size=n, replace=True)
    region = rng.choice(["Asia", "Europe", "North America", "Rest of World"], size=n, p=[0.56, 0.22, 0.14, 0.08])
    country_map = {
        "Asia": ["China", "Japan", "South Korea", "Singapore"],
        "Europe": ["UK", "Germany", "France", "Poland"],
        "North America": ["United States", "Canada"],
        "Rest of World": ["Australia", "Brazil", "South Africa"],
    }
    country = [rng.choice(country_map[r]) for r in region]
    age = np.clip(rng.normal(62, 9, n).round().astype(int), 34, 82)
    sex = rng.choice(["Male", "Female"], size=n, p=[0.57, 0.43])
    race = rng.choice(["Asian", "White", "Black or African American", "Other"], size=n, p=[0.58, 0.31, 0.05, 0.06])
    ecog = rng.choice(["0", "1"], size=n, p=[0.42, 0.58])
    stage = rng.choice(["IIIB/IIIC", "IV"], size=n, p=[0.18, 0.82])
    pdl1 = rng.choice(["<1%", "1-49%", ">=50%"], size=n, p=[0.34, 0.41, 0.25])
    histology = rng.choice(["Adenocarcinoma", "Squamous", "Other NSCLC"], size=n, p=[0.68, 0.23, 0.09])
    disease_months = np.clip(rng.gamma(2.2, 4.8, n), 0.5, 42).round(1)

    # Stratified-style blocked randomization within ECOG x PD-L1 strata.
    arm = np.empty(n, dtype=object)
    df_strat = pd.DataFrame({"idx": np.arange(n), "ecog": ecog, "pdl1": pdl1})
    for _, g in df_strat.groupby(["ecog", "pdl1"]):
        idx = g["idx"].to_numpy()
        rng.shuffle(idx)
        labels = np.array([ARM_T, ARM_C] * ((len(idx) + 1) // 2), dtype=object)[: len(idx)]
        rng.shuffle(labels)
        arm[idx] = labels

    randdt = _random_dates(rng, n)
    trtsdt = randdt + pd.to_timedelta(rng.integers(0, 4, n), unit="D")
    cutoff = pd.Timestamp("2026-01-31")
    admin_months = ((cutoff - trtsdt).days / 30.4375).astype(float)

    trt_ind = (arm == ARM_T).astype(int)
    cov_hr = np.ones(n)
    cov_hr *= np.where(ecog == "1", 1.22, 1.00)
    cov_hr *= np.where(stage == "IV", 1.18, 1.00)
    cov_hr *= np.where(pdl1 == ">=50%", 0.88, np.where(pdl1 == "<1%", 1.08, 1.0))
    cov_hr *= np.where(age >= 65, 1.06, 1.0)

    # PFS simulation: median control approx 7.2 months, HR about 0.63.
    baseline_haz_pfs = np.log(2) / (7.2**1.18)
    hazard_pfs = baseline_haz_pfs * cov_hr * np.where(trt_ind == 1, 0.63, 1.00)
    true_pfs = _weibull_event_time(rng, hazard_pfs, shape=1.18)
    dropout_pfs = rng.uniform(10, 27, n)
    pfs_obs = np.minimum.reduce([true_pfs, dropout_pfs, admin_months])
    pfs_event = (true_pfs <= pfs_obs + 1e-8).astype(int)
    pfs_dt = trtsdt + pd.to_timedelta(np.round(pfs_obs * 30.4375).astype(int), unit="D")

    # OS simulation: partly correlated with PFS and longer than PFS; median control approx 17 months.
    baseline_haz_os = np.log(2) / (17.0**1.05)
    hazard_os = baseline_haz_os * (0.95 * cov_hr + 0.05) * np.where(trt_ind == 1, 0.76, 1.00)
    true_os_raw = _weibull_event_time(rng, hazard_os, shape=1.05)
    true_os = np.maximum(true_os_raw, true_pfs + rng.exponential(4.0, n))
    dropout_os = rng.uniform(14, 34, n)
    os_obs = np.minimum.reduce([true_os, dropout_os, admin_months])
    os_event = (true_os <= os_obs + 1e-8).astype(int)
    os_dt = trtsdt + pd.to_timedelta(np.round(os_obs * 30.4375).astype(int), unit="D")

    # Response probabilities: treatment improves ORR.
    bor = []
    best_pct_change = []
    for i in range(n):
        high = pdl1[i] == ">=50%"
        if arm[i] == ARM_T:
            probs = np.array([0.05, 0.41, 0.32, 0.17, 0.05])
            if high:
                probs += np.array([0.02, 0.05, -0.02, -0.04, -0.01])
        else:
            probs = np.array([0.02, 0.25, 0.35, 0.30, 0.08])
            if high:
                probs += np.array([0.01, 0.03, -0.01, -0.02, -0.01])
        probs = np.clip(probs, 0.01, None)
        probs = probs / probs.sum()
        cat = rng.choice(["CR", "PR", "SD", "PD", "NE"], p=probs)
        bor.append(cat)
        if cat == "CR":
            change = rng.normal(-78, 10)
        elif cat == "PR":
            change = rng.normal(-45, 12)
        elif cat == "SD":
            change = rng.normal(-5, 13)
        elif cat == "PD":
            change = rng.normal(28, 18)
        else:
            change = np.nan
        best_pct_change.append(change)

    # Exposure duration: usually until progression or censoring, with discontinuation margin.
    exposure_months = np.minimum(pfs_obs + rng.uniform(0.0, 1.2, n), admin_months)
    exposure_months = np.maximum(exposure_months, rng.uniform(0.5, 2.5, n))
    trtedt = trtsdt + pd.to_timedelta(np.round(exposure_months * 30.4375).astype(int), unit="D")
    trtedt = pd.Series(trtedt).where(pd.Series(trtedt) <= cutoff, cutoff)
    trtdurd = ((trtedt - trtsdt).dt.days + 1).astype(int)
    rel_dose_intensity = np.clip(rng.normal(93 - 3 * trt_ind, 9, n), 55, 105).round(1)

    dm = pd.DataFrame({
        "STUDYID": STUDY_ID,
        "USUBJID": usubjid,
        "SUBJID": [f"{i:04d}" for i in subjid],
        "SITEID": siteid,
        "COUNTRY": country,
        "REGION": region,
        "ARM": arm,
        "ACTARM": arm,
        "RANDDT": pd.to_datetime(randdt).strftime("%Y-%m-%d"),
        "TRTSDT": pd.to_datetime(trtsdt).strftime("%Y-%m-%d"),
        "TRTEDT": pd.to_datetime(trtedt).dt.strftime("%Y-%m-%d"),
        "AGE": age,
        "AGEGR1": np.where(age < 65, "<65", ">=65"),
        "SEX": sex,
        "RACE": race,
        "ECOG": ecog,
        "STAGE": stage,
        "PDL1CAT": pdl1,
        "HISTOLOGY": histology,
        "DISEASE_MONTHS": disease_months,
        "TRTDURD": trtdurd,
        "RDI": rel_dose_intensity,
        "FASFL": "Y",
        "SAFFL": "Y",
    })

    tte = pd.DataFrame({
        "STUDYID": STUDY_ID,
        "USUBJID": np.repeat(usubjid, 2),
        "PARAMCD": np.tile(["PFS", "OS"], n),
        "PARAM": np.tile(["Progression-Free Survival", "Overall Survival"], n),
        "AVAL": np.ravel(np.column_stack([pfs_obs, os_obs])).round(2),
        "AVALD": np.ravel(np.column_stack([pfs_obs * 30.4375, os_obs * 30.4375])).round().astype(int),
        "CNSR": np.ravel(np.column_stack([1 - pfs_event, 1 - os_event])).astype(int),
        "EVENT": np.ravel(np.column_stack([pfs_event, os_event])).astype(int),
        "ADT": pd.to_datetime(np.ravel(np.column_stack([pfs_dt, os_dt]))).strftime("%Y-%m-%d"),
        "EVNTDESC": np.where(np.ravel(np.column_stack([pfs_event, os_event])).astype(int) == 1, "Event", "Censored"),
    })

    rs = pd.DataFrame({
        "STUDYID": STUDY_ID,
        "USUBJID": usubjid,
        "BOR": bor,
        "ORRFL": ["Y" if b in ["CR", "PR"] else "N" for b in bor],
        "DCRFL": ["Y" if b in ["CR", "PR", "SD"] else "N" for b in bor],
        "BESTPCHG": np.round(best_pct_change, 1),
    })

    # Disposition.
    ds_reasons = []
    for i in range(n):
        if os_event[i] == 1 and os_obs[i] <= exposure_months[i] + 0.5:
            ds_reasons.append("Death")
        elif pfs_event[i] == 1:
            ds_reasons.append("Progressive disease")
        else:
            ds_reasons.append(rng.choice(["Completed treatment", "Ongoing", "Adverse event", "Withdrawal by subject", "Other"], p=[0.27, 0.36, 0.13, 0.12, 0.12]))
    ds = pd.DataFrame({
        "STUDYID": STUDY_ID,
        "USUBJID": usubjid,
        "DSCAT": "DISPOSITION EVENT",
        "DSDECOD": ds_reasons,
        "DSDT": pd.to_datetime(trtedt).dt.strftime("%Y-%m-%d"),
    })

    # Adverse events.
    ae_catalog = [
        ("GASTROINTESTINAL DISORDERS", "Nausea", 0.24, 0.31, 0.06),
        ("GASTROINTESTINAL DISORDERS", "Diarrhoea", 0.16, 0.26, 0.05),
        ("GENERAL DISORDERS", "Fatigue", 0.28, 0.34, 0.06),
        ("METABOLISM AND NUTRITION DISORDERS", "Decreased appetite", 0.15, 0.23, 0.04),
        ("BLOOD AND LYMPHATIC SYSTEM DISORDERS", "Anaemia", 0.18, 0.22, 0.10),
        ("BLOOD AND LYMPHATIC SYSTEM DISORDERS", "Neutropenia", 0.08, 0.18, 0.16),
        ("INFECTIONS AND INFESTATIONS", "Pneumonia", 0.06, 0.07, 0.18),
        ("SKIN AND SUBCUTANEOUS TISSUE DISORDERS", "Rash", 0.07, 0.13, 0.03),
        ("HEPATOBILIARY DISORDERS", "Alanine aminotransferase increased", 0.06, 0.15, 0.12),
        ("RESPIRATORY, THORACIC AND MEDIASTINAL DISORDERS", "Dyspnoea", 0.10, 0.11, 0.09),
        ("NERVOUS SYSTEM DISORDERS", "Headache", 0.09, 0.11, 0.01),
        ("MUSCULOSKELETAL AND CONNECTIVE TISSUE DISORDERS", "Arthralgia", 0.08, 0.10, 0.01),
        ("GENERAL DISORDERS", "Pyrexia", 0.07, 0.09, 0.04),
        ("INVESTIGATIONS", "Weight decreased", 0.05, 0.08, 0.02),
        ("CARDIAC DISORDERS", "Tachycardia", 0.03, 0.04, 0.04),
    ]
    ae_rows = []
    aeseq = {u: 0 for u in usubjid}
    for i, u in enumerate(usubjid):
        for soc, pt, p_ctrl, p_trt, p_gr3 in ae_catalog:
            p = p_trt if arm[i] == ARM_T else p_ctrl
            # Slightly more AEs in older/ECOG1 patients.
            p_adj = min(0.85, p * (1.08 if age[i] >= 65 else 1.0) * (1.08 if ecog[i] == "1" else 1.0))
            if rng.uniform() < p_adj:
                aeseq[u] += 1
                grade_probs = np.array([0.48, 0.34, 0.13, 0.04, 0.01])
                grade_probs[2:] *= (1 + 2.0 * p_gr3)
                grade_probs = grade_probs / grade_probs.sum()
                grade = int(rng.choice([1, 2, 3, 4, 5], p=grade_probs))
                serious = "Y" if (grade >= 4 or rng.uniform() < (0.06 + 0.12 * (grade >= 3))) else "N"
                related = "Y" if rng.uniform() < (0.62 if arm[i] == ARM_T else 0.38) else "N"
                ae_day = int(rng.integers(1, max(2, min(trtdurd[i], 540))))
                dur = int(rng.integers(3, 29))
                start = pd.Timestamp(trtsdt[i]) + pd.Timedelta(days=ae_day)
                end = min(start + pd.Timedelta(days=dur), pd.Timestamp(trtedt.iloc[i]))
                discont = "Y" if (grade >= 3 and rng.uniform() < 0.10) or grade == 5 else "N"
                outcome = "Fatal" if grade == 5 else rng.choice(["Recovered/resolved", "Recovering/resolving", "Not recovered/not resolved"], p=[0.62, 0.25, 0.13])
                ae_rows.append({
                    "STUDYID": STUDY_ID,
                    "USUBJID": u,
                    "AESEQ": aeseq[u],
                    "AEBODSYS": soc,
                    "AEDECOD": pt,
                    "AETERM": pt.upper(),
                    "AESTDT": start.strftime("%Y-%m-%d"),
                    "AEENDT": end.strftime("%Y-%m-%d"),
                    "AETOXGR": grade,
                    "AESER": serious,
                    "AEREL": related,
                    "AEACN": "DRUG WITHDRAWN" if discont == "Y" else rng.choice(["DOSE NOT CHANGED", "DOSE REDUCED", "DRUG INTERRUPTED"], p=[0.68, 0.15, 0.17]),
                    "AEOUT": outcome,
                    "AESDTH": "Y" if outcome == "Fatal" else "N",
                    "TRTEMFL": "Y",
                })
    ae = pd.DataFrame(ae_rows)

    # Lab shift data for four lab parameters.
    lab_params = [
        ("ALT", "Alanine aminotransferase", 0.10, 0.17),
        ("AST", "Aspartate aminotransferase", 0.09, 0.15),
        ("NEUT", "Neutrophils", 0.06, 0.14),
        ("HGB", "Hemoglobin", 0.12, 0.16),
    ]
    lab_rows = []
    for i, u in enumerate(usubjid):
        for paramcd, param, p_ctrl, p_trt in lab_params:
            base_grade = int(rng.choice([0, 1, 2], p=[0.88, 0.10, 0.02]))
            p_worse = p_trt if arm[i] == ARM_T else p_ctrl
            if rng.uniform() < p_worse:
                worst_grade = min(4, base_grade + int(rng.choice([1, 2, 3], p=[0.70, 0.23, 0.07])))
            else:
                worst_grade = base_grade
            lab_rows.append({
                "STUDYID": STUDY_ID,
                "USUBJID": u,
                "PARAMCD": paramcd,
                "PARAM": param,
                "BASEGR": base_grade,
                "WORSTGR": worst_grade,
                "SHIFT": f"{base_grade} to {worst_grade}",
            })
    lb = pd.DataFrame(lab_rows)

    # Exposure dataset.
    ex = pd.DataFrame({
        "STUDYID": STUDY_ID,
        "USUBJID": usubjid,
        "EXTRT": arm,
        "EXSTDTC": pd.to_datetime(trtsdt).strftime("%Y-%m-%d"),
        "EXENDTC": pd.to_datetime(trtedt).dt.strftime("%Y-%m-%d"),
        "EXDURD": trtdurd,
        "RDI": rel_dose_intensity,
    })

    dm.to_csv(DATA_RAW / "dm.csv", index=False)
    tte.to_csv(DATA_RAW / "tte.csv", index=False)
    rs.to_csv(DATA_RAW / "rs.csv", index=False)
    ds.to_csv(DATA_RAW / "ds.csv", index=False)
    ae.to_csv(DATA_RAW / "ae.csv", index=False)
    lb.to_csv(DATA_RAW / "lb.csv", index=False)
    ex.to_csv(DATA_RAW / "ex.csv", index=False)

    manifest = pd.DataFrame([
        {"dataset": "dm", "rows": len(dm), "description": "Subject-level raw demographics/randomization"},
        {"dataset": "tte", "rows": len(tte), "description": "Time-to-event source records for PFS and OS"},
        {"dataset": "rs", "rows": len(rs), "description": "Best overall response and tumor change"},
        {"dataset": "ds", "rows": len(ds), "description": "Disposition records"},
        {"dataset": "ae", "rows": len(ae), "description": "Treatment-emergent adverse events"},
        {"dataset": "lb", "rows": len(lb), "description": "Laboratory grade shift records"},
        {"dataset": "ex", "rows": len(ex), "description": "Exposure and relative dose intensity"},
    ])
    manifest.to_csv(DATA_RAW / "raw_manifest.csv", index=False)
    print(f"Generated raw data in {DATA_RAW}")


if __name__ == "__main__":
    generate_trial_data()
