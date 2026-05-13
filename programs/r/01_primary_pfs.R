# Primary PFS analysis template in R
source("programs/r/00_setup.R")

adtte <- read_csv(file.path(adam_dir, "adtte.csv"), show_col_types = FALSE)
pfs <- adtte %>%
  filter(PARAMCD == "PFS", ANL01FL == "Y") %>%
  mutate(event = 1 - CNSR, trt = factor(TRT01P))

fit_km <- survfit(Surv(AVAL, event) ~ trt, data = pfs)
fit_cox <- coxph(Surv(AVAL, event) ~ trt, data = pfs)
logrank <- survdiff(Surv(AVAL, event) ~ trt, data = pfs)

print(summary(fit_km))
print(summary(fit_cox))
print(logrank)
