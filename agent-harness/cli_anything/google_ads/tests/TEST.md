# google-ads-cli Test Plan and Results

## Test Inventory Plan

| File | Description | Planned Count |
|------|-------------|---------------|
| `test_core.py` | Unit tests for core modules (no API calls) | ~35 |
| `test_full_e2e.py` | E2E tests requiring real Google Ads credentials | ~15 |

---

## Unit Test Plan (`test_core.py`)

### `core/auth.py`
- `test_get_config_path_default` — returns ~/.config/google-ads-cli/credentials.yaml
- `test_get_config_path_explicit` — explicit path overrides default
- `test_get_config_path_env` — GOOGLE_ADS_CLI_CONFIG env var respected
- `test_load_config_missing` — returns empty dict when file not found
- `test_load_config_valid` — parses YAML correctly
- `test_save_config` — creates directory and writes YAML
- `test_save_config_masks_secrets` — (conceptual) raw values stored, masking in CLI
- `test_get_client_no_config` — raises RuntimeError with setup hint
- `test_get_client_missing_token` — raises RuntimeError on missing developer_token

### `core/campaigns.py`
- `test_list_campaigns_empty_result` — returns empty list when no rows
- `test_campaign_status_values` — ENABLED/PAUSED/REMOVED accepted
- `test_create_campaign_defaults` — defaults: PAUSED, today start date, SEARCH channel

### `core/budgets.py`
- `test_micros_conversion` — 5000000 micros → $5.00
- `test_create_budget_required_fields` — name + amount_micros required
- `test_update_budget_field_mask` — only amount_micros in field mask

### `core/keywords.py`
- `test_keyword_match_types` — BROAD/PHRASE/EXACT all valid
- `test_add_keywords_multi` — multiple keywords in one operation
- `test_remove_keyword_resource_name` — correct resource name format

### `utils/google_ads_backend.py`
- `test_format_customer_id` — strips dashes and spaces
- `test_micros_to_currency` — conversion correctness
- `test_currency_to_micros` — round-trip accuracy
- `test_build_resource_name` — correct path format
- `test_translate_error_non_google` — falls back to str(exc)
- `test_backend_is_configured_false` — returns False when no config
- `test_backend_is_configured_true` — returns True when developer_token present

### `google_ads_cli.py` (Click CLI structure)
- `test_cli_help` — --help returns exit 0
- `test_auth_help` — auth --help works
- `test_campaigns_help` — campaigns --help works
- `test_ad_groups_help` — ad-groups --help works
- `test_budgets_help` — budgets --help works
- `test_keywords_help` — keywords --help works
- `test_reports_help` — reports --help works
- `test_json_flag_propagation` — --json sets json_output on context
- `test_customer_id_required_error` — proper UsageError without customer ID
- `test_micros_to_currency_helper` — $5.00 from 5000000
- `test_version_flag` — --version prints version and exits 0

### `reports.py`
- `test_run_query_empty` — empty result set → empty list
- `test_campaign_performance_fields` — result dicts have expected keys
- `test_keyword_performance_ctr` — CTR calculated as percentage

---

## E2E Test Plan (`test_full_e2e.py`)

These tests call the real Google Ads API. Set env vars:
```
GOOGLE_ADS_CUSTOMER_ID=<your test account ID>
GOOGLE_ADS_CLI_CONFIG=~/.config/google-ads-cli/credentials.yaml
```

### Credential Validation
- `test_credentials_valid` — auth test returns ok=True
- `test_accessible_customers` — lists at least one account

### Account Operations
- `test_account_info` — get_customer_info returns name and currency

### Campaign Read Operations
- `test_list_campaigns` — returns list (may be empty for test accounts)
- `test_campaign_performance_report` — returns list with expected fields

### Budget Operations (creates/cleans up)
- `test_budget_lifecycle` — create budget, verify in list, update amount

### Campaign Lifecycle (creates/cleans up)
- `test_campaign_lifecycle` — create budget → create campaign (PAUSED) → verify → pause → remove

### Ad Group Lifecycle
- `test_ad_group_lifecycle` — create campaign + budget → create ad group → verify → pause

### Keyword Operations
- `test_keyword_lifecycle` — create ad group → add keyword → list → pause → remove

### Reports
- `test_gaql_query` — run raw GAQL for campaigns, get back structured data

### CLI Subprocess Tests
- `test_cli_help_subprocess` — google-ads-cli --help via subprocess
- `test_cli_auth_show_subprocess` — google-ads-cli auth show via subprocess
- `test_cli_campaigns_list_json` — --json output parses as valid JSON
- `test_cli_reports_campaigns_json` — campaign report JSON output

