## 1. Purpose

This guide explains the simulated analysis datasets, derivation logic, metadata, traceability and known limitations. It is included because reviewer guides are a normal part of regulatory-style clinical data submissions and show that the portfolio is not just a collection of tables.

## 2. Dataset overview

| Dataset   | Submission-style role          | Structure                                | Key variables                                           | Why it matters                                                                 |
|:----------|:-------------------------------|:-----------------------------------------|:--------------------------------------------------------|:-------------------------------------------------------------------------------|
| ADSL      | Subject-Level Analysis Dataset | One record per subject                   | Treatment, demographics, strata, flags, exposure        | ADSL for all population denominators                                           |
| ADTTE     | Time-to-Event Analysis Dataset | One record per subject per endpoint      | PARAMCD, AVAL, CNSR, EVNTDESC, STARTDT, ADT             | PFS/OS KM, log-rank and Cox analyses                                           |
| ADRS      | Response Analysis Dataset      | One record per subject                   | BOR, ORRFL, DCRFL, BESTPCHG                             | ORR/DCR summaries and waterfall plot                                           |
| ADAE      | Adverse Event Analysis Dataset | One record per AE                        | AEBODSYS, AEDECOD, AETOXGR, AESER, AEREL, AEACN, AESDTH | TEAE incidence, seriousness, severity, discontinuation and fatal-event outputs |
| ADLB      | Laboratory Analysis Dataset    | One record per subject per lab parameter | BASEGR, WORSTGR, SHIFT                                  | Laboratory grade-shift table                                                   |

## 3. Data flow

| Layer         | Dataset   |   Rows |   Variables | Purpose                                                 |
|:--------------|:----------|-------:|------------:|:--------------------------------------------------------|
| Raw/simulated | DM        |    420 |          24 | Demography, randomization, baseline and treatment dates |
| Raw/simulated | TTE       |    840 |          10 | Progression-free survival and overall survival source   |
| Raw/simulated | RS        |    420 |           6 | Best overall response and tumor change source           |
| Raw/simulated | AE        |    976 |          15 | Adverse event source                                    |
| Raw/simulated | LB        |   1680 |           7 | Laboratory grade shifts source                          |
| ADaM-style    | ADSL      |    420 |          33 | Subject-level analysis dataset                          |
| ADaM-style    | ADTTE     |    840 |          20 | Time-to-event analysis dataset                          |
| ADaM-style    | ADAE      |    976 |          24 | Adverse event analysis dataset                          |
| ADaM-style    | ADRS      |    420 |          15 | Response analysis dataset                               |
| ADaM-style    | ADLB      |   1680 |          11 | Laboratory analysis dataset                             |

## 4. Traceability matrix

| Requirement             | Analysis question                               | Document reference   | Dataset/variables                 | Output                                       | Program                          |
|:------------------------|:------------------------------------------------|:---------------------|:----------------------------------|:---------------------------------------------|:---------------------------------|
| Primary objective       | Compare PFS                                     | SAP Section 7.1      | ADTTE PARAMCD=PFS                 | Table 14.2.1, Figure 14.2.1                  | programs/python/generate_tlfs.py |
| Key secondary objective | Compare OS                                      | SAP Section 7.2      | ADTTE PARAMCD=OS                  | Table 14.2.2, Figure 14.2.2                  | programs/python/generate_tlfs.py |
| Key secondary objective | Summarize ORR                                   | SAP Section 7.3      | ADRS ORRFL                        | Table 14.2.3, Figure 14.2.4                  | programs/python/generate_tlfs.py |
| Safety objective        | Summarize TEAEs                                 | SAP Section 8        | ADAE TRTEMFL/AOCCFL/AOCCSFL       | Tables 14.3.1-14.3.5, Listings 16.2.2-16.2.3 | programs/python/generate_tlfs.py |
| Data standards          | Document ADaM-style metadata                    | ADRG Section 4       | ADSL/ADTTE/ADAE/ADRS/ADLB         | define_like_metadata.xml, adam_spec.csv      | programs/python/build_adam.py    |
| QC objective            | Confirm reproducibility and output completeness | Validation Report    | All analysis datasets and outputs | qc/validation_checks.csv                     | programs/python/qc_validation.py |

## 5. Metadata and limitations

- The analysis datasets are ADaM-style CSV files with define-like XML metadata. They are not official SAS XPT transport files in this executable environment.
- The synthetic data were generated for portfolio demonstration only and do not represent any real drug, patient or site.
- SAS and R skeletons are included for translation to a more conventional sponsor/CRO toolchain.
- All scripts are deterministic under the fixed seed and can be regenerated from the repository root.
