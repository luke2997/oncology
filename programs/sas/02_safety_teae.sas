/* Safety TEAE summary template in SAS */
%include "programs/sas/00_setup.sas";

proc import datafile="&root/data/adam/adsl.csv" out=adsl dbms=csv replace;
  guessingrows=max;
run;

proc import datafile="&root/data/adam/adae.csv" out=adae dbms=csv replace;
  guessingrows=max;
run;

proc sort data=adsl out=denom nodupkey;
  where SAFFL="Y";
  by TRT01P USUBJID;
run;

proc sort data=adae out=teae nodupkey;
  where TRTEMFL="Y";
  by TRT01P USUBJID AEBODSYS AEDECOD;
run;

proc freq data=teae;
  tables TRT01P*AEBODSYS*AEDECOD / missing nopercent norow nocol;
run;
