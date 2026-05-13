# Safety TEAE summary template in R
source("programs/r/00_setup.R")

adsl <- read_csv(file.path(adam_dir, "adsl.csv"), show_col_types = FALSE)
adae <- read_csv(file.path(adam_dir, "adae.csv"), show_col_types = FALSE)

denom <- adsl %>% filter(SAFFL == "Y") %>% count(TRT01P, name = "N")

teae_by_pt <- adae %>%
  filter(TRTEMFL == "Y") %>%
  distinct(TRT01P, USUBJID, AEBODSYS, AEDECOD) %>%
  count(TRT01P, AEBODSYS, AEDECOD, name = "n") %>%
  left_join(denom, by = "TRT01P") %>%
  mutate(pct = 100 * n / N) %>%
  arrange(AEBODSYS, desc(n))

print(teae_by_pt)
