# Test Plan: SPEC-0012

## Test Mapping
- `FR-026`, `DATA-014`, `AC-046` $\rightarrow$ `tests/test_electoral_campaign_donations.py::TestElectoralCampaignDonationsCrossmatch::test_electoral_donation_model_validation_and_masking`
- `FR-027`, `AC-047` $\rightarrow$ `tests/test_electoral_campaign_donations.py::TestElectoralCampaignDonationsCrossmatch::test_electoral_crossmatch_rule_detects_donor_as_supplier`
- `NFR-015`, `AC-048` $\rightarrow$ `tests/test_electoral_campaign_donations.py::TestElectoralCampaignDonationsCrossmatch::test_electoral_crossmatch_rule_ignores_masked_cpf_homonym`
- `AC-049` $\rightarrow$ `tests/test_electoral_campaign_donations.py::TestElectoralCampaignDonationsCrossmatch::test_electoral_crossmatch_rule_ignores_unrelated_supplier`
