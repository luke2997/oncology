
/* ---------------------------------------------------------------------------
   ONC-305-301 SAS template macros
   Purpose: show regulated-workflow thinking for TLF generation.
   Note: Template only; not executed in the Python build environment.
--------------------------------------------------------------------------- */

%macro count_pct(data=, class=, trt=TRT01P, out=);
    proc sql;
        create table &out as
        select &class,
               &trt,
               count(distinct USUBJID) as n
        from &data
        group by &class, &trt;
    quit;
%mend;

%macro km_phreg(data=adtte, paramcd=PFS, out=);
    data _tte;
        set &data;
        where PARAMCD="&paramcd" and ANL01FL="Y";
        event = 1 - CNSR;
    run;

    proc lifetest data=_tte plots=survival;
        time AVAL*CNSR(1);
        strata TRT01P;
    run;

    proc phreg data=_tte;
        class TRT01P(ref="Placebo + SOC") ECOG PDL1CAT / param=ref;
        model AVAL*CNSR(1) = TRT01P ECOG PDL1CAT / ties=efron;
        ods output ParameterEstimates=&out;
    run;
%mend;

%macro teae_socpt(data=adae, out=);
    data _teae;
        set &data;
        where SAFFL="Y" and TRTEMFL="Y";
    run;
    proc sql;
        create table &out as
        select AEBODSYS, AEDECOD, TRT01P, count(distinct USUBJID) as subjects
        from _teae
        group by AEBODSYS, AEDECOD, TRT01P;
    quit;
%mend;
