from __future__ import annotations

import pandas as pd
import numpy as np

from utils import DATA_RAW, DATA_ADAM, DATA_SPECS, STUDY_ID, ensure_dirs, ARM_T, ARM_C


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_RAW / f"{name}.csv")


def build_adam() -> None:
    """Build ADaM-style analysis datasets from raw simulated data.

    This is not a formal CDISC-certified implementation, but it deliberately uses ADaM naming
    patterns and analysis flags so recruiters can inspect familiar clinical-trial workflow logic.
    """
    ensure_dirs()
    dm = _read("dm")
    tte = _read("tte")
    rs = _read("rs")
    ds = _read("ds")
    ae = _read("ae")
    lb = _read("lb")
    ex = _read("ex")

    dm["RANDDT"] = pd.to_datetime(dm["RANDDT"])
    dm["TRTSDT"] = pd.to_datetime(dm["TRTSDT"])
    dm["TRTEDT"] = pd.to_datetime(dm["TRTEDT"])
    dm["TRTDURM"] = (dm["TRTDURD"] / 30.4375).round(2)
    dm["TRT01P"] = dm["ARM"]
    dm["TRT01A"] = dm["ACTARM"]
    dm["TRT01PN"] = np.where(dm["TRT01P"] == ARM_T, 1, 0)
    dm["TRT01AN"] = np.where(dm["TRT01A"] == ARM_T, 1, 0)
    dm["AGEGR1N"] = np.where(dm["AGEGR1"] == "<65", 1, 2)
    dm["ECOGN"] = pd.to_numeric(dm["ECOG"])
    dm["STAGE4FL"] = np.where(dm["STAGE"] == "IV", "Y", "N")
    dm["PDL1HIGHFL"] = np.where(dm["PDL1CAT"] == ">=50%", "Y", "N")

    ds_sub = ds[["USUBJID", "DSDECOD"]].rename(columns={"DSDECOD": "DCSREAS"})
    adsl = dm.merge(ds_sub, on="USUBJID", how="left")
    adsl["FASFL"] = "Y"
    adsl["SAFFL"] = "Y"
    adsl["ITTFL"] = "Y"
    adsl["STUDYID"] = STUDY_ID
    adsl = adsl[[
        "STUDYID", "USUBJID", "SUBJID", "SITEID", "COUNTRY", "REGION", "TRT01P", "TRT01A", "TRT01PN", "TRT01AN",
        "RANDDT", "TRTSDT", "TRTEDT", "TRTDURD", "TRTDURM", "RDI", "FASFL", "SAFFL", "ITTFL",
        "AGE", "AGEGR1", "AGEGR1N", "SEX", "RACE", "ECOG", "ECOGN", "STAGE", "STAGE4FL", "PDL1CAT", "PDL1HIGHFL", "HISTOLOGY", "DISEASE_MONTHS", "DCSREAS"
    ]]

    tte["ADT"] = pd.to_datetime(tte["ADT"])
    adtte = tte.merge(adsl[["USUBJID", "TRT01P", "TRT01PN", "TRTSDT", "AGEGR1", "SEX", "ECOG", "STAGE", "PDL1CAT", "REGION", "FASFL"]], on="USUBJID", how="left")
    adtte["ANL01FL"] = "Y"
    adtte["AVAL"] = adtte["AVAL"].astype(float)
    adtte["AVALD"] = adtte["AVALD"].astype(int)
    adtte["CNSR"] = adtte["CNSR"].astype(int)
    adtte["EVNTDESC"] = np.where(adtte["CNSR"] == 0, "Event", "Censored")
    adtte["STARTDT"] = adtte["TRTSDT"]
    adtte = adtte[["STUDYID", "USUBJID", "TRT01P", "TRT01PN", "PARAM", "PARAMCD", "AVAL", "AVALD", "CNSR", "EVNTDESC", "STARTDT", "ADT", "ANL01FL", "AGEGR1", "SEX", "ECOG", "STAGE", "PDL1CAT", "REGION", "FASFL"]]

    if not ae.empty:
        ae["AESTDT"] = pd.to_datetime(ae["AESTDT"])
        ae["AEENDT"] = pd.to_datetime(ae["AEENDT"])
    adae = ae.merge(adsl[["USUBJID", "TRT01P", "TRT01PN", "TRTSDT", "TRTEDT", "SAFFL"]], on="USUBJID", how="left")
    if not adae.empty:
        adae["ASTDY"] = (adae["AESTDT"] - adae["TRTSDT"]).dt.days + 1
        adae["AENDY"] = (adae["AEENDT"] - adae["TRTSDT"]).dt.days + 1
        adae["TRTEMFL"] = np.where(adae["AESTDT"] >= adae["TRTSDT"], "Y", "N")
        adae["AOCCFL"] = ""
        adae = adae.sort_values(["USUBJID", "AEBODSYS", "AEDECOD", "AETOXGR"], ascending=[True, True, True, False])
        first_idx = adae.drop_duplicates(["USUBJID", "AEBODSYS", "AEDECOD"]).index
        adae.loc[first_idx, "AOCCFL"] = "Y"
        adae["AOCCSFL"] = ""
        first_soc_idx = adae.drop_duplicates(["USUBJID", "AEBODSYS"]).index
        adae.loc[first_soc_idx, "AOCCSFL"] = "Y"
    adae = adae[["STUDYID", "USUBJID", "TRT01P", "TRT01PN", "SAFFL", "TRTSDT", "TRTEDT", "AESEQ", "AEBODSYS", "AEDECOD", "AETERM", "AESTDT", "AEENDT", "ASTDY", "AENDY", "AETOXGR", "AESER", "AEREL", "AEACN", "AEOUT", "AESDTH", "TRTEMFL", "AOCCFL", "AOCCSFL"]]

    adrs = rs.merge(adsl[["USUBJID", "TRT01P", "TRT01PN", "FASFL", "PDL1CAT", "ECOG"]], on="USUBJID", how="left")
    bor_order = {"CR": 1, "PR": 2, "SD": 3, "PD": 4, "NE": 5}
    adrs["BORNUM"] = adrs["BOR"].map(bor_order)
    adrs["PARAMCD"] = "BOR"
    adrs["PARAM"] = "Best Overall Response"
    adrs["ANL01FL"] = "Y"
    adrs = adrs[["STUDYID", "USUBJID", "TRT01P", "TRT01PN", "PARAM", "PARAMCD", "BOR", "BORNUM", "ORRFL", "DCRFL", "BESTPCHG", "ANL01FL", "FASFL", "PDL1CAT", "ECOG"]]

    adlb = lb.merge(adsl[["USUBJID", "TRT01P", "TRT01PN", "SAFFL"]], on="USUBJID", how="left")
    adlb["ANL01FL"] = "Y"
    adlb = adlb[["STUDYID", "USUBJID", "TRT01P", "TRT01PN", "PARAM", "PARAMCD", "BASEGR", "WORSTGR", "SHIFT", "ANL01FL", "SAFFL"]]

    # Save ADaM-style datasets.
    for name, df in [("adsl", adsl), ("adtte", adtte), ("adae", adae), ("adrs", adrs), ("adlb", adlb)]:
        df.to_csv(DATA_ADAM / f"{name}.csv", index=False)

    # ADaM specification dictionary.
    specs = []
    descriptions = {
        "adsl": "Subject-Level Analysis Dataset",
        "adtte": "Time-to-Event Analysis Dataset",
        "adae": "Adverse Event Analysis Dataset",
        "adrs": "Tumor Response Analysis Dataset",
        "adlb": "Laboratory Shift Analysis Dataset",
    }
    for name, df in [("adsl", adsl), ("adtte", adtte), ("adae", adae), ("adrs", adrs), ("adlb", adlb)]:
        for col in df.columns:
            specs.append({
                "Dataset": name.upper(),
                "Dataset Label": descriptions[name],
                "Variable": col,
                "Type": str(df[col].dtype),
                "Role": "Identifier" if col in ["STUDYID", "USUBJID", "SUBJID"] else ("Analysis" if col in ["AVAL", "CNSR", "AETOXGR", "BOR", "ORRFL", "WORSTGR"] else "Covariate/Descriptor"),
                "Origin": "Derived" if col in ["TRT01PN", "TRT01AN", "AGEGR1N", "STAGE4FL", "PDL1HIGHFL", "ANL01FL", "AOCCFL", "AOCCSFL", "ASTDY", "AENDY", "BORNUM"] else "Source/Assigned",
                "Comment": "Simulated portfolio variable; see programs/python/build_adam.py for derivation logic."
            })
    spec_df = pd.DataFrame(specs)
    spec_df.to_csv(DATA_SPECS / "adam_spec.csv", index=False)

    # Simple define.xml-like metadata for visual proof of CDISC awareness.
    xml_lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", "<ODM FileType=\"Snapshot\" FileOID=\"ONC-305-301.DEFINE\" CreationDateTime=\"2026-01-31T00:00:00\" ODMVersion=\"1.3.2\">", "  <Study OID=\"ONC-305-301\">", "    <GlobalVariables>", "      <StudyName>ONC-305-301 Simulated Phase III Oncology Portfolio</StudyName>", "      <StudyDescription>Simulated randomized Phase III oncology statistical submission portfolio.</StudyDescription>", "      <ProtocolName>ONC-305-301</ProtocolName>", "    </GlobalVariables>", "    <MetaDataVersion OID=\"MDV.ADAM\" Name=\"ADaM-style metadata\" Description=\"Portfolio metadata; not a formal CDISC submission.\">"]
    for dataset in sorted(spec_df["Dataset"].unique()):
        label = spec_df.loc[spec_df["Dataset"] == dataset, "Dataset Label"].iloc[0]
        xml_lines.append(f"      <ItemGroupDef OID=\"IG.{dataset}\" Name=\"{dataset}\" Repeating=\"No\" IsReferenceData=\"No\" SASDatasetName=\"{dataset}\" Domain=\"{dataset}\" Purpose=\"Analysis\">")
        xml_lines.append(f"        <Description><TranslatedText>{label}</TranslatedText></Description>")
        for var in spec_df.loc[spec_df["Dataset"] == dataset, "Variable"]:
            xml_lines.append(f"        <ItemRef ItemOID=\"IT.{dataset}.{var}\" Mandatory=\"No\" />")
        xml_lines.append("      </ItemGroupDef>")
    for _, row in spec_df.iterrows():
        xml_lines.append(f"      <ItemDef OID=\"IT.{row['Dataset']}.{row['Variable']}\" Name=\"{row['Variable']}\" DataType=\"text\" Length=\"200\">")
        xml_lines.append(f"        <Description><TranslatedText>{row['Role']}; {row['Origin']}</TranslatedText></Description>")
        xml_lines.append("      </ItemDef>")
    xml_lines += ["    </MetaDataVersion>", "  </Study>", "</ODM>"]
    (DATA_SPECS / "define_like_metadata.xml").write_text("\n".join(xml_lines), encoding="utf-8")

    print(f"Built ADaM-style datasets in {DATA_ADAM}")


if __name__ == "__main__":
    build_adam()
