# ONC-305-301 simulated portfolio - R setup template
# This file is a recruiter-facing template showing how the Python implementation maps to R/pharmaverse-style work.

# Suggested packages if running in a full R environment:
# install.packages(c("tidyverse", "survival", "survminer", "rtables", "tern", "admiral", "xportr"))

library(dplyr)
library(readr)
library(survival)

root <- normalizePath(file.path(dirname(sys.frame(1)$ofile), "..", ".."), mustWork = FALSE)
raw_dir <- file.path(root, "data", "raw")
adam_dir <- file.path(root, "data", "adam")
out_dir <- file.path(root, "outputs")
