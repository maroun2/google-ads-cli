# google-ads-cli

Command-line interface for the Google Ads API, built on the [google-ads-python](https://github.com/googleads/google-ads-python) library.

## Prerequisites

- Python 3.9+
- A Google Ads developer token
- OAuth2 credentials (Desktop app type) from Google Cloud Console

## Installation

```bash
cd agent-harness
pip install -e .
```

## Authentication Setup

```bash
google-ads-cli auth setup
```

This guides you through:
1. Entering your developer token
2. Entering OAuth2 client ID + secret
3. Opening browser for Google account authorization
4. Optionally entering a manager (MCC) account ID

Credentials are saved to `~/.config/google-ads-cli/credentials.yaml`.

Test your credentials:
```bash
google-ads-cli auth test
```

## Usage

```bash
# List accessible accounts
google-ads-cli accounts list

# List campaigns (customer ID required for most commands)
google-ads-cli --customer-id 1234567890 campaigns list

# Use env var instead of flag
export GOOGLE_ADS_CUSTOMER_ID=1234567890
google-ads-cli campaigns list

# JSON output for scripting
google-ads-cli --json campaigns list

# Interactive REPL
google-ads-cli
```

## Commands

| Group | Commands |
|-------|---------|
| `auth` | `setup`, `test`, `show` |
| `accounts` | `list`, `info`, `sub-accounts` |
| `campaigns` | `list`, `get`, `create`, `enable`, `pause`, `remove` |
| `ad-groups` | `list`, `get`, `create`, `enable`, `pause` |
| `budgets` | `list`, `get`, `create`, `update` |
| `keywords` | `list`, `add`, `enable`, `pause`, `remove` |
| `reports` | `campaigns`, `ad-groups`, `keywords`, `search-terms`, `run` |

## Examples

```bash
# Create a $10/day budget
google-ads-cli budgets create --name "My Budget" --amount 10.00

# Create a paused search campaign
google-ads-cli campaigns create \
  --name "My Campaign" \
  --budget-id 123456 \
  --channel SEARCH \
  --status PAUSED

# Create an ad group with $1.50 CPC bid
google-ads-cli ad-groups create \
  --name "Ad Group 1" \
  --campaign-id 987654321 \
  --cpc-bid 1.50

# Add keywords
google-ads-cli keywords add \
  --ad-group-id 12345 \
  -k "running shoes" \
  -k "buy sneakers" \
  --match-type PHRASE

# Campaign performance last 7 days
google-ads-cli reports campaigns --date-range LAST_7_DAYS

# Raw GAQL query
google-ads-cli reports run "SELECT campaign.id, campaign.name, metrics.impressions FROM campaign ORDER BY metrics.impressions DESC LIMIT 10"

# JSON output for scripting
google-ads-cli --json --customer-id 1234567890 campaigns list | jq '.[].name'
```

## Running Tests

```bash
cd agent-harness
pytest cli_anything/google_ads/tests/ -v
```

E2E tests require valid Google Ads credentials.

## Config File Format

`~/.config/google-ads-cli/credentials.yaml`:

```yaml
developer_token: your_developer_token
client_id: your_oauth2_client_id.apps.googleusercontent.com
client_secret: your_client_secret
refresh_token: your_refresh_token
use_proto_plus: false
# Optional:
login_customer_id: "1234567890"  # manager account ID
```

Custom config path:
```bash
google-ads-cli --config /path/to/credentials.yaml campaigns list
# or
export GOOGLE_ADS_CLI_CONFIG=/path/to/credentials.yaml
```
