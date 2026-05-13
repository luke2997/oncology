/* ONC-305-301 simulated portfolio - SAS setup template */
/* Update ROOT to your local repository path before running in SAS. */
%let root=/path/to/oncology_stat_submission_portfolio;
libname raw "&root/data/raw";
libname adam "&root/data/adam";
filename out "&root/outputs";
options mprint mlogic symbolgen validvarname=upcase;
