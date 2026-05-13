/* Validation/QC template in SAS */
%include "programs/sas/00_setup.sas";

proc import datafile="&root/data/adam/adsl.csv" out=adsl dbms=csv replace; guessingrows=max; run;
proc import datafile="&root/data/adam/adtte.csv" out=adtte dbms=csv replace; guessingrows=max; run;
proc import datafile="&root/data/adam/adae.csv" out=adae dbms=csv replace; guessingrows=max; run;

proc sql;
  title "ADSL uniqueness check";
  select count(*) as rows, count(distinct USUBJID) as unique_subjects from adsl;

  title "ADTTE endpoint count check";
  select PARAMCD, count(*) as rows, count(distinct USUBJID) as subjects from adtte group by PARAMCD;

  title "ADAE toxicity grade check";
  select AETOXGR, count(*) as rows from adae group by AETOXGR;
quit;
