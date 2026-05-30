---
name: "cli-anything-google-ads"
description: "CLI harness for the Google Ads API — manage campaigns, budgets, ad groups, keywords, and run reports via command line"
---

# cli-anything-google-ads

Command-line interface for the Google Ads API built on the official [google-ads-python](https://github.com/googleads/google-ads-python) library.

## Prerequisites

- Google Ads developer token: https://developers.google.com/google-ads/api/docs/first-call/dev-token
- OAuth2 credentials (Desktop app type): https://console.cloud.google.com/apis/credentials
- Python 3.9+

## Installation

```bash
cd agent-harness
pip install -e .
```

## Authentication

```bash
# Interactive setup (opens browser for OAuth2)
google-ads-cli auth setup

# Test credentials
google-ads-cli auth test

# Show current config (secrets masked)
google-ads-cli auth show
```

Credentials stored at `~/.config/google-ads-cli/credentials.yaml`.

## Global Flags

| Flag | Description |
|------|-------------|
| `--config PATH` | Path to credentials.yaml (or `GOOGLE_ADS_CLI_CONFIG` env) |
| `--customer-id ID` | Google Ads customer ID (or `GOOGLE_ADS_CUSTOMER_ID` env) |
| `--api-version VER` | API version, default `v24` |
| `--json` | Output as JSON for machine consumption |

## Command Groups

### auth — Credential management
```bash
google-ads-cli auth setup              # Interactive OAuth2 + developer token setup
google-ads-cli auth test               # Test credentials against the API
google-ads-cli auth show               # Display config (masked secrets)
```

### accounts — Account discovery
```bash
google-ads-cli accounts list           # List all accessible accounts
google-ads-cli accounts info           # Show current account details
google-ads-cli accounts sub-accounts   # List child accounts (MCC/manager)
```

### campaigns — Campaign management
```bash
google-ads-cli campaigns list [--status ENABLED|PAUSED|REMOVED]
google-ads-cli campaigns get <campaign_id>
google-ads-cli campaigns create --name "Name" --budget-id <id> [--channel SEARCH] [--status PAUSED]
google-ads-cli campaigns enable <campaign_id>
google-ads-cli campaigns pause <campaign_id>
google-ads-cli campaigns remove <campaign_id> [--yes]
```

### ad-groups — Ad group management
```bash
google-ads-cli ad-groups list [--campaign-id <id>] [--status ENABLED|PAUSED]
google-ads-cli ad-groups get <ad_group_id>
google-ads-cli ad-groups create --name "Name" --campaign-id <id> [--cpc-bid 1.50]
google-ads-cli ad-groups enable <ad_group_id>
google-ads-cli ad-groups pause <ad_group_id>
```

### budgets — Budget management
```bash
google-ads-cli budgets list [--all]
google-ads-cli budgets get <budget_id>
google-ads-cli budgets create --name "Budget" --amount 10.00
google-ads-cli budgets update <budget_id> --amount 15.00
```

### keywords — Keyword management
```bash
google-ads-cli keywords list [--ad-group-id <id>] [--campaign-id <id>]
google-ads-cli keywords add --ad-group-id <id> -k "keyword 1" -k "keyword 2" [--match-type PHRASE]
google-ads-cli keywords enable <criterion_id> --ad-group-id <id>
google-ads-cli keywords pause <criterion_id> --ad-group-id <id>
google-ads-cli keywords remove <criterion_id> --ad-group-id <id>
```

### reports — Analytics and reporting
```bash
google-ads-cli reports campaigns [--date-range LAST_30_DAYS] [--status ENABLED]
google-ads-cli reports ad-groups [--campaign-id <id>] [--date-range LAST_7_DAYS]
google-ads-cli reports keywords [--campaign-id <id>] [--limit 50]
google-ads-cli reports search-terms [--campaign-id <id>]
google-ads-cli reports run "SELECT campaign.id, campaign.name FROM campaign LIMIT 10"
```

## Agent Usage (JSON Mode)

All commands support `--json` for machine-readable output:

```bash
# List campaigns as JSON
google-ads-cli --json --customer-id 1234567890 campaigns list

# Create budget, capture ID
BUDGET_ID=$(google-ads-cli --json budgets create --name "Test" --amount 5.00 | jq -r .budget_id)

# Create campaign using that budget
CAMPAIGN_ID=$(google-ads-cli --json campaigns create \
  --name "Test Campaign" \
  --budget-id "$BUDGET_ID" \
  --status PAUSED | jq -r .campaign_id)

# Get campaign performance
google-ads-cli --json reports campaigns --date-range LAST_7_DAYS | \
  jq '.[] | {name: .campaign_name, clicks: .clicks, cost: .cost}'
```

## Error Handling

- Missing credentials: `RuntimeError: No credentials found at ~/.config/google-ads-cli/credentials.yaml`
- Missing customer ID: `UsageError: Customer ID required`
- API errors: Google Ads error messages with request_id
- In JSON mode: errors go to stderr as `{"error": "..."}`

## Date Ranges for Reports

Standard GAQL date ranges:
- `TODAY`, `YESTERDAY`
- `LAST_7_DAYS`, `LAST_14_DAYS`, `LAST_30_DAYS`
- `THIS_WEEK_SUN_TODAY`, `LAST_WEEK_SUN_SAT`
- `THIS_MONTH`, `LAST_MONTH`
- `THIS_YEAR`

## Key Facts for Agents

- Customer IDs: dashes are stripped automatically (`123-456-7890` → `1234567890`)
- Budget/CPC amounts: specified in currency units (dollars), stored as micros internally
- New campaigns default to PAUSED to prevent accidental spend
- Keywords support BROAD, PHRASE, EXACT match types
- `reports run` accepts any valid GAQL query
- Manager accounts need `login_customer_id` in config for child account access
