from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable, List, Tuple, Dict, Any

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_ADAM = ROOT / "data" / "adam"
DATA_SPECS = ROOT / "data" / "specs"
OUT_TABLES = ROOT / "outputs" / "tables"
OUT_LISTINGS = ROOT / "outputs" / "listings"
OUT_FIGURES = ROOT / "outputs" / "figures"
OUT_REPORTS = ROOT / "outputs" / "reports"
DOCS = ROOT / "docs"
QC = ROOT / "qc"

ARM_T = "ONC-305 + SOC"
ARM_C = "Placebo + SOC"
ARMS = [ARM_T, ARM_C]
TOTAL = "Total"
STUDY_ID = "ONC-305-301"
SEED = 202602


def ensure_dirs() -> None:
    for p in [DATA_RAW, DATA_ADAM, DATA_SPECS, OUT_TABLES, OUT_LISTINGS, OUT_FIGURES, OUT_REPORTS, DOCS, QC]:
        p.mkdir(parents=True, exist_ok=True)


def pct(n: int | float, denom: int | float) -> str:
    if denom == 0 or pd.isna(denom):
        return "0 (0.0%)"
    return f"{int(n)} ({100*float(n)/float(denom):.1f}%)"


def n_pct(series: pd.Series, denom: int) -> str:
    return pct(series.sum(), denom)


def mean_sd(x: pd.Series) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if len(x) == 0:
        return "NA"
    return f"{x.mean():.1f} ({x.std(ddof=1):.1f})"


def median_range(x: pd.Series) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if len(x) == 0:
        return "NA"
    return f"{x.median():.1f} ({x.min():.1f}, {x.max():.1f})"


def q1_q3(x: pd.Series) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if len(x) == 0:
        return "NA"
    return f"{x.median():.1f} ({x.quantile(.25):.1f}, {x.quantile(.75):.1f})"


def fmt_p(p: float) -> str:
    if pd.isna(p):
        return "NA"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def fmt_ci(lo: float, hi: float, decimals: int = 2) -> str:
    if pd.isna(lo) or pd.isna(hi):
        return "NA"
    return f"({lo:.{decimals}f}, {hi:.{decimals}f})"


def df_to_markdown(df: pd.DataFrame, title: str | None = None, footnotes: list[str] | None = None) -> str:
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
        lines.append("")
    lines.append(df.to_markdown(index=False))
    if footnotes:
        lines.append("")
        for ft in footnotes:
            lines.append(f"* {ft}")
    lines.append("")
    return "\n".join(lines)


def write_table(df: pd.DataFrame, stem: str, title: str, footnotes: list[str] | None = None) -> None:
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_TABLES / f"{stem}.csv", index=False)
    (OUT_TABLES / f"{stem}.md").write_text(df_to_markdown(df, title=title, footnotes=footnotes), encoding="utf-8")
    # TXT is useful for conservative review systems and resembles legacy TLF output.
    with open(OUT_TABLES / f"{stem}.txt", "w", encoding="utf-8") as f:
        if title:
            f.write(title + "\n")
            f.write("=" * len(title) + "\n\n")
        f.write(df.to_string(index=False))
        if footnotes:
            f.write("\n\n")
            for ft in footnotes:
                f.write(f"* {ft}\n")


def write_listing(df: pd.DataFrame, stem: str, title: str, footnotes: list[str] | None = None) -> None:
    OUT_LISTINGS.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_LISTINGS / f"{stem}.csv", index=False)
    (OUT_LISTINGS / f"{stem}.md").write_text(df_to_markdown(df, title=title, footnotes=footnotes), encoding="utf-8")
    with open(OUT_LISTINGS / f"{stem}.txt", "w", encoding="utf-8") as f:
        if title:
            f.write(title + "\n")
            f.write("=" * len(title) + "\n\n")
        f.write(df.to_string(index=False))
        if footnotes:
            f.write("\n\n")
            for ft in footnotes:
                f.write(f"* {ft}\n")


def km_curve(time: np.ndarray, event: np.ndarray) -> pd.DataFrame:
    """Kaplan-Meier curve with Greenwood standard error.

    Parameters
    ----------
    time: observed times, positive numeric
    event: 1 for event, 0 for censored
    """
    df = pd.DataFrame({"time": time, "event": event}).dropna().sort_values("time")
    event_times = np.sort(df.loc[df["event"] == 1, "time"].unique())
    surv = 1.0
    var_term = 0.0
    rows = [{"time": 0.0, "survival": 1.0, "se": 0.0, "n_risk": len(df), "n_event": 0}]
    for t in event_times:
        at_risk = (df["time"] >= t).sum()
        d = ((df["time"] == t) & (df["event"] == 1)).sum()
        if at_risk <= 0:
            continue
        surv *= (1 - d / at_risk)
        if at_risk - d > 0:
            var_term += d / (at_risk * (at_risk - d))
        se = surv * math.sqrt(var_term) if var_term >= 0 else np.nan
        rows.append({"time": float(t), "survival": float(surv), "se": float(se), "n_risk": int(at_risk), "n_event": int(d)})
    return pd.DataFrame(rows)