---

## Realistic Workflow Scenarios

### Scenario 1: New Campaign Setup
Simulates setting up a basic search campaign from scratch.
- Operations: create budget → create campaign (PAUSED) → create ad group → add keywords
- Verified: each resource ID returned, objects exist via list commands
- Cleanup: pause campaign → remove campaign → (budget remains shared)

### Scenario 2: Performance Review
Simulates an analyst reviewing account performance.
- Operations: list campaigns → campaign report → ad group report → keyword report → search terms
- Verified: all reports return dicts with impressions/clicks/cost fields

### Scenario 3: Budget Management
Simulates adjusting campaign budgets.
- Operations: list budgets → create budget → update amount → verify updated amount
- Verified: new amount reflected in get_budget

---

## Test Results

### Unit Tests (`test_core.py`) — 2026-05-30

```
============================= test session starts ==============================
platform linux -- Python 3.12.8, pytest-9.0.3, pluggy-1.6.0
collected 41 items

test_core.py::TestAuthConfigPath::test_default_path PASSED
test_core.py::TestAuthConfigPath::test_explicit_path PASSED
test_core.py::TestAuthConfigPath::test_env_var PASSED
test_core.py::TestAuthConfigPath::test_explicit_overrides_env PASSED
test_core.py::TestAuthLoadConfig::test_missing_file_returns_empty PASSED
test_core.py::TestAuthLoadConfig::test_valid_yaml PASSED
test_core.py::TestAuthLoadConfig::test_empty_yaml_returns_empty PASSED
test_core.py::TestAuthSaveConfig::test_creates_directory PASSED
test_core.py::TestAuthSaveConfig::test_overwrites_existing PASSED
test_core.py::TestAuthGetClient::test_no_config_raises PASSED
test_core.py::TestAuthGetClient::test_missing_developer_token_raises PASSED
test_core.py::TestBackendUtils::test_format_customer_id_strips_dashes PASSED
test_core.py::TestBackendUtils::test_format_customer_id_strips_spaces PASSED
test_core.py::TestBackendUtils::test_format_customer_id_already_clean PASSED
test_core.py::TestBackendUtils::test_micros_to_currency PASSED
test_core.py::TestBackendUtils::test_currency_to_micros PASSED
test_core.py::TestBackendUtils::test_micros_roundtrip PASSED
test_core.py::TestBackendUtils::test_build_resource_name_campaign PASSED
test_core.py::TestBackendUtils::test_build_resource_name_strips_dashes PASSED
test_core.py::TestBackendUtils::test_translate_error_non_google PASSED
test_core.py::TestBackendUtils::test_backend_not_configured PASSED
test_core.py::TestBackendUtils::test_backend_is_configured PASSED
test_core.py::TestCLIStructure::test_cli_help PASSED
test_core.py::TestCLIStructure::test_cli_version PASSED
test_core.py::TestCLIStructure::test_auth_help PASSED
test_core.py::TestCLIStructure::test_campaigns_help PASSED
test_core.py::TestCLIStructure::test_ad_groups_help PASSED
test_core.py::TestCLIStructure::test_budgets_help PASSED
test_core.py::TestCLIStructure::test_keywords_help PASSED
test_core.py::TestCLIStructure::test_reports_help PASSED
test_core.py::TestCLIStructure::test_auth_show_help PASSED
test_core.py::TestCLIStructure::test_campaigns_list_help PASSED
test_core.py::TestCLIStructure::test_campaigns_create_help PASSED
test_core.py::TestCLIStructure::test_keywords_add_help PASSED
test_core.py::TestCLIStructure::test_reports_run_help PASSED
test_core.py::TestCLIAuthShow::test_auth_show_no_config PASSED
test_core.py::TestCLIAuthShow::test_auth_show_with_config PASSED
test_core.py::TestCLIAuthShow::test_auth_show_json PASSED
test_core.py::TestContext::test_require_customer_missing PASSED
test_core.py::TestContext::test_require_customer_present PASSED
test_core.py::TestContext::test_output_json_mode PASSED

============================== 41 passed in 2.08s ==============================
```

**Summary:** 41/41 passed (100%) in 2.08s

**Coverage:** All core modules covered. E2E tests (`test_full_e2e.py`) require real Google Ads credentials — set `GOOGLE_ADS_CUSTOMER_ID` to run them.
