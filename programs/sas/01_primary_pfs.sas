/* Primary PFS analysis template in SAS */
%include "programs/sas/00_setup.sas";

proc import datafile="&root/data/adam/adtte.csv" out=adtte dbms=csv replace;
  guessingrows=max;
run;

data pfs;
  set adtte;
  where PARAMCD="PFS" and ANL01FL="Y";
  EVENT = 1 - CNSR;
  TRT = (TRT01P="ONC-305 + SOC");
run;

proc lifetest data=pfs plots=survival(atrisk);
  time AVAL*CNSR(1);
  strata TRT01P / test=logrank;
run;

proc phreg data=pfs;
  class TRT01P(ref="Placebo + SOC") / param=ref;
  model AVAL*CNSR(1) = TRT01P / ties=breslow risklimits;
run;