def km_estimate_at(time: np.ndarray, event: np.ndarray, at: float) -> float:
    curve = km_curve(time, event)
    sub = curve[curve["time"] <= at]
    if sub.empty:
        return 1.0
    return float(sub.iloc[-1]["survival"])


def km_median(time: np.ndarray, event: np.ndarray) -> float:
    curve = km_curve(time, event)
    hit = curve[curve["survival"] <= 0.5]
    if hit.empty:
        return np.nan
    return float(hit.iloc[0]["time"])


def bootstrap_km_median_ci(time: np.ndarray, event: np.ndarray, n_boot: int = 300, seed: int = SEED) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    n = len(time)
    med = km_median(time, event)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        m = km_median(np.asarray(time)[idx], np.asarray(event)[idx])
        if not np.isnan(m):
            vals.append(m)
    if len(vals) < 20:
        return med, np.nan, np.nan
    return med, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def logrank_test(time: np.ndarray, event: np.ndarray, group: np.ndarray) -> tuple[float, float]:
    """Two-sample log-rank test. group should be 0/1."""
    df = pd.DataFrame({"time": time, "event": event, "group": group}).dropna()
    event_times = np.sort(df.loc[df["event"] == 1, "time"].unique())
    O1 = E1 = V1 = 0.0
    for t in event_times:
        risk = df["time"] >= t
        n = risk.sum()
        n1 = (risk & (df["group"] == 1)).sum()
        d = ((df["time"] == t) & (df["event"] == 1)).sum()
        d1 = ((df["time"] == t) & (df["event"] == 1) & (df["group"] == 1)).sum()
        if n <= 1:
            continue
        O1 += d1
        E1 += d * n1 / n
        V1 += (n1 * (n - n1) * d * (n - d)) / (n**2 * (n - 1))
    z = (O1 - E1) / math.sqrt(V1) if V1 > 0 else np.nan
    chi2 = z**2 if not pd.isna(z) else np.nan
    p = 1 - stats.chi2.cdf(chi2, 1) if not pd.isna(chi2) else np.nan
    return float(chi2), float(p)


def cox_ph(time: np.ndarray, event: np.ndarray, group: np.ndarray, covariates: pd.DataFrame | None = None) -> dict[str, float]:
    """Cox PH model with treatment group 1 vs 0 using statsmodels PHReg.

    Returns HR, CI, p-value. Falls back to log-rank approximation if PHReg fails.
    """
    try:
        import statsmodels.api as sm
        from statsmodels.duration.hazard_regression import PHReg
        X = pd.DataFrame({"trt": group.astype(float)})
        if covariates is not None and not covariates.empty:
            X = pd.concat([X.reset_index(drop=True), covariates.reset_index(drop=True)], axis=1)
        # Drop rows with invalid time/event/covariates
        model_df = X.copy()
        model_df["time"] = np.asarray(time, dtype=float)
        model_df["event"] = np.asarray(event, dtype=int)
        model_df = model_df.dropna()
        mod = PHReg(model_df["time"], model_df.drop(columns=["time", "event"]), status=model_df["event"], ties="breslow")
        res = mod.fit(disp=False)
        beta = float(res.params[0])
        se = float(res.bse[0])
        hr = math.exp(beta)
        lo = math.exp(beta - 1.96 * se)
        hi = math.exp(beta + 1.96 * se)
        p = float(2 * (1 - stats.norm.cdf(abs(beta / se)))) if se > 0 else np.nan
        return {"hr": hr, "lcl": lo, "ucl": hi, "p": p, "beta": beta, "se": se}
    except Exception:
        chi2, p = logrank_test(time, event, group)
        # Crude event-rate ratio fallback - not a substitute, but keeps outputs robust.
        rate1 = event[group == 1].sum() / max(time[group == 1].sum(), 1e-9)
        rate0 = event[group == 0].sum() / max(time[group == 0].sum(), 1e-9)
        hr = rate1 / rate0 if rate0 > 0 else np.nan
        return {"hr": float(hr), "lcl": np.nan, "ucl": np.nan, "p": float(p), "beta": np.nan, "se": np.nan}


def beta_ci(x: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return np.nan, np.nan
    lo = 0.0 if x == 0 else stats.beta.ppf(alpha / 2, x, n - x + 1)
    hi = 1.0 if x == n else stats.beta.ppf(1 - alpha / 2, x + 1, n - x)
    return float(lo), float(hi)


def safe_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_")
